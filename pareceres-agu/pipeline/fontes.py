"""Clientes das três fontes públicas do acervo consultivo da AGU.

Cada fonte tem uma forma própria e um risco próprio, e por isso um cliente
próprio. O que elas têm em comum é o que o resto do pipeline consome: uma lista
de dicionários com texto e metadado de autoridade.

    CONUNI    manifestações de uniformização (Câmaras Nacionais Temáticas)
    ONS       Orientações Normativas da AGU
    SUMULAS   Súmulas da AGU

Nenhuma exige autenticação. Todas são páginas ou serviços públicos.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (acervo-consultivo-agu; coleta de atos publicos)"}

CONUNI_API = "https://cgu.agu.gov.br/cgi-bin/sapiens_com/relsapiens/coleta.py"
ONS_URL = "https://www.gov.br/agu/pt-br/composicao/cgu/cgu/onsagu"
SUMULAS_URL = "https://www.gov.br/agu/pt-br/composicao/cgu/cgu/sumula"

# Como o CONUNI resolve o link do inteiro teor, conforme `origem_manifestacao`.
ORIGENS = {
    2: "https://sapiens.agu.gov.br/valida_publico?id=%s",
    3: "https://cgu.agu.gov.br/decor/arquivos/%s",
}


def _abrir(url: str, dados: bytes | None = None, tentativas: int = 3,
           timeout: int = 180) -> bytes:
    ultimo: Exception | None = None
    for n in range(tentativas):
        try:
            req = urllib.request.Request(url, data=dados, headers=dict(UA))
            if dados is not None:
                req.add_header("Content-Type", "application/x-www-form-urlencoded")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # rede instável é rotina; não vale abortar a coleta
            ultimo = e
            time.sleep(2 * (n + 1))
    raise ultimo  # type: ignore[misc]


def _texto(bruto: str) -> str:
    """HTML → texto, preservando a quebra de parágrafo que separa os incisos."""
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", bruto)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(p|div|li|h[1-6])>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    linhas = [re.sub(r"[ \t ]+", " ", l).strip() for l in t.split("\n")]
    return "\n".join(l for l in linhas if l)


# --------------------------------------------------------------------- CONUNI

def conuni() -> list[dict]:
    """O catálogo inteiro do CONUNI numa requisição.

    `script=53, base=1` é a consulta que a própria página de consulta pública
    dispara ao carregar. Não há paginação: vêm todas as manifestações de uma vez.
    """
    corpo = urllib.parse.urlencode({
        "script": "53", "base": "1", "sqlpronto": "VAZIO",
        "param1": "NULL", "param2": "NULL", "param3": "NULL",
        "param4": "NULL", "param5": "NULL",
    }).encode()
    resposta = json.loads(_abrir(CONUNI_API, corpo).decode("utf-8", "ignore"))
    if resposta.get("erro") != "OK":
        raise RuntimeError(f"CONUNI recusou a consulta: {resposta.get('erro')}")
    registros = resposta["info"]
    for r in registros:
        r["url_inteiro_teor"] = url_manifestacao(
            r.get("origem_manifestacao"), r.get("link_manifestacao"))
    return registros


def url_manifestacao(origem, link) -> str | None:
    """Resolve o endereço do inteiro teor a partir de origem + link.

    origem 1 é 'internet': o link já é a URL. origem 0 e vazio não têm arquivo.
    """
    if not link:
        return None
    try:
        origem = int(origem)
    except (TypeError, ValueError):
        return None
    if origem == 1:
        return link if str(link).startswith("http") else None
    molde = ORIGENS.get(origem)
    return (molde % link) if molde else None


# ------------------------------------------------------------------------ ONs

# A página das ONs é uma lista de cartões. O que decide a leitura NÃO está no
# enunciado: está no parêntese do título. "(cancelada)", "(revogada)" e "(nova
# redação na ON 77/2023)" aparecem ali, e nesses cartões o corpo vem VAZIO —
# uma ON revogada e uma ON íntegra têm o mesmo aspecto para quem só lê o corpo.
_TITULO = re.compile(r'(?is)<div[^>]*class="[^"]*on-titulo[^"]*"[^>]*>(.*?)</div>')
_REGIME = re.compile(r'(?is)<span[^>]*class="[^"]*on-regime[^"]*"[^>]*>(.*?)</span>')
_CORPO = re.compile(r'(?is)<div[^>]*class="[^"]*on-corpo[^"]*"[^>]*>(.*?)</div>\s*(?:<div[^>]*class="[^"]*on-meta|</div>)')
_META = re.compile(r'(?is)<div[^>]*class="[^"]*on-meta[^"]*"[^>]*>(.*?)</div>')
_LINK = re.compile(r'(?is)<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>')
_NUMERO = re.compile(r"(?i)orienta[çc][ãa]o\s+normativa\s*n?[ºo°]?\s*(\d+)\s*/\s*(\d{4})")
_CNU_ATO = re.compile(r"(?i)orienta[çc][ãa]o\s+normativa\s+CNU/CGU/AGU\s*n?[ºo°]?\s*(\d+)")
_PARENTESE = re.compile(r"\(([^()]*)\)\s*$")

# Situações que o título declara entre parênteses. A chave é o que se procura
# no texto do parêntese; o valor é o rótulo que vai para o banco.
_SITUACOES = (
    ("cancelad", "cancelada"),
    ("revogad", "revogada"),
    ("nova redação", "nova redação dada por outro ato"),
    ("prejudicad", "prejudicada"),
    ("suspens", "suspensa"),
)

_PLONE = "https://www.gov.br/agu/pt-br/composicao/cgu/cgu/"


def _links(bloco: str) -> list[dict]:
    saida = []
    for url, rotulo in _LINK.findall(bloco):
        url = html.unescape(url).strip()
        if url.startswith("resolveuid/"):
            url = _PLONE + url
        saida.append({"rotulo": _texto(rotulo) or None, "url": url})
    return saida


def _situacao(titulo: str) -> str | None:
    m = _PARENTESE.search(titulo.strip())
    if not m:
        return None
    dentro = m.group(1).strip()
    if not any(chave in dentro.lower() for chave, _ in _SITUACOES):
        return None
    # O parêntese mistura a situação com rótulos de link ("fundamentação",
    # "redação original"), que não dizem nada sobre o estado do ato. Ficam de
    # fora: o campo tem de responder "o que aconteceu com esta ON", e mais nada.
    pedacos = [p.strip(" ,;|") for p in re.split(r"[|,;]", dentro)]
    uteis = [p for p in pedacos
             if p and not re.fullmatch(r"(?i)funda\w*|reda[çc][ãa]o original", p)]
    limpo = ", ".join(uteis) or dentro
    # devolve o texto literal quando ele diz mais que o rótulo: "nova redação
    # na ON 77/2023" identifica o ato novo, e é isso que se vai ler.
    return limpo


def _cnu(bloco: str) -> list[dict]:
    """O bloco final da página: as ONs da extinta Câmara Nacional de
    Uniformização, que a AGU declara terem 'a mesma eficácia das ONs acima'.

    Vêm todas dentro de um único cartão, um parágrafo por ato, e os parágrafos
    seguintes sem link são o enunciado ou a observação do ato anterior.
    """
    atos: list[dict] = []
    for par in re.findall(r"(?is)<p>(.*?)</p>", bloco):
        texto = _texto(par)
        m = _CNU_ATO.search(texto)
        if m:
            atos.append({
                "especie": "Orientação Normativa CNU",
                "numero": int(m.group(1)),
                "ano": None,
                "citacao": re.sub(r"\s+", " ", texto.split("(")[0]).strip(" ,"),
                "grupo": "Câmara Nacional de Uniformização (extinta) — mesma eficácia das ONs da AGU",
                "situacao_declarada": _situacao(texto),
                "regime_declarado": None,
                "texto": "",
                "links": _links(par),
                "url_publicacao": None,
            })
            ma = re.search(r"de\s+\d{1,2}\s+de\s+\w+\s+de\s+(\d{4})", texto)
            if ma:
                atos[-1]["ano"] = int(ma.group(1))
        elif atos:
            if texto.lower().startswith("obs"):
                anterior = atos[-1].get("situacao_declarada")
                atos[-1]["situacao_declarada"] = "; ".join(
                    x for x in (anterior, texto) if x)
                atos[-1]["links"].extend(_links(par))
            else:
                atos[-1]["texto"] = (atos[-1]["texto"] + "\n" + texto).strip()
    return atos


def ons() -> list[dict]:
    bruto = _abrir(ONS_URL).decode("utf-8", "ignore")
    cartoes = bruto.split('<div class="on-card"')[1:]
    saida: list[dict] = []
    for bloco in cartoes:
        mt = _TITULO.search(bloco)
        titulo_html = mt.group(1) if mt else ""
        titulo = _texto(titulo_html)
        corpo = _CORPO.search(bloco)
        meta = _META.search(bloco)
        texto = _texto(corpo.group(1)) if corpo else ""

        if "mesma eficácia das ONs" in titulo:
            saida.extend(_cnu(bloco))
            continue

        mn = _NUMERO.search(titulo)
        numero_inferido = False
        if mn:
            numero, ano = int(mn.group(1)), int(mn.group(2))
        else:
            # A própria página tem um cartão cujo título perdeu o número e
            # ficou só "Fundamentação". O número se infere pela posição na
            # sequência, que é confiável porque a lista é ordenada.
            #
            # O ANO, NÃO. Copiar o ano da ON anterior parecia inofensivo e
            # estava errado: a vizinha de cima é de 2024 e a de baixo, de 2025.
            # Ano inventado numa citação é erro que o cliente paga, e sai da
            # ferramenta com o mesmo aspecto de um dado colhido. Fica nulo.
            anterior = next((d for d in reversed(saida) if d.get("numero")), None)
            if not anterior or not texto:
                continue
            numero, ano = anterior["numero"] + 1, None
            numero_inferido = True

        regime = _REGIME.search(bloco)
        registro = {
            "especie": "Orientação Normativa",
            "numero": numero,
            "ano": ano,
            "citacao": (f"Orientação Normativa AGU nº {numero}/{ano}" if ano else
                        f"Orientação Normativa AGU nº {numero} "
                        f"(ano não identificado na fonte)"),
            "grupo": "Advocacia-Geral da União",
            "situacao_declarada": _situacao(titulo),
            "regime_declarado": _texto(regime.group(1)) if regime else None,
            "texto": texto,
            "links": _links(titulo_html) + (_links(meta.group(1)) if meta else []),
            "url_publicacao": None,
        }
        primeiro = _LINK.search(titulo_html)
        if primeiro:
            registro["url_publicacao"] = html.unescape(primeiro.group(1))
        if numero_inferido:
            registro["numero_inferido"] = True
            vizinha = f"{anterior['numero']}/{anterior['ano']}" if anterior else "?"
            registro["aviso"] = (
                f"O título desta ON na página da AGU traz apenas 'Fundamentação', "
                f"sem número nem ano. O número {numero} foi inferido pela posição "
                f"na sequência, logo após a ON {vizinha}, e o ANO não pôde ser "
                f"determinado — as ONs vizinhas são de anos diferentes. NÃO cite "
                f"sem conferir número e ano no ato, pelo link.")
        saida.append(registro)
    return saida


# -------------------------------------------------------------------- Súmulas

# A página das súmulas é texto corrido: cabeçalho, enunciado entre aspas,
# referências. O cabeçalho é o único marcador confiável — e nem ele é uniforme:
# "SÚMULA Nº 49, DE 20 DE ABRIL DE 2010" convive com "SÚMULA Nº 50, 13 DE
# AGOSTO DE 2010", sem o "DE". Exigir o "DE" perdia duas súmulas em silêncio.
_SUM_CAB = re.compile(
    r"(?im)^\s*S[ÚU]MULA\s+N?[ºo°]?\s*(\d+)\s*,\s*(?:DE\s+)?(\d.*?)\s*$")
# O enunciado vem entre aspas; o resto do bloco é publicação e referências.
_SUM_ENUNCIADO = re.compile(r'["“]([^"”]{40,})["”]')
_SUM_REVOGADA = re.compile(
    r"(?im)^\s*\(?\*?\)?\s*(revogad\w[^\n]*|cancelad\w[^\n]*|"
    r"redação alterada[^\n]*|prejudicad\w[^\n]*)$")


def sumulas() -> list[dict]:
    texto = _texto(_abrir(SUMULAS_URL).decode("utf-8", "ignore"))
    marcas = list(_SUM_CAB.finditer(texto))
    saida: list[dict] = []
    for i, m in enumerate(marcas):
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        corpo = texto[m.end():fim].strip()
        numero = int(m.group(1))
        data = m.group(2).strip()
        ma = re.search(r"(\d{4})", data)
        enunciado = _SUM_ENUNCIADO.search(corpo)
        situacao = _SUM_REVOGADA.search(corpo)
        saida.append({
            "especie": "Súmula",
            "numero": numero,
            "ano": int(ma.group(1)) if ma else None,
            "citacao": f"Súmula da AGU nº {numero}",
            "grupo": "Advocacia-Geral da União",
            "data_por_extenso": data,
            "situacao_declarada": situacao.group(1).strip() if situacao else None,
            "enunciado": enunciado.group(1).strip() if enunciado else None,
            "texto": corpo,
        })
    return saida
