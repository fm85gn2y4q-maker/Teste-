from __future__ import annotations

import referencias


def _refs(texto: str) -> set[str]:
    return {ref for _, ref in referencias.extrair(texto)}


def test_lei_com_separador_de_milhar_nao_e_truncada():
    """A armadilha que custou 1.224 documentos no acervo da PGE-RJ: alternância
    de regex é preguiçosa à esquerda e casa '866' dentro de '8.666'."""
    achados = _refs("nos termos da Lei nº 8.666, de 1993, aplicável à espécie")
    assert "Lei 8.666/1993" in achados
    assert not any("Lei 866" in a for a in achados)


def test_lei_14133_sem_ano_explicito():
    assert "Lei 14.133" in _refs("o art. 29 da Lei nº 14.133 dispõe")


def test_ano_de_dois_digitos_vira_seculo_certo():
    achados = _refs("Lei nº 8.666/93 e Lei nº 14.133/21")
    assert "Lei 8.666/1993" in achados
    assert "Lei 14.133/2021" in achados


def test_orientacao_normativa_com_e_sem_ano():
    achados = _refs("conforme a Orientação Normativa AGU nº 4/2009 e a ON nº 77/2023")
    assert "Orientação Normativa AGU nº 4/2009" in achados


def test_sumula_distingue_a_corte():
    achados = _refs("a Súmula Vinculante nº 13 do STF e a Súmula da AGU nº 34")
    assert any("Súmula Vinculante" in a for a in achados)
    assert any("34" in a for a in achados)


def test_acordao_do_tcu_guarda_a_corte():
    achados = _refs("Acórdão nº 1.214/2013-TCU-Plenário")
    assert any("1.214/2013" in a and "TCU" in a for a in achados)


def test_parecer_interno_da_agu():
    achados = _refs("nos termos do PARECER n. 00001/2026/CNLCA/CGU/AGU")
    assert any("CNLCA" in a for a in achados)


def test_texto_sem_referencia_nao_inventa():
    assert referencias.extrair("A Administração deve motivar seus atos.") == {}


def test_ocorrencias_sao_contadas():
    contagem = referencias.extrair(
        "Lei nº 8.666/1993 ... Lei nº 8.666/1993 ... Lei nº 8.666/1993")
    assert contagem[("norma", "Lei 8.666/1993")] == 3
