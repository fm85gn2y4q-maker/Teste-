"""A régua do acervo: o grau de vinculação.

Se estes testes passarem e todos os outros falharem, o acervo ainda é honesto.
Se estes falharem, ele mente sobre a única coisa que decide o uso do documento
numa peça.
"""

from __future__ import annotations

import autoridade
import pytest


def test_natureza_do_conuni_vira_alcance():
    for natureza, esperado in (
            ("Toda a Administração Pública Federal", "administracao_federal"),
            ("Órgãos da AGU", "agu"),
            ("Órgãos da CGU", "cgu"),
            ("Apenas órgãos envolvidos no processo", "processo"),
    ):
        chave, _, _ = autoridade.classificar(None, natureza)
        assert chave == esperado, natureza


def test_natureza_desconhecida_nao_vira_vinculante():
    """O caso perigoso: campo vazio ou inesperado NÃO pode virar alcance amplo."""
    for natureza in (None, "", "   ", "qualquer coisa nova que a AGU inventar"):
        chave, _, explicacao = autoridade.classificar(None, natureza)
        assert chave == "indefinido"
        assert "Não presuma" in explicacao


def test_comparacao_de_natureza_ignora_caixa_e_espaco():
    chave, _, _ = autoridade.classificar(None, "  ÓRGÃOS DA AGU  ")
    assert chave == "agu"


def test_especie_tem_regime_proprio_e_ignora_natureza():
    """ON e súmula não dependem da `natureza` de um processo: a vinculação vem
    da espécie. Passar uma natureza restritiva não pode rebaixá-las."""
    chave, _, _ = autoridade.classificar("Orientação Normativa",
                                         "Apenas órgãos envolvidos no processo")
    assert chave == "administracao_federal"
    chave, _, _ = autoridade.classificar("Súmula", "Apenas órgãos envolvidos no processo")
    assert chave == "agu"


def test_on_da_cnu_extinta_mantem_eficacia():
    chave, _, explicacao = autoridade.classificar("Orientação Normativa CNU", None)
    assert chave == "administracao_federal"
    assert "mesma eficácia" in explicacao


def test_alcance_federal_vem_com_a_ressalva_da_lc_73():
    """Nunca afirmar vinculação do art. 40, § 1º sem mandar conferir o ato."""
    _, _, explicacao = autoridade.classificar(None, "Toda a Administração Pública Federal")
    assert "40" in explicacao and "Presidente da República" in explicacao


def test_ordem_cresce_com_o_alcance():
    ordens = [autoridade.ordem(k) for k in
              ("indefinido", "processo", "cgu", "agu", "administracao_federal")]
    assert ordens == sorted(ordens)
    assert len(set(ordens)) == len(ordens)


def test_aviso_de_ente_federado_nomeia_municipio():
    """A carteira do escritório é municipal: o aviso tem de dizer a palavra."""
    assert "Município" in autoridade.AVISO_ENTE
    assert "persuasivo" in autoridade.AVISO_ENTE
