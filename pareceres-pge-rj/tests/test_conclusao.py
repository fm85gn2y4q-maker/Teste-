"""Extração da conclusão do parecer.

Cada teste aqui corresponde a um defeito que apareceu contra documento real.
"""

import pytest

from conclusao import conclusao_de, parece_alheio
from conftest import corpo

FORMULAS = [
    ("Ante todo o exposto, opino pela regularidade.", "exposto"),
    ("Diante do exposto, não há óbices jurídicos.", "exposto"),
    ("Em face do exposto, nada a opor.", "exposto"),
    ("Do exposto, opina-se pela aprovação.", "exposto"),
    ("À vista do exposto, é o parecer.", "exposto"),
    ("Isto posto, conclui-se pela viabilidade.", "exposto"),
    ("Pelo exposto, sugere-se o arquivamento.", "exposto"),
    ("Conclusão: a contratação é viável.", "conclusao"),
    ("Nestes termos, submeto à consideração superior.", "termos"),
]


@pytest.mark.parametrize("texto,tipo", FORMULAS)
def test_reconhece_as_formulas_de_fecho(texto, tipo):
    conc, achado, alheio = conclusao_de(corpo(texto))
    assert achado == tipo
    assert not alheio
    assert conc.startswith(texto[:20])


def test_nao_trunca_no_meio_da_palavra():
    """O padrão antigo casava "do o exposto" dentro de "ante todo o exposto",
    e a conclusão saía começando no meio de "todo"."""
    conc, _, _ = conclusao_de(corpo("Ante todo o exposto, opino pela regularidade."))
    assert conc.startswith("Ante todo o exposto")
    assert not conc.startswith("do o exposto")


def test_texto_curto_nao_produz_conclusao():
    assert conclusao_de("Diante do exposto, opino.") == ("", "", False)


def test_sem_formula_nenhuma():
    conc, tipo, alheio = conclusao_de(corpo("Segue o processo para providências."))
    assert conc == "" and tipo == "" and not alheio


# --------------------------------------------------------------- proveniência
DECISAO_TCE = (
    "Pelo exposto e examinado, em sede de cognição sumária, Decido: I - Pela CONCESSÃO "
    "DE TUTELA PROVISÓRIA, nos termos do Art. 84-A do RITCERJ. GA-2, ANDREA SIQUEIRA "
    "MARTINS CONSELHEIRA SUBSTITUTA. TCE-RJ PROCESSO Nº 102.035-8/2020")
PECA_MP = (
    "Pelo exposto, o MINISTÉRIO PÚBLICO DO ESTADO DO RIO DE JANEIRO, por meio da 1ª "
    "Promotoria de Justiça de Tutela Coletiva de Cidadania da Capital, requer...")


@pytest.mark.parametrize("peca", [DECISAO_TCE, PECA_MP])
def test_reconhece_peca_de_outro_orgao(peca):
    assert parece_alheio(peca)


def test_conclusao_propria_nao_e_confundida_com_peca_alheia():
    assert not parece_alheio("Diante do exposto, opino pela viabilidade da contratação.")


def test_uma_mencao_isolada_nao_condena():
    """Parecer que apenas cita o Tribunal de Contas continua sendo da PGE."""
    assert not parece_alheio(
        "Diante do exposto, e observada a jurisprudência do Tribunal de Contas, opino "
        "pela viabilidade jurídica da contratação pretendida.")


@pytest.mark.parametrize("peca", [DECISAO_TCE, PECA_MP])
def test_prefere_a_conclusao_da_pge_a_peca_reproduzida_depois(peca):
    """No Parecer FMF 75/2020 a peça de terceiro vinha DEPOIS da conclusão, e
    como se ficava com a última fórmula, era ela que entrava no campo."""
    propria = ("Diante do exposto, opino pela invalidade do chamamento público "
               "realizado por meio do Edital SUBEXEC 001/2020. Rio de Janeiro, 2020. "
               "FELIPE DE MELO FONTE, Procurador do Estado.")
    conc, _, alheio = conclusao_de(corpo(propria, peca))
    assert not alheio
    assert conc.startswith("Diante do exposto, opino pela invalidade")


@pytest.mark.parametrize("peca", [DECISAO_TCE, PECA_MP])
def test_corta_a_cauda_de_terceiro(peca):
    propria = ("Diante do exposto, opino pela invalidade do chamamento público "
               "realizado por meio do Edital SUBEXEC 001/2020, e pela presença de "
               "vício insanável na celebração do contrato de gestão.")
    conc, _, _ = conclusao_de(corpo(propria, peca))
    assert "CONSELHEIRA" not in conc.upper()
    assert "PROMOTORIA" not in conc.upper()


def test_marca_quando_so_existe_peca_de_terceiro():
    conc, _, alheio = conclusao_de(corpo(DECISAO_TCE))
    assert alheio
    assert conc  # devolve mesmo assim, para o consumidor decidir


def test_conclusao_vence_despacho_de_chancela():
    """Fórmula de conclusão propriamente dita tem prioridade sobre o mero
    "de acordo com o parecer", que não conclui nada."""
    doc = corpo("Diante do exposto, opino pela viabilidade.",
                "De acordo com o bem lançado parecer do i. Procurador.")
    _, tipo, _ = conclusao_de(doc)
    assert tipo == "exposto"
