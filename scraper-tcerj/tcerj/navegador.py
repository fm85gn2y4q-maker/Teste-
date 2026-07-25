"""Coleta via navegador real (Playwright).

Modo de uso geral: funciona mesmo sem conhecer o endpoint interno, porque lê o
que a própria aplicação renderiza na tela. É mais lento que o modo `api`, então
serve como caminho padrão até que a descoberta encontre o endpoint — e como
alternativa estável caso o endpoint mude.
"""

from __future__ import annotations

import logging
import re
from typing import AsyncIterator, Callable
from urllib.parse import urljoin, urlparse

from .config import Config
from .extracao import documento_de_texto, html_para_texto
from .modelos import Documento, TipoDocumento

log = logging.getLogger(__name__)

# Links que costumam apontar para o inteiro teor de um documento.
_RE_LINK_DOCUMENTO = re.compile(
    r"acord|delibera|sumula|s%C3%BAmula|enunciado|jurisprud|documento|"
    r"detalhe|visualiz|inteiro|\.pdf$",
    re.IGNORECASE,
)


async def coletar(
    config: Config,
    *,
    termo: str | None = None,
    tipo: TipoDocumento | None = None,
    max_paginas: int = 10,
    max_documentos: int | None = None,
    headless: bool = True,
    ja_visitado: Callable[[str], bool] | None = None,
) -> AsyncIterator[Documento]:
    """Percorre a listagem e emite um `Documento` por resultado encontrado."""
    from playwright.async_api import async_playwright

    visitado = ja_visitado or (lambda _: False)
    emitidos = 0

    async with async_playwright() as playwright:
        navegador = await playwright.chromium.launch(
            headless=headless, executable_path=config.executavel_navegador()
        )
        contexto = await navegador.new_context(user_agent=config.user_agent, locale="pt-BR")
        pagina = await contexto.new_page()

        try:
            for caminho in config.portais:
                url_portal = config.url_absoluta(caminho)
                log.info("Abrindo portal %s", url_portal)
                try:
                    await pagina.goto(url_portal, wait_until="domcontentloaded", timeout=60_000)
                except Exception as erro:  # noqa: BLE001 - portal pode estar fora do ar
                    log.warning("Não foi possível abrir %s: %s", url_portal, erro)
                    continue

                if termo:
                    await _buscar(pagina, termo, config)

                for numero_pagina in range(1, max_paginas + 1):
                    await pagina.wait_for_timeout(int(config.intervalo_seg * 1000))
                    links = await _coletar_links(pagina, url_portal, config)
                    log.info("Página %d de %s: %d link(s)", numero_pagina, url_portal, len(links))

                    for link in links:
                        if max_documentos is not None and emitidos >= max_documentos:
                            return
                        if visitado(link):
                            continue
                        documento = await _abrir_documento(contexto, link, config, tipo)
                        if documento is not None:
                            emitidos += 1
                            yield documento

                    if not await _proxima_pagina(pagina, config):
                        break
        finally:
            await contexto.close()
            await navegador.close()


async def _buscar(pagina, termo: str, config: Config) -> None:
    try:
        campo = pagina.locator(config.seletores.campo_busca).first
        await campo.wait_for(state="visible", timeout=10_000)
        await campo.fill(termo)
        await campo.press("Enter")
        await pagina.wait_for_timeout(3_000)
    except Exception as erro:  # noqa: BLE001 - nem todo portal exige termo
        log.debug("Busca não submetida em %s: %s", pagina.url, erro)


async def _coletar_links(pagina, url_base: str, config: Config) -> list[str]:
    """Extrai as URLs de detalhe visíveis na listagem.

    Primeiro tenta o seletor configurado; se ele não casar com nada (layout
    diferente do previsto), cai para uma varredura de todos os links da página
    filtrada por vocabulário de documento.
    """
    try:
        brutos: list[str] = await pagina.eval_on_selector_all(
            f"{config.seletores.item_resultado} a[href]",
            "els => els.map(e => e.getAttribute('href'))",
        )
    except Exception:  # noqa: BLE001 - seletor inválido para este layout
        brutos = []

    if not brutos:
        try:
            brutos = await pagina.eval_on_selector_all(
                "a[href]", "els => els.map(e => e.getAttribute('href'))"
            )
        except Exception:  # noqa: BLE001
            brutos = []

    dominio = urlparse(url_base).netloc
    vistos: dict[str, None] = {}
    for bruto in brutos:
        if not bruto or bruto.startswith(("javascript:", "mailto:", "#")):
            continue
        absoluto = urljoin(pagina.url or url_base, bruto)
        if urlparse(absoluto).netloc != dominio:
            continue
        if not _RE_LINK_DOCUMENTO.search(absoluto):
            continue
        vistos.setdefault(absoluto, None)
    return list(vistos)


async def _abrir_documento(
    contexto, url: str, config: Config, tipo: TipoDocumento | None
) -> Documento | None:
    aba = await contexto.new_page()
    try:
        resposta = await aba.goto(url, wait_until="domcontentloaded", timeout=60_000)
        if resposta is not None and resposta.status >= 400:
            log.warning("HTTP %d em %s", resposta.status, url)
            return None

        # PDFs não renderizam no DOM; registramos o endereço para download
        # posterior em vez de tentar extrair texto da tela.
        tipo_conteudo = ""
        if resposta is not None:
            tipo_conteudo = (resposta.headers or {}).get("content-type", "")
        if "pdf" in tipo_conteudo.lower() or url.lower().endswith(".pdf"):
            return Documento(
                tipo=tipo or TipoDocumento.INDEFINIDO, url=url, url_pdf=url, fonte="tcerj"
            )

        await aba.wait_for_timeout(1_200)
        try:
            html = await aba.inner_html(config.seletores.corpo_detalhe, timeout=5_000)
        except Exception:  # noqa: BLE001 - seletor ausente neste layout
            html = await aba.content()

        texto = html_para_texto(html)
        if len(texto) < 80:  # página vazia ou ainda carregando
            return None
        return documento_de_texto(texto, url=url, tipo_esperado=tipo)
    except Exception as erro:  # noqa: BLE001 - um documento ruim não para a coleta
        log.warning("Falha ao ler %s: %s", url, erro)
        return None
    finally:
        await aba.close()


async def _proxima_pagina(pagina, config: Config) -> bool:
    """Avança a paginação. Retorna False quando não há próxima página."""
    try:
        botao = pagina.locator(config.seletores.proxima_pagina).first
        if not await botao.is_visible(timeout=3_000):
            return False
        if await botao.is_disabled():
            return False
        await botao.click(timeout=5_000)
        await pagina.wait_for_timeout(2_500)
        return True
    except Exception as erro:  # noqa: BLE001 - fim natural da listagem
        log.debug("Sem próxima página: %s", erro)
        return False
