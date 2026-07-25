"""Extração de metadados a partir do texto/HTML dos documentos do TCE-RJ.

Estas funções trabalham sobre o *texto* do documento, não sobre a estrutura da
página. Isso é proposital: o layout do portal muda, mas a forma como o Tribunal
escreve "Acórdão nº 123/2020", "Processo nº 210.123-4/2019" ou "Relator:
Conselheiro Fulano" é estável. Quando a extração por seletor de CSS falha, o
pipeline ainda consegue recuperar os metadados a partir do texto corrido.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from .modelos import Documento, TipoDocumento, normalizar

# ---------------------------------------------------------------------------
# Expressões regulares de domínio
# ---------------------------------------------------------------------------

_ESPECIES = (
    r"ac[óo]rd[ãa]o|s[úu]mula|enunciado|delibera[çc][ãa]o|resolu[çc][ãa]o|"
    r"parecer\s+pr[ée]vio|decis[ãa]o|voto"
)

# "Acórdão nº 1.234/2020", "DELIBERAÇÃO Nº 277/2020", "Súmula 15"
_RE_ESPECIE_NUMERO = re.compile(
    rf"(?P<especie>{_ESPECIES})"
    r"[\s\-–:]*"
    r"(?:n[ºo°.]?\s*)?"
    # A forma com milhar exige o ponto; sem essa exigência "1234" casaria só
    # como "123" e o resto do número seria perdido.
    r"(?P<numero>\d{1,3}(?:\.\d{3})+|\d+)"
    r"(?:\s*[/\-]\s*(?P<ano>\d{2,4}))?",
    re.IGNORECASE,
)

# "Processo nº 210.123-4/2019", "TCE-RJ 104.567-9/22", "Proc. 100.123-0/2018"
_RE_PROCESSO = re.compile(
    r"(?:processo|proc\.?|tce[\-\s]?rj)\s*"
    r"(?:n[ºo°.]?\s*)?"
    r"(?P<numero>\d{3}\.\d{3}-\d(?:\s*/\s*\d{2,4})?)",
    re.IGNORECASE,
)

# Número de processo solto, sem rótulo (ex.: coluna de tabela)
_RE_PROCESSO_SOLTO = re.compile(r"\b\d{3}\.\d{3}-\d(?:\s*/\s*\d{2,4})?\b")

# O nome do relator nunca atravessa a quebra de linha: só espaço horizontal é
# aceito entre os tokens, senão a captura invade o rótulo seguinte
# ("Relator: Fulano\nSessão de ...").
_RE_RELATOR = re.compile(
    r"(?:relator[ao]?|rel\.?)[^\S\n]*[:\-–]?[^\S\n]*"
    r"(?:(?:conselheir[oa]|cons)\.?[^\S\n]+(?:substitut[oa][^\S\n]+)?)?"
    r"(?P<nome>[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\wÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç'.]*"
    r"(?:[^\S\n]+(?:d[aeo]s?[^\S\n]+)?[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\wÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç'.]*){0,5})",
    re.IGNORECASE,
)

# Rótulos que costumam seguir o nome na mesma linha e não fazem parte dele.
_PARADAS_RELATOR = (
    "sessao", "sessao de", "processo", "data", "publicacao", "ementa",
    "orgao", "plenario", "camara", "julgado", "acordao", "voto", "em",
)

_RE_DATA = re.compile(r"\b(?P<d>\d{1,2})[/\-.](?P<m>\d{1,2})[/\-.](?P<a>\d{2,4})\b")

_ORGAOS = (
    "plenário",
    "plenario",
    "primeira câmara",
    "segunda câmara",
    "primeira camara",
    "segunda camara",
    "1ª câmara",
    "2ª câmara",
    "conselho",
    "tribunal pleno",
)

_MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}

_RE_DATA_EXTENSO = re.compile(
    r"\b(?P<d>\d{1,2})\s+de\s+(?P<mes>[a-zç]+)\s+de\s+(?P<a>\d{4})\b", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Conversores básicos
# ---------------------------------------------------------------------------


# "Ã" e "Â" são o rastro da dupla codificação. Servem apenas como porta de
# entrada barata: em português correto elas também ocorrem ("ACÓRDÃO"), e quem
# decide de fato é a viabilidade da reconversão.
_RE_SUSPEITA = re.compile(r"[ÃÂ]")


def _suspeitas(texto: str) -> int:
    return len(_RE_SUSPEITA.findall(texto))


def corrigir_mojibake(texto: str) -> str:
    """Desfaz a dupla codificação de páginas servidas sem charset.

    Vários portais públicos entregam UTF-8 sem declarar o charset, e o
    navegador interpreta o conteúdo como cp1252/Latin-1. Sem esta correção o
    texto chega como "ACÃ“RDÃƒO NÂº" e nenhuma das expressões de extração casa.

    A reconversão só é aceita quando reduz o número de marcas suspeitas, de
    modo que texto já correto passe intacto: "ACÓRDÃO" não sobrevive ao
    round-trip (gera byte inválido em UTF-8) e é devolvido como está.
    """
    for _ in range(3):  # a dupla codificação pode estar aninhada
        if not _RE_SUSPEITA.search(texto):
            return texto

        melhor = None
        # cp1252 primeiro: é o que os navegadores usam de fato ao adivinhar, e
        # é o único que explica "Ó" virando "Ã“" (aspa tipográfica).
        for codec in ("cp1252", "latin-1"):
            try:
                candidato = texto.encode(codec).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if _suspeitas(candidato) < _suspeitas(texto):
                melhor = candidato
                break

        if melhor is None:
            return texto
        texto = melhor
    return texto


def html_para_texto(html: str) -> str:
    """Converte HTML em texto legível, preservando quebras de parágrafo."""
    sopa = BeautifulSoup(html, "lxml")
    for tag in sopa(["script", "style", "noscript"]):
        tag.decompose()
    texto = sopa.get_text("\n")
    texto = corrigir_mojibake(texto)
    texto = re.sub(r"[ \t\xa0]+", " ", texto)
    texto = re.sub(r"\n\s*\n\s*\n+", "\n\n", texto)
    return texto.strip()


def parse_data(valor: str | None) -> date | None:
    """Interpreta datas em dd/mm/aaaa, aaaa-mm-dd ou por extenso."""
    if not valor:
        return None
    texto = valor.strip()

    iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", texto)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None

    extenso = _RE_DATA_EXTENSO.search(texto)
    if extenso:
        mes = _MESES.get(normalizar(extenso.group("mes")))
        if mes:
            try:
                return date(int(extenso.group("a")), mes, int(extenso.group("d")))
            except ValueError:
                return None

    achado = _RE_DATA.search(texto)
    if not achado:
        return None
    dia, mes, ano = (int(achado.group("d")), int(achado.group("m")), int(achado.group("a")))
    ano = _expandir_ano(ano)
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def _expandir_ano(ano: int) -> int:
    """Converte ano de dois dígitos em quatro ('22' -> 2022)."""
    if ano >= 1000:
        return ano
    # O TCE-RJ foi criado em 1936; qualquer coisa acima de 36 é século XX.
    return 1900 + ano if ano > 36 else 2000 + ano


# ---------------------------------------------------------------------------
# Extratores de campo
# ---------------------------------------------------------------------------


def extrair_especie_e_numero(texto: str) -> tuple[TipoDocumento, str | None, int | None]:
    """Retorna (tipo, número, ano) a partir do cabeçalho do documento."""
    achado = _RE_ESPECIE_NUMERO.search(texto)
    if not achado:
        return TipoDocumento.INDEFINIDO, None, None

    tipo = TipoDocumento.de_texto(achado.group("especie"))
    numero = achado.group("numero").replace(".", "")
    ano_bruto = achado.group("ano")
    ano = _expandir_ano(int(ano_bruto)) if ano_bruto else None
    return tipo, numero, ano


def extrair_processo(texto: str) -> str | None:
    achado = _RE_PROCESSO.search(texto)
    if achado:
        return _normalizar_processo(achado.group("numero"))
    solto = _RE_PROCESSO_SOLTO.search(texto)
    return _normalizar_processo(solto.group(0)) if solto else None


def _normalizar_processo(numero: str) -> str:
    return re.sub(r"\s*/\s*", "/", re.sub(r"\s+", "", numero))


def extrair_relator(texto: str) -> str | None:
    achado = _RE_RELATOR.search(texto)
    if not achado:
        return None
    nome = achado.group("nome").strip(" .,;:")

    # Apara rótulos que vieram colados na mesma linha ("Fulano Sessão de").
    tokens = nome.split()
    while tokens and normalizar(tokens[-1]) in _PARADAS_RELATOR:
        tokens.pop()
    nome = " ".join(tokens)

    # Descarta capturas que na verdade pegaram a palavra seguinte do texto
    # corrido (ex.: "Relator" no fim de uma frase).
    if len(nome) < 3 or normalizar(nome) in {"conselheiro", "conselheira", "substituto"}:
        return None
    return nome


def extrair_orgao(texto: str) -> str | None:
    normalizado = normalizar(texto)
    for orgao in _ORGAOS:
        alvo = normalizar(orgao)
        if alvo in normalizado:
            return orgao.title()
    return None


def extrair_ementa(texto: str) -> str | None:
    """Isola o bloco de ementa.

    O padrão do Tribunal é o rótulo "EMENTA" seguido do texto até a próxima
    seção (RELATÓRIO, VOTO, ACORDAM etc.).
    """
    achado = re.search(r"\bement[ao]\b\s*[:\-–]?\s*", texto, re.IGNORECASE)
    if not achado:
        return None

    resto = texto[achado.end():]
    fim = re.search(
        r"\n\s*(?:relat[óo]rio|voto|acordam|ac[óo]rd[ãa]o|"
        r"decis[ãa]o|fundamenta[çc][ãa]o|dispositivo)\b",
        resto,
        re.IGNORECASE,
    )
    bloco = resto[: fim.start()] if fim else resto[:4000]
    bloco = re.sub(r"\s+", " ", bloco).strip(" .;:-–\n")
    return bloco or None


def extrair_assuntos(texto: str) -> list[str]:
    """Lê a linha de assuntos/descritores, quando presente."""
    achado = re.search(
        r"(?:assuntos?|descritores?|palavras[\-\s]chave|indexa[çc][ãa]o)\s*[:\-–]\s*(?P<v>[^\n]+)",
        texto,
        re.IGNORECASE,
    )
    if not achado:
        return []
    bruto = achado.group("v")
    partes = re.split(r"\s*[;/|]\s*|\s*,\s*", bruto)
    vistos: list[str] = []
    for parte in partes:
        limpo = parte.strip(" .;:-–")
        if limpo and normalizar(limpo) not in {normalizar(v) for v in vistos}:
            vistos.append(limpo)
    return vistos


# ---------------------------------------------------------------------------
# Montagem do documento
# ---------------------------------------------------------------------------


def documento_de_texto(
    texto: str,
    *,
    url: str | None = None,
    tipo_esperado: TipoDocumento | None = None,
) -> Documento:
    """Constrói um `Documento` a partir do texto integral.

    `tipo_esperado` vem do filtro usado na busca e serve de desempate quando o
    cabeçalho não identifica a espécie.
    """
    tipo, numero, ano = extrair_especie_e_numero(texto)
    if tipo is TipoDocumento.INDEFINIDO and tipo_esperado:
        tipo = tipo_esperado

    datas = _datas_rotuladas(texto)

    return Documento(
        tipo=tipo,
        numero=numero,
        ano=ano,
        processo=extrair_processo(texto),
        relator=extrair_relator(texto),
        orgao_julgador=extrair_orgao(texto),
        data_sessao=datas.get("sessao"),
        data_publicacao=datas.get("publicacao"),
        ementa=extrair_ementa(texto),
        inteiro_teor=texto,
        assuntos=extrair_assuntos(texto),
        url=url,
        fonte="tcerj",
    )


def _datas_rotuladas(texto: str) -> dict[str, date | None]:
    """Separa data de sessão/julgamento da data de publicação."""
    resultado: dict[str, date | None] = {}

    sessao = re.search(
        r"(?:sess[ãa]o|julgad[oa]\s+em|data\s+do\s+julgamento|em\s+sess[ãa]o\s+de)"
        r"[^\n\d]{0,40}(?P<v>\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|"
        r"\d{1,2}\s+de\s+[a-zç]+\s+de\s+\d{4})",
        texto,
        re.IGNORECASE,
    )
    if sessao:
        resultado["sessao"] = parse_data(sessao.group("v"))

    publicacao = re.search(
        r"(?:publica[çc][ãa]o|publicad[oa]\s+em|d\.?o\.?e\.?\s*(?:de)?)"
        r"[^\n\d]{0,40}(?P<v>\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|"
        r"\d{1,2}\s+de\s+[a-zç]+\s+de\s+\d{4})",
        texto,
        re.IGNORECASE,
    )
    if publicacao:
        resultado["publicacao"] = parse_data(publicacao.group("v"))

    return resultado


def documento_de_registro(
    registro: dict,
    *,
    tipo_esperado: TipoDocumento | None = None,
) -> Documento:
    """Converte um registro JSON da API em `Documento`.

    Os nomes de campo variam conforme o endpoint, então cada atributo é buscado
    por uma lista de apelidos plausíveis antes de cair na extração por texto.
    """
    def pegar(*chaves: str) -> str | None:
        for chave in chaves:
            for real, valor in registro.items():
                if normalizar(real) == normalizar(chave) and valor not in (None, ""):
                    return str(valor)
        return None

    numero = pegar("numero", "numeroAcordao", "nrDocumento", "numeroDocumento", "num")
    ano_bruto = pegar("ano", "exercicio", "anoDocumento")
    texto = pegar("inteiroTeor", "textoIntegral", "conteudo", "texto", "corpo")
    ementa = pegar("ementa", "resumo", "descricao")

    tipo = TipoDocumento.de_texto(
        pegar("tipo", "tipoDocumento", "especie", "natureza", "tipoAto")
    )
    if tipo is TipoDocumento.INDEFINIDO and tipo_esperado:
        tipo = tipo_esperado

    documento = Documento(
        tipo=tipo,
        numero=re.sub(r"\D", "", numero) or None if numero else None,
        ano=_expandir_ano(int(ano_bruto)) if ano_bruto and ano_bruto.isdigit() else None,
        processo=pegar("processo", "numeroProcesso", "nrProcesso", "proc"),
        relator=pegar("relator", "nomeRelator", "conselheiroRelator"),
        orgao_julgador=pegar("orgao", "orgaoJulgador", "colegiado", "sessaoTipo"),
        data_sessao=parse_data(pegar("dataSessao", "dataJulgamento", "data")),
        data_publicacao=parse_data(pegar("dataPublicacao", "dtPublicacao")),
        ementa=ementa,
        inteiro_teor=texto,
        url=pegar("url", "link", "urlDocumento"),
        url_pdf=pegar("urlPdf", "linkPdf", "arquivo", "pdf"),
        fonte="tcerj",
        bruto=registro,
    )

    # Completa lacunas com o que der para inferir do texto disponível.
    base = texto or ementa
    if base:
        documento.mesclar(documento_de_texto(base, tipo_esperado=tipo_esperado))
    return documento
