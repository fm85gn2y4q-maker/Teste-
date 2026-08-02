"""Descoberta de acórdãos pela Pesquisa Textual do TCE-RJ.

A Jurisprudência Selecionada é curadoria: 1.067 ementas de um universo que
passa de cem mil acórdãos por ano. A Pesquisa Textual alcança o acervo além
dela, e é a única rota que permite recorte por tema — a consulta por
número/ano é cega ao assunto.

Este módulo apenas **descobre** referências (número e ano do acórdão). Quem
baixa o inteiro teor continua sendo `inteiro_teor.py`, pelo mesmo endpoint de
sempre. Separar as duas coisas é o que permite medir o tamanho da coleta antes
de comprometer horas de download.

Formato do endpoint levantado em `PESQUISA_TEXTUAL_API.md`.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Iterator

log = logging.getLogger(__name__)

URL = (
    "https://www.tcerj.tc.br/liana-pesquisa-externo/api/pesquisatextual/"
    "acordao/pagina/{pagina}/tamanhoPagina/{tamanho}"
)

# O servidor recusa mais do que isso por página; 100 corta as requisições de
# descoberta em cinco, comparado ao padrão de 20 da interface.
TAMANHO_PAGINA = 100

# `quantidadeTotal` satura aqui. Não é o número de resultados: é o teto. Uma
# consulta que o atinge está incompleta e precisa ser fatiada.
TETO = 10_000

_RE_MARCACAO = re.compile(r"<[^>]+>")


@dataclass(slots=True)
class Referencia:
    """Um acórdão localizado, ainda sem inteiro teor."""

    numero: str
    ano: int
    processo: str | None
    interessado: str | None
    orgao: str | None
    natureza: str | None

    @property
    def oficial(self) -> str:
        return f"acordao-{self.numero}-{self.ano}"


def _limpar(texto: str | None) -> str | None:
    """Tira o destaque que o servidor injeta em torno dos termos buscados."""
    if not texto:
        return None
    return re.sub(r"\s+", " ", _RE_MARCACAO.sub("", texto)).strip() or None


def _corpo(
    termo: str,
    pagina: int,
    *,
    municipio: int | None = None,
    ano_min: int | None = None,
    ano_max: int | None = None,
) -> dict[str, Any]:
    """Monta a requisição. Todos os campos vão, mesmo vazios."""
    corpo: dict[str, Any] = {
        "comTodasAsPalavras": termo,
        "interessado": "",
        "dataCadIni": "", "dataCadFim": "",
        # Data em ISO. Enviar dd/mm/aaaa devolve 500, porque o servidor lê o
        # dia como mês e "31/12" não existe.
        "dataSessaoIni": f"{ano_min}-01-01" if ano_min else "",
        "dataSessaoFim": f"{ano_max}-12-31" if ano_max else "",
        "naturezas": [], "naturezasExcluidas": [],
        "retornaTextoDocumento": False,
        "pagina": pagina,
        "quantidadePorPagina": TAMANHO_PAGINA,
    }
    if municipio is not None:
        corpo["enteFederativoId"] = municipio
    return corpo


def _referencias(resultados: list[dict]) -> Iterator[Referencia]:
    for item in resultados:
        numero, ano = item.get("numeroAcordao"), item.get("anoAcordao")
        if not numero or not ano:
            continue  # processo sem acórdão publicado
        processo = None
        if item.get("numero") and item.get("ano"):
            processo = f"{item['numero']}-{item.get('dv', '')}/{item['ano']}"
        # A natureza vem nula no campo próprio; está no título, depois do
        # número do processo.
        titulo = _limpar(item.get("titulo")) or ""
        natureza = titulo.split(" - ", 1)[1] if " - " in titulo else None
        yield Referencia(
            numero=str(numero), ano=int(ano), processo=processo,
            interessado=_limpar(item.get("interessado")),
            orgao=_limpar(item.get("orgao")),
            natureza=natureza,
        )


async def descobrir(
    cliente,
    termo: str,
    *,
    municipio: int | None = None,
    ano_min: int | None = None,
    ano_max: int | None = None,
    max_paginas: int = 200,
) -> tuple[list[Referencia], int]:
    """Percorre uma consulta e devolve (referências, total informado).

    O total serve para saber se a consulta bateu no teto — nesse caso ela está
    incompleta e o recorte precisa ser mais estreito.
    """
    achadas: list[Referencia] = []
    total = 0

    for pagina in range(1, max_paginas + 1):
        resposta = await cliente.requisitar(
            "POST",
            URL.format(pagina=pagina, tamanho=TAMANHO_PAGINA),
            json_body=_corpo(termo, pagina, municipio=municipio,
                             ano_min=ano_min, ano_max=ano_max),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                # Sem estes o comportamento não foi testado; o portal os envia.
                "Origin": "https://www.tcerj.tc.br",
                "Referer": "https://www.tcerj.tc.br/consulta-acordaos/app",
            },
        )
        dados = resposta.json()
        if pagina == 1:
            total = dados.get("quantidadeTotal", 0)
            if total >= TETO:
                log.warning(
                    "'%s' bateu o teto de %d: o recorte está incompleto.",
                    termo, TETO,
                )

        resultados = dados.get("resultados") or []
        if not resultados:
            break
        achadas.extend(_referencias(resultados))

        # `quantidadePaginas` devolve sempre 1; a parada vem da contagem.
        if pagina * TAMANHO_PAGINA >= min(total, TETO):
            break

    return achadas, total
