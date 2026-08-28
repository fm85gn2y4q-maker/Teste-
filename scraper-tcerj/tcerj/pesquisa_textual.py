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

from .modelos import normalizar

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


# Naturezas de ato de pessoal — registro de aposentadoria, pensão, admissão.
# São ~90% do que o Tribunal julga e não firmam tese: texto padronizado, três
# páginas, "julgar legal o ato". Trazê-las inflaria o acervo com o material
# menos citável e encheria a busca de nomes de servidores, com matrícula e
# proventos, numa base que existe para citar precedente.
#
# O casamento é por PREFIXO e sem acento, deliberadamente: "DISPENSA DE
# LICITAÇÃO" e "SUSPENSÃO DO DIREITO DE LICITAR" contêm "PENS" no meio, e um
# filtro por substring as excluiria — justamente as que mais interessam.
ATOS_DE_PESSOAL = (
    "APOSENTADORIA",
    "PENSAO",
    "REFORMA",
    "TRANSFERENCIA PARA RESERVA",
    "CONTRATACAO DE PESSOAL",
    "CONTRATACAO POR PRAZO",
    "ADMISSAO",
    "READMISSAO",
    "REVISAO DE PROVENTOS",
    "REVISAO DE PENSAO",
    "RECADASTRAMENTO DE INATIVOS",
    "DOCUMENTOS ANEXOS A APOSENTADORIA",
)


def e_ato_de_pessoal(natureza: str | None) -> bool:
    """A natureza é registro de ato de pessoal?

    Sem natureza declarada devolve False: na dúvida, coleta. Descartar por
    ausência de metadado perderia material silenciosamente.
    """
    if not natureza:
        return False
    return normalizar(natureza).upper().lstrip().startswith(ATOS_DE_PESSOAL)


def _limpar(texto: str | None) -> str | None:
    """Tira o destaque que o servidor injeta em torno dos termos buscados."""
    if not texto:
        return None
    return re.sub(r"\s+", " ", _RE_MARCACAO.sub("", texto)).strip() or None


# Grupos de natureza que são REGISTRO DE ATO DE PESSOAL, não decisão.
#
# Medido em 2026: dos 24.019 acórdãos do ano, 21.994 (91%) caem nestes grupos.
# São aposentadoria, pensão, contratação por prazo determinado e afins — três
# páginas, texto padronizado, "julgar legal o ato". Não há tese para citar, e
# trazê-los significa despejar no acervo milhares de nomes de servidores com
# matrícula e proventos, num banco que serve para pesquisar jurisprudência.
#
# O grupo 284 (suspensão de direito de licitar e contratar) NÃO está aqui de
# propósito: é sanção, tem conteúdo decisório, e só apareceu na peneira inicial
# por acidente de expressão regular.
GRUPOS_DE_PESSOAL = frozenset({
    1, 5, 7, 15, 125, 133, 157, 160, 162, 169, 181, 261, 269, 291, 292,
    322, 323, 327, 331, 332, 342, 381, 382, 383, 384, 385, 386, 387, 388, 389,
})

URL_CATALOGO = "https://www.tcerj.tc.br/scap-webapi-externo/api/natureza/tipo/{tipo}"


async def naturezas_de_pessoal(cliente) -> list[dict[str, Any]]:
    """Os objetos de natureza a excluir, buscados no catálogo do Tribunal.

    O filtro NÃO aceita id: `naturezasExcluidas` desserializa para a entidade
    `Liana.Domain.Entities.Natureza`, e mandar inteiro devolve 400. Mandar um
    objeto reduzido devolve 200 e **não filtra nada** — que é o modo de falhar
    perigoso, porque parece ter funcionado. Só o objeto do catálogo, inteiro,
    filtra de verdade.
    """
    achadas: list[dict[str, Any]] = []
    for tipo in (1, 2, 3, 4, 5):
        try:
            resposta = await cliente.obter(URL_CATALOGO.format(tipo=tipo))
            for x in resposta.json():
                grupo = (x.get("grupoNatureza") or {}).get("idGrupoNatureza")
                if grupo in GRUPOS_DE_PESSOAL:
                    achadas.append(x)
        except Exception as erro:  # noqa: BLE001 — catálogo de terceiro
            log.warning("Catálogo de naturezas tipo %s indisponível: %s",
                        tipo, str(erro)[:80])
    return achadas


def _corpo(
    termo: str,
    pagina: int,
    *,
    municipio: int | None = None,
    ano_min: int | None = None,
    ano_max: int | None = None,
    desde: str | None = None,
    ate: str | None = None,
    naturezas_excluidas: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Monta a requisição. Todos os campos vão, mesmo vazios.

    `desde`/`ate` são datas ISO e têm precedência sobre `ano_min`/`ano_max`:
    um ano inteiro pode passar do teto de 10.000 — 2026 tem 24.019 acórdãos —
    e nesse caso a consulta volta truncada sem dizer que truncou.
    """
    corpo: dict[str, Any] = {
        "comTodasAsPalavras": termo,
        "interessado": "",
        "dataCadIni": "", "dataCadFim": "",
        # Data em ISO. Enviar dd/mm/aaaa devolve 500, porque o servidor lê o
        # dia como mês e "31/12" não existe.
        "dataSessaoIni": desde or (f"{ano_min}-01-01" if ano_min else ""),
        "dataSessaoFim": ate or (f"{ano_max}-12-31" if ano_max else ""),
        "naturezas": [], "naturezasExcluidas": naturezas_excluidas or [],
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
    desde: str | None = None,
    ate: str | None = None,
    naturezas_excluidas: list[dict[str, Any]] | None = None,
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
                             ano_min=ano_min, ano_max=ano_max,
                             desde=desde, ate=ate,
                             naturezas_excluidas=naturezas_excluidas),
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
                    "'%s' [%s..%s] bateu o teto de %d: o recorte está "
                    "INCOMPLETO e o que voltar é uma amostra, não o conjunto.",
                    termo or "(sem termo)", desde or ano_min or "-",
                    ate or ano_max or "-", TETO,
                )

        resultados = dados.get("resultados") or []
        if not resultados:
            break
        achadas.extend(_referencias(resultados))

        # `quantidadePaginas` devolve sempre 1; a parada vem da contagem.
        if pagina * TAMANHO_PAGINA >= min(total, TETO):
            break

    return achadas, total
