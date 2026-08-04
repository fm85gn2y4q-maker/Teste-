"""Extração das referências citadas — normas, súmulas, ONs e acórdãos.

O regex de norma repete uma correção que custou caro no acervo da PGE-RJ:
alternância é preguiçosa à esquerda, e `(\\d{1,3}(?:\\.\\d{3})*|\\d{1,6})` casa
"866" dentro de "8666" sem nunca tentar a segunda alternativa. A primeira
alternativa exige o grupo de milhar; a segunda cobre o número simples.
"""

from __future__ import annotations

import re

_NUM = r"(\d{1,3}(?:\.\d{3})+|\d{1,6})"

# Espécie normativa seguida de número e, quase sempre, ano.
_NORMA = re.compile(
    r"(?i)\b(lei\s+complementar|lei|decreto-lei|decreto|medida\s+provisória|"
    r"instrução\s+normativa|portaria\s+normativa|portaria|resolução|"
    r"emenda\s+constitucional)\s*"
    r"(?:n?[ºo°.]{0,2}\s*)?" + _NUM + r"\s*(?:,?\s*de\s*[^,;)\n]{0,40}?)?"
    r"(?:/|\s+de\s+|\s*,\s*de\s+)?(\d{4}|\d{2})?\b")

_ON = re.compile(
    r"(?i)\borienta[çc][ãa]o\s+normativa\s*(?:AGU|CNU/CGU/AGU|CGU)?\s*"
    r"n?[ºo°.]{0,2}\s*(\d{1,3})\s*(?:/\s*(\d{4}))?")

_SUMULA = re.compile(
    r"(?i)\bs[úu]mula\s+(vinculante\s+)?(?:d[aeo]\s+)?"
    r"(AGU|STF|STJ|TST|TCU)?\s*n?[ºo°.]{0,2}\s*(\d{1,4})")

_ACORDAO = re.compile(
    r"(?i)\bac[óo]rd[ãa]o\s+n?[ºo°.]{0,2}\s*" + _NUM +
    r"\s*/\s*(\d{4})\s*[-–]?\s*(TCU|STF|STJ)?"
    r"(?:\s*[-–]?\s*(Plen[áa]rio|Primeira\s+C[âa]mara|Segunda\s+C[âa]mara))?")

_PARECER_AGU = re.compile(
    r"(?i)\bparecer\s+(?:n?[ºo°.]{0,2}\s*)?(\d{1,5})\s*/\s*(\d{4})\s*/\s*"
    r"([A-ZÇÃÉ\-]{2,12})(?:/[A-Z\-]{2,8})*")

# Enunciados normativos do TCU e da AGU costumam vir sem espécie, no meio da
# frase ("art. 3º da 14.133"). Não se tenta adivinhar: sem espécie, não conta.

MESES = {"janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5,
         "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
         "novembro": 11, "dezembro": 12}


def _ano(bruto: str | None) -> str | None:
    if not bruto:
        return None
    if len(bruto) == 4:
        return bruto
    n = int(bruto)
    return str(1900 + n) if n > 30 else str(2000 + n)


def extrair(texto: str) -> dict[tuple[str, str], int]:
    """Devolve {(especie, referencia): ocorrências}."""
    achados: dict[tuple[str, str], int] = {}

    def somar(especie: str, referencia: str) -> None:
        chave = (especie, referencia)
        achados[chave] = achados.get(chave, 0) + 1

    for m in _NORMA.finditer(texto):
        especie = re.sub(r"\s+", " ", m.group(1)).title()
        numero = m.group(2)
        ano = _ano(m.group(3))
        somar("norma", f"{especie} {numero}/{ano}" if ano else f"{especie} {numero}")

    for m in _ON.finditer(texto):
        numero, ano = m.group(1), m.group(2)
        somar("orientacao_normativa",
              f"Orientação Normativa AGU nº {int(numero)}/{ano}" if ano
              else f"Orientação Normativa AGU nº {int(numero)}")

    for m in _SUMULA.finditer(texto):
        vinculante, corte, numero = m.group(1), m.group(2), m.group(3)
        rotulo = "Súmula Vinculante" if vinculante else "Súmula"
        alvo = f"{rotulo} {corte} nº {int(numero)}" if corte else f"{rotulo} nº {int(numero)}"
        somar("sumula", alvo)

    for m in _ACORDAO.finditer(texto):
        numero, ano, corte, colegiado = m.groups()
        alvo = f"Acórdão {numero}/{ano}"
        if corte:
            alvo += f"-{corte.upper()}"
        if colegiado:
            alvo += f" ({re.sub(r'\\s+', ' ', colegiado)})"
        somar("acordao", alvo)

    for m in _PARECER_AGU.finditer(texto):
        numero, ano, unidade = m.groups()
        somar("parecer_interno", f"PARECER n. {int(numero)}/{ano}/{unidade.upper()}")

    return achados
