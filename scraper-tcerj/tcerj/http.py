"""Cliente HTTP com controle de taxa, repetição e respeito ao robots.txt."""

from __future__ import annotations

import asyncio
import logging
import time
import urllib.robotparser
from typing import Any
from urllib.parse import urlparse

import httpx

from .config import Config

log = logging.getLogger(__name__)

# Erros transitórios que justificam nova tentativa. 4xx (salvo 429) indica
# problema na requisição e repetir só agrava.
_STATUS_REPETIVEIS = {408, 429, 500, 502, 503, 504}


class LimitadorDeTaxa:
    """Garante um intervalo mínimo entre requisições, entre corrotinas."""

    def __init__(self, intervalo_seg: float) -> None:
        self._intervalo = intervalo_seg
        self._proximo = 0.0
        self._trava = asyncio.Lock()

    async def aguardar(self) -> None:
        async with self._trava:
            agora = time.monotonic()
            espera = self._proximo - agora
            if espera > 0:
                await asyncio.sleep(espera)
                agora = time.monotonic()
            self._proximo = agora + self._intervalo


class ErroHttp(RuntimeError):
    def __init__(self, url: str, status: int | None, detalhe: str) -> None:
        super().__init__(f"{url} -> {status or 'sem resposta'}: {detalhe}")
        self.url = url
        self.status = status


class Cliente:
    """Envelope sobre o httpx com as políticas de coleta do projeto."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._limitador = LimitadorDeTaxa(config.intervalo_seg)
        self._semaforo = asyncio.Semaphore(config.concorrencia)
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._cliente = httpx.AsyncClient(
            timeout=config.timeout_seg,
            follow_redirects=True,
            headers={
                "User-Agent": config.user_agent,
                "Accept-Language": "pt-BR,pt;q=0.9",
            },
        )

    async def __aenter__(self) -> "Cliente":
        return self

    async def __aexit__(self, *_) -> None:
        await self.fechar()

    async def fechar(self) -> None:
        await self._cliente.aclose()

    # -- robots -----------------------------------------------------------

    async def permitido(self, url: str) -> bool:
        if not self.config.respeitar_robots:
            return True
        partes = urlparse(url)
        raiz = f"{partes.scheme}://{partes.netloc}"

        if raiz not in self._robots:
            self._robots[raiz] = await self._carregar_robots(raiz)

        leitor = self._robots[raiz]
        if leitor is None:  # sem robots.txt acessível: segue permitido
            return True
        return leitor.can_fetch(self.config.user_agent, url)

    async def _carregar_robots(self, raiz: str) -> urllib.robotparser.RobotFileParser | None:
        leitor = urllib.robotparser.RobotFileParser()
        try:
            resposta = await self._cliente.get(f"{raiz}/robots.txt", timeout=15.0)
        except httpx.HTTPError as erro:
            log.debug("robots.txt indisponível em %s: %s", raiz, erro)
            return None
        if resposta.status_code >= 400:
            return None
        leitor.parse(resposta.text.splitlines())
        return leitor

    # -- requisições ------------------------------------------------------

    async def requisitar(
        self,
        metodo: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        if not await self.permitido(url):
            raise ErroHttp(url, None, "bloqueado pelo robots.txt")

        ultimo_erro: Exception | None = None
        for tentativa in range(1, self.config.tentativas + 1):
            async with self._semaforo:
                await self._limitador.aguardar()
                try:
                    resposta = await self._cliente.request(
                        metodo, url, params=params, json=json_body, headers=headers
                    )
                except httpx.HTTPError as erro:
                    ultimo_erro = erro
                    log.warning("Falha de rede em %s (tentativa %d): %s", url, tentativa, erro)
                else:
                    if resposta.status_code not in _STATUS_REPETIVEIS:
                        if resposta.status_code >= 400:
                            raise ErroHttp(url, resposta.status_code, resposta.reason_phrase)
                        return resposta
                    ultimo_erro = ErroHttp(url, resposta.status_code, resposta.reason_phrase)
                    log.warning(
                        "HTTP %d em %s (tentativa %d)", resposta.status_code, url, tentativa
                    )
                    espera_servidor = _retry_after(resposta)
                    if espera_servidor is not None:
                        await asyncio.sleep(espera_servidor)
                        continue

            if tentativa < self.config.tentativas:
                await asyncio.sleep(2**tentativa)  # 2s, 4s, 8s, 16s

        raise ErroHttp(url, getattr(ultimo_erro, "status", None), str(ultimo_erro))

    async def obter(self, url: str, **kwargs) -> httpx.Response:
        return await self.requisitar("GET", url, **kwargs)

    async def obter_texto(self, url: str, **kwargs) -> str:
        return (await self.obter(url, **kwargs)).text


def _retry_after(resposta: httpx.Response) -> float | None:
    """Lê o cabeçalho Retry-After, quando o servidor indica a espera."""
    valor = resposta.headers.get("Retry-After")
    if not valor:
        return None
    try:
        return min(float(valor), 120.0)
    except ValueError:
        return None
