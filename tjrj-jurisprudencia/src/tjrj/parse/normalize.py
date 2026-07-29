"""Normalização de nomes, órgãos e números de processo.

Sem isto, o acervo tem três "Décima Câmara Cível" e cinco grafias do mesmo
desembargador — e nenhuma pergunta agregada ("como esta câmara decide?",
"qual o entendimento deste relator?") tem resposta confiável.
"""

from __future__ import annotations

import re
import unicodedata

# Títulos e ruídos que aparecem colados ao nome nos acórdãos.
# A ordem importa: alternativas mais longas primeiro, senão "relator" casa
# antes de "relator designado" e deixa "designado" pendurado no nome.
TITULOS = (
    r"desembargador(?:a)?(?:\s+federal)?",
    r"des(?:emberg\.|embarg\.|a\b|\.)",
    r"dr(?:a)?\.?",
    r"exmo(?:\.|a)?\s*sr(?:\.|a)?",
    r"ju[ií]z(?:a)?(?:\s+de\s+direito)?(?:\s+convocad[oa])?",
    r"ministr[oa]",
    r"relator(?:a)?\s+designad[oa]",
    r"relator(?:a)?",
    r"revisor(?:a)?",
    r"vogal",
    r"presidente",
)
_RE_TITULO = re.compile(r"^(?:%s)\s*[:\-–]?\s*" % "|".join(TITULOS), re.IGNORECASE)
_RE_TITULO_FIM = re.compile(r"\s*[-–,]?\s*(?:%s)\s*$" % "|".join(TITULOS), re.IGNORECASE)
_RE_ESPACO = re.compile(r"\s+")
_RE_NAO_NOME = re.compile(r"[^A-Za-zÀ-ÖØ-öø-ÿ' ]+")
_RE_NAO_TEXTO = re.compile(r"[^0-9A-Za-zÀ-ÖØ-öø-ÿ ]+")

# Preposições ficam minúsculas na forma canônica.
_MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "em", "del", "di", "van", "von"}

ROMANOS = {
    "primeira": "1", "segunda": "2", "terceira": "3", "quarta": "4", "quinta": "5",
    "sexta": "6", "setima": "7", "oitava": "8", "nona": "9", "decima": "10",
    "vigesima": "20", "trigesima": "30",
}


def sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def chave(texto: str) -> str:
    """Chave de comparação de nomes: sem acento, sem dígito, minúscula."""
    t = sem_acento(texto or "").lower()
    t = _RE_NAO_NOME.sub(" ", t)
    return _RE_ESPACO.sub(" ", t).strip()


def chave_texto(texto: str) -> str:
    """Como `chave`, mas preserva dígitos — o que órgãos exigem ('10ª Câmara')."""
    t = sem_acento(texto or "").lower()
    t = _RE_NAO_TEXTO.sub(" ", t)
    return _RE_ESPACO.sub(" ", t).strip()


def limpar_nome(bruto: str) -> str:
    """Remove títulos, cargos e pontuação de um nome de julgador."""
    nome = _RE_ESPACO.sub(" ", (bruto or "").strip().strip(".,;:-–—"))
    anterior = None
    while nome and nome != anterior:  # títulos podem vir empilhados
        anterior = nome
        nome = _RE_TITULO.sub("", nome).strip()
        nome = _RE_TITULO_FIM.sub("", nome).strip()
        nome = nome.strip(".,;:-–—").strip()
    return nome


def nome_canonico(bruto: str) -> str:
    """Forma de exibição: 'JOÃO DA SILVA' -> 'João da Silva'."""
    nome = limpar_nome(bruto)
    partes = []
    for i, p in enumerate(nome.split()):
        base = sem_acento(p).lower()
        partes.append(p.lower() if i and base in _MINUSCULAS else p.capitalize())
    return " ".join(partes)


def chave_julgador(bruto: str) -> str:
    """Chave de deduplicação de julgador."""
    return chave(limpar_nome(bruto))


def chave_orgao(bruto: str) -> str:
    """Normaliza órgão julgador.

    'DÉCIMA CÂMARA CÍVEL', '10ª Câmara Cível' e '10a. Camara Civel' colapsam
    na mesma chave.
    """
    t = chave_texto(bruto)
    t = re.sub(r"\b(\d+)\s*[ºªoa]\.?\b", r"\1", t)
    for extenso, numero in ROMANOS.items():
        t = re.sub(rf"\b{extenso}\b", numero, t)
    # "vigesima primeira" -> "20 1" -> "21"
    t = re.sub(r"\b(\d0) (\d)\b", lambda m: str(int(m.group(1)) + int(m.group(2))), t)
    t = re.sub(r"\bcamara\s+de\s+direito\b", "camara", t)
    return _RE_ESPACO.sub(" ", t).strip()


_RE_CNJ = re.compile(r"(\d{7})[-.]?(\d{2})[.\-]?(\d{4})[.\-]?(\d)[.\-]?(\d{2})[.\-]?(\d{4})")


def numero_cnj(bruto: str) -> str | None:
    """Extrai e formata o número único CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO."""
    if not bruto:
        return None
    m = _RE_CNJ.search(re.sub(r"\s+", "", bruto))
    if not m:
        return None
    n, d, a, j, tr, o = m.groups()
    return f"{n}-{d}.{a}.{j}.{tr}.{o}"


def cnj_valido(numero: str) -> bool:
    """Confere o dígito verificador (módulo 97 base 10, ISO 7064)."""
    so_digitos = re.sub(r"\D", "", numero or "")
    if len(so_digitos) != 20:
        return False
    n, d, resto = so_digitos[:7], so_digitos[7:9], so_digitos[9:]
    return int(f"{n}{resto}{d}") % 97 == 1
