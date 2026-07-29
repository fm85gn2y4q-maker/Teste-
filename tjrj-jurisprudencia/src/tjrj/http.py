"""Cliente HTTP educado, com cache em disco do conteúdo cru.

Duas regras governam este módulo:

1. **O tribunal não é seu servidor.** Uma conexão, ritmo fixo, recuo
   exponencial, `User-Agent` que diz quem você é e como te achar. Coletar
   devagar é o que permite coletar por meses; coletar rápido é o que faz o
   IP ser bloqueado na segunda semana e o projeto morrer.
2. **Guarde o cru.** Todo byte recebido vai para o cache antes de ser
   interpretado. Quando o parser mudar — e ele vai mudar — você reprocessa
   o acervo inteiro em minutos, sem tocar de novo no TJRJ. Sem isso, cada
   bug de parsing custa outra varredura completa.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import random
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .config import CFG, Config

log = logging.getLogger("tjrj.http")

# Status que merecem nova tentativa. 403 e 404 não estão aqui de propósito:
# repetir um bloqueio só o aprofunda.
RETENTAR = {429, 500, 502, 503, 504, 408}


@dataclass
class Resposta:
    url: str
    status: int
    conteudo: bytes
    headers: Mapping[str, str]
    do_cache: bool = False

    @property
    def texto(self) -> str:
        for cs in ("utf-8", "latin-1", "cp1252"):
            try:
                return self.conteudo.decode(cs)
            except UnicodeDecodeError:
                continue
        return self.conteudo.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.texto)


class Limitador:
    """Espaça as requisições no tempo. Simples e global ao processo."""

    def __init__(self, req_por_segundo: float):
        self.intervalo = 1.0 / max(req_por_segundo, 0.01)
        self._lock = threading.Lock()
        self._ultima = 0.0

    def esperar(self) -> None:
        with self._lock:
            agora = time.monotonic()
            atraso = self._ultima + self.intervalo - agora
            if atraso > 0:
                time.sleep(atraso)
            self._ultima = time.monotonic()


class Cliente:
    def __init__(self, cfg: Config = CFG, *, cache: bool = True):
        self.cfg = cfg
        self.usar_cache = cache
        self.limitador = Limitador(cfg.req_por_segundo)
        self._sessao = None

    # -- sessão ---------------------------------------------------------
    @property
    def sessao(self):
        if self._sessao is None:
            import httpx  # importado tarde: os testes offline não precisam dele

            self._sessao = httpx.Client(
                headers={
                    "User-Agent": self.cfg.user_agent,
                    "Accept-Language": "pt-BR,pt;q=0.9",
                },
                timeout=self.cfg.timeout_s,
                follow_redirects=True,
                # Um host judicial legado costuma negociar TLS antigo; se
                # falhar o handshake, ajuste aqui e não desligue a verificação.
                verify=True,
            )
        return self._sessao

    def fechar(self) -> None:
        if self._sessao is not None:
            self._sessao.close()
            self._sessao = None

    def __enter__(self) -> "Cliente":
        return self

    def __exit__(self, *_) -> None:
        self.fechar()

    # -- cache ----------------------------------------------------------
    def _caminho_cache(self, metodo: str, url: str, dados: Any) -> Path:
        chave = hashlib.sha256(
            f"{metodo}|{url}|{json.dumps(dados, sort_keys=True, default=str)}".encode()
        ).hexdigest()
        # Dois níveis de diretório: um cache de milhões de arquivos num
        # diretório só derruba qualquer sistema de arquivos.
        return self.cfg.cache / chave[:2] / chave[2:4] / f"{chave}.gz"

    def _ler_cache(self, caminho: Path) -> Resposta | None:
        if not (self.usar_cache and caminho.exists()):
            return None
        try:
            with gzip.open(caminho, "rb") as fh:
                env = json.loads(fh.readline().decode())
                corpo = fh.read()
            return Resposta(env["url"], env["status"], corpo, env.get("headers", {}), do_cache=True)
        except (OSError, ValueError, KeyError):
            log.warning("cache corrompido, ignorando: %s", caminho)
            return None

    def _gravar_cache(self, caminho: Path, r: Resposta) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        env = json.dumps(
            {"url": r.url, "status": r.status, "headers": dict(r.headers), "em": time.time()}
        )
        tmp = caminho.with_suffix(".tmp")
        with gzip.open(tmp, "wb") as fh:
            fh.write(env.encode() + b"\n")
            fh.write(r.conteudo)
        tmp.replace(caminho)  # atômico: nunca deixa cache meio escrito

    # -- requisição -----------------------------------------------------
    def pegar(
        self,
        url: str,
        *,
        metodo: str = "GET",
        params: Mapping[str, Any] | None = None,
        dados: Any = None,
        json_corpo: Any = None,
        headers: Mapping[str, str] | None = None,
        cache: bool | None = None,
    ) -> Resposta:
        assinatura = {"params": dict(params or {}), "dados": dados, "json": json_corpo}
        caminho = self._caminho_cache(metodo, url, assinatura)

        if cache is not False:
            guardada = self._ler_cache(caminho)
            if guardada is not None:
                return guardada

        ultima_falha: Exception | None = None
        for tentativa in range(1, self.cfg.tentativas + 1):
            self.limitador.esperar()
            try:
                resp = self.sessao.request(
                    metodo, url, params=params, data=dados, json=json_corpo, headers=headers
                )
            except Exception as e:  # rede caiu, TLS, DNS
                ultima_falha = e
                self._recuar(tentativa, f"{type(e).__name__}: {e}")
                continue

            r = Resposta(str(resp.url), resp.status_code, resp.content, dict(resp.headers))

            if r.status in RETENTAR:
                espera = self._respeitar_retry_after(resp.headers)
                self._recuar(tentativa, f"HTTP {r.status}", forcado=espera)
                continue

            if r.status == 403:
                # Bloqueio ou política. Insistir piora; pare e avise.
                raise BloqueioError(f"403 em {url} — coleta interrompida por bloqueio do servidor")

            if cache is not False and r.status == 200 and r.conteudo:
                self._gravar_cache(caminho, r)
            return r

        raise ColetaError(f"falha após {self.cfg.tentativas} tentativas em {url}: {ultima_falha}")

    def _recuar(self, tentativa: int, motivo: str, forcado: float | None = None) -> None:
        # Recuo exponencial com jitter: sem o jitter, várias tarefas voltam
        # exatamente no mesmo instante e reproduzem o pico que causou o erro.
        espera = forcado if forcado is not None else min(60.0, 2**tentativa) + random.uniform(0, 1.5)
        log.warning("tentativa %d falhou (%s); aguardando %.1fs", tentativa, motivo, espera)
        time.sleep(espera)

    @staticmethod
    def _respeitar_retry_after(headers: Mapping[str, str]) -> float | None:
        valor = headers.get("Retry-After") or headers.get("retry-after")
        if not valor:
            return None
        try:
            return min(300.0, float(valor))
        except ValueError:
            return None


class ColetaError(RuntimeError):
    pass


class BloqueioError(ColetaError):
    """O servidor recusou. Diagnostique antes de voltar — não contorne."""
