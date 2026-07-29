"""Extração da composição do julgamento a partir do inteiro teor.

Este é o dado que praticamente nenhuma base pública entrega e que o projeto
existe para ter: **quem mais julgou além do relator**, em que qualidade, e
quem ficou vencido.

Ele quase nunca vem em campo estruturado. Vem em prosa, em três lugares do
acórdão:

1. o cabeçalho/autuação ("Relator: Des. Fulano");
2. a fórmula do acórdão ("ACORDAM os Desembargadores que integram a Décima
   Câmara Cível ... por maioria, vencido o Desembargador Beltrano");
3. o bloco de assinatura e a ata ("Votaram os Desembargadores ...",
   "Presidiu o julgamento ...").

A estratégia é ler os três, unir por julgador e ficar com o papel de maior
autoridade. Cada participação carrega `confianca` e `fonte`, porque uma
extração por regex sobre texto de OCR não é o mesmo fato que um campo vindo
do sistema — e quem for citar precisa saber a diferença.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Protocol

from .normalize import chave_julgador, nome_canonico

# Um nome próprio em caixa alta ou capitalizado, com preposições.
# Só espaços — nunca `\s`: em PDF de acórdão a linha seguinte quase sempre
# começa com outra palavra capitalizada ("ACORDAM", "EMENTA") e um `\s+`
# aqui devora o documento inteiro dentro do nome.
_PALAVRA = r"[A-ZÀ-Ý][A-Za-zÀ-ÿ'´`^~]+"
_LIGACAO = r"(?:d[aeoi]s?|e|del|van|von|neto|filho|j[úu]nior)"
NOME = rf"{_PALAVRA}(?:[ ]+(?:{_LIGACAO}|{_PALAVRA})){{1,6}}"
# Os padrões abaixo são compilados com re.I (os acórdãos oscilam entre
# "Relator", "RELATOR" e "relator"), mas o nome PRECISA continuar sensível a
# caixa — é a capitalização que separa um nome próprio do resto da frase.
# `(?-i:...)` desliga o flag só nesse trecho.
NOME_CS = rf"(?-i:{NOME})"
TITULO = (
    r"(?:Des(?:embargador)?(?:a)?\.?|Dr(?:a)?\.?|Ju[ií]z(?:a)?(?:\s+Convocad[oa])?|Ministr[oa])"
)
_T = rf"(?:{TITULO}[ ]*)?"
# Palavras de ligação que antecedem o nome: "designado para o acórdão **o**
# Desembargador Fulano", "Votaram **os Srs.** Desembargadores Fulano...".
# O `\b` no fim não é decorativo: sem ele, o "a" de `as?` casa com o "A" de
# "Antônio" e o nome entra no acervo decapitado.
_PREAMBULO = (
    r"(?:[ ]+(?:os?|as?|Srs?\.?|Sras?\.?|Senhor(?:es|as)?|Excelent[íi]ssim[oa]s?|"
    r"Desembargador(?:es|as)?|Ju[ií]z(?:es|as)?|Ministr[oa]s?|Doutor(?:es|as)?)\b\.?)*"
)

PAPEIS = ("relator", "relator_designado", "revisor", "vogal", "presidente")

# Precedência quando o mesmo julgador aparece com papéis diferentes.
_PESO = {"relator_designado": 5, "relator": 4, "revisor": 3, "presidente": 2, "vogal": 1}


@dataclass
class Participacao:
    nome: str
    nome_norm: str
    papel: str
    vencido: bool = False
    ordem: int | None = None
    confianca: float = 0.8
    fonte: str = "regex"


class Desambiguador(Protocol):
    """Ponto de extensão para um passo de LLM sobre os casos duvidosos.

    Só deve ser chamado quando a regex falha (ver `precisa_revisao`). Rodar
    LLM em milhões de acórdãos é caro e desnecessário: a fórmula do acórdão
    é padronizada em >90% dos casos.
    """

    def __call__(self, trecho: str) -> list[Participacao]: ...


# --- padrões ----------------------------------------------------------------

_P_RELATOR = [
    re.compile(rf"\bRelator(?:a)?\s*[:\-–]\s*{_T}(?P<n>{NOME_CS})", re.I),
    re.compile(rf"\bnos\s+termos\s+do\s+voto\s+d[oa]\s+{_T}Relator(?:a)?\b", re.I),
    # Bloco de assinatura: nome numa linha, "Relator" na seguinte.
    re.compile(rf"^{_T}(?P<n>{NOME_CS})\s*$\s*^\s*Relator(?:a)?\s*$", re.I | re.M),
]

_P_RELATOR_DESIGNADO = [
    re.compile(
        rf"\bRelator(?:a)?[ ]+designad[oa](?:[ ]+p(?:ar)?a[ ]+o[ ]+ac[óo]rd[ãa]o)?"
        rf"[ ]*[:\-–]?{_PREAMBULO}[ ]*{_T}(?P<n>{NOME_CS})",
        re.I,
    ),
]

_P_REVISOR = [re.compile(rf"\bRevisor(?:a)?[ ]*[:\-–][ ]*{_T}(?P<n>{NOME_CS})", re.I)]

_P_PRESIDENTE = [
    re.compile(
        rf"\bPresidi(?:u|ram)[ ]+(?:o[ ]+julgamento|a[ ]+sess[ãa]o|os[ ]+trabalhos)"
        rf"{_PREAMBULO}[ ]*{_T}(?P<n>{NOME_CS})",
        re.I,
    ),
    re.compile(rf"\bPresidente[ ]*[:\-–][ ]*{_T}(?P<n>{NOME_CS})", re.I),
]

# Listas: "Votaram os Desembargadores X, Y e Z."
_P_LISTA = [
    re.compile(
        r"\b(?:Votaram|Participaram[ ]+do[ ]+julgamento|Presentes[ ]+ao[ ]+julgamento|"
        r"Compuseram[ ]+a[ ]+Turma[ ]+Julgadora|Acompanharam[ ]+o[ ]+voto)"
        + _PREAMBULO
        + r"[ ]*[:\-–]?[ ]*(?P<lista>[^.;]{5,600})",
        re.I,
    ),
]

_P_VENCIDO = [
    re.compile(rf"\bvencid[oa]s?{_PREAMBULO}[ ]*{_T}(?P<lista>[^.;]{{3,300}})", re.I),
    re.compile(rf"\bdivergiu{_PREAMBULO}[ ]*{_T}(?P<n>{NOME_CS})", re.I),
]

_SEPARADOR = re.compile(r",|\se\s|\/", re.I)


def extrair(texto: str, *, desambiguar: Desambiguador | None = None) -> list[Participacao]:
    """Devolve a composição do julgamento encontrada no texto."""
    if not texto:
        return []
    texto = _preparar(texto)
    achados: list[Participacao] = []

    for papel, padroes, conf in (
        ("relator_designado", _P_RELATOR_DESIGNADO, 0.9),
        ("relator", _P_RELATOR, 0.9),
        ("revisor", _P_REVISOR, 0.85),
        ("presidente", _P_PRESIDENTE, 0.8),
    ):
        for p in padroes:
            for m in p.finditer(texto):
                nome = (m.groupdict().get("n") or "").strip()
                if _nome_plausivel(nome):
                    achados.append(_mk(nome, papel, conf))
            if any(a.papel == papel for a in achados):
                break  # o padrão mais específico já resolveu

    for p in _P_LISTA:
        for m in p.finditer(texto):
            for i, nome in enumerate(_quebrar_lista(m.group("lista"))):
                achados.append(_mk(nome, "vogal", 0.7, ordem=i))

    vencidos = {
        chave_julgador(n)
        for p in _P_VENCIDO
        for m in p.finditer(texto)
        for n in (
            _quebrar_lista(m.group("lista"))
            if "lista" in (m.groupdict() or {}) and m.groupdict().get("lista")
            else [m.groupdict().get("n") or ""]
        )
        if _nome_plausivel(n)
    }

    consolidado = _consolidar(achados, vencidos)

    if desambiguar is not None and precisa_revisao(consolidado):
        extra = desambiguar(texto[:8000])
        consolidado = _consolidar(consolidado + list(extra), vencidos)

    return consolidado


def precisa_revisao(participacoes: Iterable[Participacao]) -> bool:
    """Sinaliza o acórdão em que a regex claramente não deu conta.

    Sem relator, ou com relator sozinho num acórdão colegiado (que por
    definição tem três votantes), é caso de revisão.
    """
    lista = list(participacoes)
    if not any(p.papel in ("relator", "relator_designado") for p in lista):
        return True
    return len(lista) < 2


def _preparar(texto: str) -> str:
    # PDFs de acórdão quebram nomes em várias linhas e enchem de espaço duplo.
    texto = texto.replace("­", "").replace("\xa0", " ")
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    return texto


def _mk(nome: str, papel: str, conf: float, ordem: int | None = None) -> Participacao:
    return Participacao(
        nome=nome_canonico(nome),
        nome_norm=chave_julgador(nome),
        papel=papel,
        ordem=ordem,
        confianca=conf,
    )


_RE_SO_NOME = re.compile(rf"^{NOME}$")


def _nome_plausivel(nome: str) -> bool:
    """Aceita apenas o que se parece com nome de pessoa.

    O critério decisivo é a capitalização: "Carlos Eduardo Mota" passa,
    "que dava provimento parcial" não. Sem isso, toda oração subordinada
    que segue a vírgula do "vencido o Desembargador X, que ..." entra no
    acervo como se fosse julgador.
    """
    limpo = " ".join((nome or "").split())
    if len(limpo) < 5:
        return False
    if not _RE_SO_NOME.match(limpo):
        return False
    return len(chave_julgador(limpo).split()) >= 2


def _quebrar_lista(bruto: str) -> list[str]:
    itens = []
    # A lista costuma vir quebrada em várias linhas do PDF; aqui a linha
    # deixa de ser fronteira, ao contrário do que vale para NOME.
    achatado = " ".join((bruto or "").split())
    for pedaco in _SEPARADOR.split(achatado):
        nome = re.sub(rf"^[ ]*{TITULO}[ ]*", "", pedaco.strip(), flags=re.I).strip()
        nome = re.sub(r"^(?:os?|as?|Srs?\.?|Sras?\.?)[ ]+", "", nome, flags=re.I).strip()
        if _nome_plausivel(nome):
            itens.append(nome)
    return itens


def _consolidar(achados: list[Participacao], vencidos: set[str]) -> list[Participacao]:
    """Um julgador, um papel: o de maior peso. Marca os vencidos."""
    melhor: dict[str, Participacao] = {}
    for p in achados:
        atual = melhor.get(p.nome_norm)
        if atual is None or _PESO.get(p.papel, 0) > _PESO.get(atual.papel, 0):
            melhor[p.nome_norm] = p
    for norm, p in melhor.items():
        if norm in vencidos:
            p.vencido = True
    return sorted(
        melhor.values(),
        key=lambda p: (-_PESO.get(p.papel, 0), p.ordem if p.ordem is not None else 99, p.nome),
    )
