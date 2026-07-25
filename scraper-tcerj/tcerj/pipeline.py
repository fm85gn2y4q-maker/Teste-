"""Coleta paginada pelo endpoint JSON e orquestração geral."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Callable

from .config import Config
from .extracao import documento_de_registro
from .http import Cliente, ErroHttp
from .modelos import Documento, TipoDocumento

log = logging.getLogger(__name__)

# Parâmetros cujo valor é um deslocamento em registros, não um índice de página.
_PAGINACAO_POR_DESLOCAMENTO = {"offset", "inicio", "start", "first", "from"}


def paginacao_no_caminho(url: str | None) -> bool:
    """Indica se a paginação vai embutida na própria URL.

    Alguns endpoints do TCE-RJ recebem página e tamanho como segmentos do
    caminho (`.../consulta/pagina/2/tamanhoPagina/50`) e simplesmente ignoram
    os mesmos valores enviados como parâmetro. Nesse caso a URL configurada
    traz os marcadores `{pagina}` e `{tamanho}`.
    """
    return bool(url) and ("{pagina}" in url or "{tamanho}" in url)


def caminhar(dados: Any, caminho: str) -> Any:
    """Percorre um caminho pontilhado dentro de estruturas aninhadas.

    Caminho vazio devolve os próprios dados — o caso em que a resposta já é a
    lista de resultados.
    """
    if not caminho:
        return dados
    atual = dados
    for parte in caminho.split("."):
        if isinstance(atual, dict):
            atual = atual.get(parte)
        elif isinstance(atual, list) and parte.isdigit():
            indice = int(parte)
            atual = atual[indice] if indice < len(atual) else None
        else:
            return None
        if atual is None:
            return None
    return atual


async def coletar_via_api(
    config: Config,
    cliente: Cliente,
    *,
    tipo: TipoDocumento | None = None,
    filtros: dict[str, Any] | None = None,
    max_paginas: int = 100,
    max_documentos: int | None = None,
) -> AsyncIterator[Documento]:
    """Pagina o endpoint descoberto e emite um `Documento` por registro."""
    api = config.api
    if not api.url:
        raise ValueError(
            "Nenhum endpoint configurado. Rode `descobrir` primeiro ou use "
            "--backend navegador."
        )

    por_deslocamento = api.campo_pagina.lower() in _PAGINACAO_POR_DESLOCAMENTO
    no_caminho = paginacao_no_caminho(api.url)
    emitidos = 0
    total_informado: int | None = None

    for indice in range(max_paginas):
        valor_pagina = (
            api.primeira_pagina + indice * api.tamanho_pagina
            if por_deslocamento
            else api.primeira_pagina + indice
        )

        parametros = {**api.parametros, **(filtros or {})}
        # Um corpo vazio (`{}`) é diferente de "sem corpo": há endpoints que
        # exigem o objeto JSON mesmo sem nenhum filtro.
        corpo = dict(api.corpo) if api.corpo is not None else None
        url = api.url

        # O parâmetro de paginação vai no corpo quando a requisição original o
        # levava lá; caso contrário, na query string.
        if no_caminho:
            url = api.url.format(pagina=valor_pagina, tamanho=api.tamanho_pagina)
            if corpo is not None:
                # O termo acompanha o corpo, e não a query string, para não
                # ser enviado duas vezes.
                if filtros:
                    corpo.update(filtros)
                parametros = dict(api.parametros)
        elif corpo is not None and api.campo_pagina in corpo:
            corpo[api.campo_pagina] = valor_pagina
            corpo[api.campo_tamanho] = api.tamanho_pagina
            if filtros:
                corpo.update(filtros)
        else:
            parametros[api.campo_pagina] = valor_pagina
            parametros[api.campo_tamanho] = api.tamanho_pagina

        try:
            resposta = await cliente.requisitar(
                api.metodo,
                url,
                params=parametros or None,
                json_body=corpo,
                headers=api.cabecalhos or None,
            )
            dados = resposta.json()
        except ErroHttp as erro:
            log.error("Falha na página %d: %s", indice, erro)
            break
        except ValueError:
            log.error("Resposta não-JSON na página %d de %s", indice, url)
            break

        if total_informado is None:
            bruto_total = caminhar(dados, api.caminho_total)
            if isinstance(bruto_total, int):
                total_informado = bruto_total
                log.info("Total informado pelo servidor: %d", total_informado)

        itens = caminhar(dados, api.caminho_itens)
        if not isinstance(itens, list) or not itens:
            log.info("Fim da paginação na página %d", indice)
            break

        for registro in itens:
            if not isinstance(registro, dict):
                continue
            if max_documentos is not None and emitidos >= max_documentos:
                return
            yield documento_de_registro(registro, tipo_esperado=tipo)
            emitidos += 1

        if total_informado is not None and emitidos >= total_informado:
            log.info("Coletado o total informado (%d)", total_informado)
            break


async def executar(
    config: Config,
    armazenamento,
    *,
    termo: str | None = None,
    tipo: TipoDocumento | None = None,
    max_paginas: int = 50,
    max_documentos: int | None = None,
    headless: bool = True,
    ao_progresso: Callable[[int, int], None] | None = None,
) -> tuple[int, int]:
    """Roda a coleta no backend configurado e grava o resultado.

    Retorna (novos, atualizados).
    """
    novos = atualizados = 0

    def progresso() -> None:
        if ao_progresso and (novos + atualizados) % 25 == 0:
            ao_progresso(novos, atualizados)

    if config.backend == "api":
        async with Cliente(config) as cliente:
            async for documento in coletar_via_api(
                config,
                cliente,
                tipo=tipo,
                filtros={config.api.campo_termo: termo} if termo else None,
                max_paginas=max_paginas,
                max_documentos=max_documentos,
            ):
                if armazenamento.gravar(documento):
                    novos += 1
                else:
                    atualizados += 1
                if documento.url:
                    armazenamento.marcar_visitado(documento.url, "ok")
                progresso()
    else:
        from . import navegador

        async for documento in navegador.coletar(
            config,
            termo=termo,
            tipo=tipo,
            max_paginas=max_paginas,
            max_documentos=max_documentos,
            headless=headless,
            ja_visitado=armazenamento.ja_visitado,
        ):
            if armazenamento.gravar(documento):
                novos += 1
            else:
                atualizados += 1
            if documento.url:
                armazenamento.marcar_visitado(documento.url, "ok")
            progresso()

    return novos, atualizados
