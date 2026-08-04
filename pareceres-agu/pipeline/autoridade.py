"""O grau de vinculação — a régua deste acervo.

Num acervo de jurisprudência o risco é a proveniência; num de legislação, a
vigência. Aqui é a **força vinculante**, e ela não está no texto: um parecer que
obriga toda a Administração Federal e um que obriga apenas os órgãos envolvidos
naquele processo têm exatamente o mesmo aspecto, o mesmo vocabulário e a mesma
estrutura. A diferença está no metadado, e é ela que decide se o documento
serve de fundamento ou só de argumento.

Medido no acervo, das 1.724 manifestações do CONUNI:

    Apenas órgãos envolvidos no processo      510
    Órgãos da CGU                             851
    Órgãos da AGU                             350
    Toda a Administração Pública Federal       12

Doze. Apresentar qualquer um dos outros 1.712 como vinculante da Administração
Federal inverte o documento.

Este módulo NÃO decide autoridade: ele traduz o que a fonte declarou. A
classificação jurídica de fundo — se o parecer foi aprovado pelo Presidente da
República e publicado, nos termos do art. 40, § 1º, da LC 73/93 — depende de
conferir o ato de aprovação, e isso o acervo não faz por ninguém.
"""

from __future__ import annotations

# Rótulo curto (ordenável) + a frase que vai para a resposta.
# O número é ordem de alcance, não hierarquia de qualidade.
ESCALA = {
    "administracao_federal": (
        5, "Toda a Administração Pública Federal",
        "A AGU declara alcance sobre toda a Administração Pública Federal. "
        "Confira o ato de aprovação antes de tratar como vinculante: o efeito "
        "do art. 40, § 1º, da LC 73/93 depende de aprovação pelo Presidente da "
        "República e publicação."),
    "agu": (
        4, "Órgãos da AGU",
        "Alcance declarado: os órgãos da Advocacia-Geral da União. Não obriga "
        "por si a Administração consulente."),
    "cgu": (
        3, "Órgãos da Consultoria-Geral da União",
        "Alcance declarado: os órgãos da Consultoria-Geral da União."),
    "processo": (
        2, "Apenas os órgãos envolvidos no processo",
        "Alcance declarado: apenas os órgãos envolvidos naquele processo. "
        "Fora dele é precedente persuasivo, não norma."),
    "indefinido": (
        1, "Alcance não declarado na fonte",
        "A fonte não declara o alcance desta manifestação. Não presuma "
        "vinculação."),
}

# A `natureza` do CONUNI, tal como vem da AGU, mapeada para a escala.
_NATUREZA = {
    "toda a administração pública federal": "administracao_federal",
    "órgãos da agu": "agu",
    "agu e órgãos envolvidos na controvérsia": "agu",
    "órgãos da cgu": "cgu",
    "apenas órgãos envolvidos no processo": "processo",
}

# Espécies que têm regime próprio de vinculação, definido em lei ou em ato
# normativo, e não pela `natureza` de um processo.
ESPECIE_PROPRIA = {
    "Orientação Normativa": (
        "administracao_federal",
        "Orientação Normativa da AGU: uniformiza o entendimento e vincula os "
        "órgãos jurídicos da AGU e a Administração Pública Federal assessorada."),
    "Orientação Normativa CNU": (
        "administracao_federal",
        "Orientação Normativa da extinta Câmara Nacional de Uniformização. A "
        "própria AGU declara que possuem a mesma eficácia das Orientações "
        "Normativas em vigor."),
    "Súmula": (
        "agu",
        "Súmula da AGU: de observância obrigatória pelos órgãos de consultoria "
        "e contencioso da AGU, da PGF e da PGBC (LC 73/93). Não é norma para a "
        "Administração consulente."),
}

# O aviso que acompanha TODA resposta deste acervo. A carteira do escritório é
# de Município, e nada aqui vincula Município.
AVISO_ENTE = (
    "Este acervo é federal. Nenhuma manifestação da AGU vincula Estado, "
    "Distrito Federal ou Município: para o ente subnacional é precedente "
    "persuasivo, por mais vinculante que seja na esfera federal.")


def classificar(especie: str | None, natureza: str | None) -> tuple[str, str, str]:
    """(chave, rótulo de alcance, explicação) do grau de vinculação."""
    if especie in ESPECIE_PROPRIA:
        chave, explicacao = ESPECIE_PROPRIA[especie]
        return chave, ESCALA[chave][1], explicacao
    chave = _NATUREZA.get((natureza or "").strip().lower(), "indefinido")
    _, rotulo, explicacao = ESCALA[chave]
    return chave, rotulo, explicacao


def ordem(chave: str) -> int:
    return ESCALA.get(chave, ESCALA["indefinido"])[0]
