"""Inteiro teor dos acórdãos: download do PDF oficial e texto por página.

A listagem de jurisprudência entrega a ementa; o voto que a fundamenta está no
PDF que o próprio portal publica. Este módulo baixa esse documento e o
converte em texto **por página**, porque é a página que permite conferir a
passagem no original — sem ela, um trecho citado é impossível de auditar.

O PDF do acórdão tem duas partes de naturezas distintas: a primeira página traz
a decisão em campos numerados, e as seguintes reproduzem os votos tal como
juntados ao processo, com o cabeçalho de folha repetido em cada uma.
"""

from __future__ import annotations

import io
import logging
import re
from collections import Counter
from dataclasses import dataclass

from .extracao import corrigir_mojibake

log = logging.getLogger(__name__)

URL_PDF = (
    "https://www.tcerj.tc.br/documento-webapi-externo/api/documento/"
    "acordao/{numero}/{ano}?votoInteiro=true"
)

# "Processo nº 106.426-3/22, fls. 20" — o número de folha do processo, que é
# como se cita peça processual e não coincide com a página do PDF.
_RE_FOLHA = re.compile(r"fls?\.\s*(\d{1,5})", re.IGNORECASE)

# Linha que só tem numeração, traço ou espaço: resto de cabeçalho e rodapé.
_RE_LINHA_VAZIA = re.compile(r"^[\s\-–—_.]*$")

# Palavra quebrada pelo fim da linha ("adminis-\ntração").
_RE_HIFENIZACAO = re.compile(r"(\w)-\n([a-záàâãéêíóôõúç])")


@dataclass(slots=True)
class Pagina:
    numero: int          # índice no PDF, a partir de 1
    folha: int | None    # folha do processo, quando o cabeçalho a declara
    texto: str


URL_PROCESSO = (
    "https://www.tcerj.tc.br/consulta-processo/Processo/List?numeroProcesso={processo}"
)


def url_do_acordao(numero: str | int, ano: int) -> str:
    return URL_PDF.format(numero=numero, ano=ano)


def url_do_processo(processo: str | None) -> str | None:
    """A consulta processual não usa o ponto de milhar."""
    if not processo:
        return None
    return URL_PROCESSO.format(processo=processo.replace(".", ""))


# Um acórdão costuma juntar mais de uma peça — voto do relator, voto-vista,
# voto vencedor —, cada qual com o próprio timbre. Exigir que a moldura cubra
# metade do documento deixaria passar a de todas elas; um quinto já basta,
# desde que a linha seja curta, que é o que distingue timbre de conteúdo.
_FRACAO_MOLDURA = 0.2
_MAXIMO_MOLDURA = 90


def _repetidas(paginas: list[str]) -> set[str]:
    """Linhas repetidas nas bordas das páginas: cabeçalho, rodapé, timbre.

    Não são conteúdo e poluiriam a busca — "Processo nº 106.426-3/22"
    apareceria como resultado em qualquer consulta que citasse o número, e o
    nome do gabinete, em toda consulta pelo relator.
    """
    if len(paginas) < 4:
        return set()
    contagem: Counter[str] = Counter()
    for texto in paginas:
        # Só as bordas: uma frase repetida no miolo é conteúdo, não moldura.
        linhas = [l.strip() for l in texto.splitlines() if l.strip()]
        contagem.update(set(linhas[:3] + linhas[-3:]))

    minimo = max(3, int(len(paginas) * _FRACAO_MOLDURA))
    return {
        linha
        for linha, n in contagem.items()
        if n >= minimo and len(linha) <= _MAXIMO_MOLDURA
    }


def _limpar(texto: str, moldura: set[str]) -> str:
    """Normalização mínima: tira moldura, junta a palavra partida, enxuga espaço."""
    linhas = []
    for linha in texto.splitlines():
        enxuta = re.sub(r"[ \t\xa0]+", " ", linha).strip()
        if not enxuta or _RE_LINHA_VAZIA.match(enxuta):
            continue
        if enxuta in moldura:
            continue
        # Cabeçalho de folha varia o número a cada página e escapa da moldura.
        if _RE_FOLHA.search(enxuta) and len(enxuta) < 60:
            continue
        linhas.append(enxuta)

    junto = "\n".join(linhas)
    junto = _RE_HIFENIZACAO.sub(r"\1\2", junto)
    return junto.strip()


def paginas_do_pdf(conteudo: bytes) -> list[Pagina]:
    """Converte o PDF em páginas de texto normalizado."""
    import fitz  # importado aqui: só a ingestão precisa do PyMuPDF

    with fitz.open(stream=io.BytesIO(conteudo), filetype="pdf") as documento:
        brutas = [pagina.get_text() for pagina in documento]

    moldura = _repetidas(brutas)
    paginas: list[Pagina] = []
    for indice, bruta in enumerate(brutas, start=1):
        bruta = corrigir_mojibake(bruta)
        achado = _RE_FOLHA.search(bruta[:400])
        limpa = _limpar(bruta, moldura)
        if not limpa:
            continue  # página em branco ou só moldura
        paginas.append(
            Pagina(
                numero=indice,
                folha=int(achado.group(1)) if achado else None,
                texto=limpa,
            )
        )
    return paginas


# ---------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------


async def coletar(
    config,
    armazenamento,
    *,
    tipo=None,
    max_documentos: int | None = None,
    ao_progresso=None,
) -> tuple[int, int, int]:
    """Baixa o inteiro teor dos documentos já catalogados que ainda não o têm.

    Retorna (documentos, páginas, falhas). É retomável por construção: a fila
    é montada a partir do que falta, então interromper e recomeçar continua de
    onde parou.
    """
    from .http import Cliente, ErroHttp

    pendentes = armazenamento.sem_inteiro_teor(tipo=tipo)
    if max_documentos is not None:
        pendentes = pendentes[:max_documentos]

    log.info("Documentos sem inteiro teor: %d", len(pendentes))
    documentos = paginas_gravadas = falhas = 0

    async with Cliente(config) as cliente:
        for documento in pendentes:
            url = url_do_acordao(documento.numero, documento.ano)
            try:
                resposta = await cliente.obter(url)
            except ErroHttp as erro:
                log.warning("Falha em %s: %s", documento.id, erro)
                armazenamento.marcar_visitado(url, "erro", str(erro))
                falhas += 1
                continue

            tipo_conteudo = resposta.headers.get("content-type", "")
            if "pdf" not in tipo_conteudo.lower():
                # O portal responde 200 com página de erro quando o documento
                # não está publicado; sem esta checagem, ela viraria "texto".
                log.warning("%s não devolveu PDF (%s)", documento.id, tipo_conteudo)
                armazenamento.marcar_visitado(url, "sem_pdf", tipo_conteudo)
                falhas += 1
                continue

            try:
                paginas = paginas_do_pdf(resposta.content)
            except Exception as erro:  # noqa: BLE001 - PDF de terceiro, formato imprevisível
                log.warning("Não foi possível ler o PDF de %s: %s", documento.id, erro)
                armazenamento.marcar_visitado(url, "ilegivel", str(erro))
                falhas += 1
                continue

            if not paginas:
                log.warning("%s: PDF sem texto aproveitável", documento.id)
                armazenamento.marcar_visitado(url, "sem_texto")
                falhas += 1
                continue

            paginas_gravadas += armazenamento.gravar_paginas(documento.id, paginas)
            armazenamento.marcar_visitado(url, "ok")
            documentos += 1
            if ao_progresso and documentos % 25 == 0:
                ao_progresso(documentos, paginas_gravadas, falhas)

    return documentos, paginas_gravadas, falhas
