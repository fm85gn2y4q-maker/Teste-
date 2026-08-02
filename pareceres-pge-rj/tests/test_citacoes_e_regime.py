"""Extração de citações e classificação do regime de vigência."""

import pytest

from corrigir import extrai
from regime import regime_e_alerta
from rodape import limpa_rodape


def normas(texto):
    return sorted(r for e, r, q, n in extrai(texto) if e == "norma")


# ------------------------------------------------------------------- normas
def test_numero_nao_e_truncado():
    """A alternância `(\\d{1,3}(?:\\.\\d{3})*|\\d{1,6})` casava "866" dentro de
    "8666" e nunca tentava a segunda alternativa: 1.224 documentos ficaram com
    "Lei 866/1993"."""
    assert "Lei 8.666/1993" in normas("aplica-se a Lei nº 8666/93")
    assert not any(r.startswith("Lei 866/") for r in normas("Lei nº 8666/93"))


@pytest.mark.parametrize("escrita", [
    "Lei nº 8.666/93", "Lei 8666/1993", "LEI Nº 8.666, de 21 de junho de 1993",
    "Lei nº 8 666/93", "Lei nnQ 8.666/93",
])
def test_variantes_de_grafia_colapsam_na_mesma_norma(escrita):
    assert normas(escrita) == ["Lei 8.666/1993"]


def test_ruido_de_ocr_no_numero_da_lei():
    """"n2" e "ng" são OCR de "nº"; o dígito só é absorvido se vier colado ao
    "n" e seguido de espaço, senão comeria o primeiro algarismo da norma."""
    assert "Decreto 362/1975" in normas(
        "Decreto Estadual n2 362 de 19 de setembro de 1975")
    assert "Lei 10.520/2002" in normas("Lei nº 10.520/2002")


def test_esfera_nao_separa_a_mesma_norma():
    assert normas("Lei Estadual nº 5.498/2009") == normas("Lei nº 5.498/2009")


def test_numero_curto_sem_ano_e_descartado():
    """"Lei 8" sem ano é ruído de OCR, não norma citável."""
    assert normas("a lei 8 do processo") == []


def test_numero_curto_com_ano_e_mantido():
    assert "Lei Complementar 8/1977" in normas(
        "Lei Complementar nº 8, de 25 de outubro de 1977")


def test_lc_abreviado():
    assert "Lei Complementar 101/2000" in normas("a LC nº 101/2000")


# ------------------------------------------- súmulas, acórdãos e precedentes
def test_sumula_com_e_sem_corte_e_a_mesma():
    achados = {(r, q) for e, r, q, n in extrai("Súmula 247 do TCU e Súmula nº 247")
               if e == "sumula"}
    assert {r for r, _ in achados} == {"Sumula 247"}
    assert {"TCU", ""} == {q for _, q in achados}


def test_acordao_com_e_sem_ponto_e_o_mesmo():
    refs = {r for e, r, q, n in extrai("Acórdão nº 1.565/2015 - Plenário e Acórdão 1565/2015 TCU")
            if e == "acordao"}
    assert refs == {"Acordao 1565/2015"}


def test_numero_nao_vaza_para_a_sigla_do_precedente():
    """"Parecer NO 25/2009" tinha "NO" capturado como sigla, criando entrada
    separada de "Parecer 25/2009"."""
    achados = {(r, q) for e, r, q, n in extrai("Parecer NO 25/2009 e Parecer nº 25/2009")
               if e == "precedente"}
    assert {r for r, _ in achados} == {"Parecer 25/2009"}
    assert all(q == "" for _, q in achados)


def test_sigla_verdadeira_e_preservada():
    achados = [(r, q) for e, r, q, n in extrai("Parecer FBMP nº 15/2020") if e == "precedente"]
    assert achados == [("Parecer 15/2020", "FBMP")]


# ------------------------------------------------------------------ regime
def test_terceiro_setor_vem_antes_da_licitacao():
    """Parecer de organização social era rotulado "Lei 8.666/1993 — revogada",
    quando a matéria se rege pela Lei 9.637/98."""
    reg, alerta = regime_e_alerta(2013, {"Lei 9.637/1998", "Lei 8.666/1993"}, "Terceiro setor")
    assert reg.startswith("Lei 9.637/1998")
    assert "lateral" in alerta


def test_terceiro_setor_sem_lei_federal_citada():
    reg, alerta = regime_e_alerta(2022, {"Lei 8.666/1993"}, "Terceiro setor")
    assert "Terceiro setor" in reg
    assert "não alcancam municipio" in alerta.replace("ã", "a").replace("ç", "c") \
        or "municipio" in alerta


@pytest.mark.parametrize("refs,esperado", [
    ({"Lei 13.019/2014"}, "Lei 13.019/2014 (MROSC)"),
    ({"Lei 9.790/1999"}, "Lei 9.790/1999 (OSCIP)"),
    ({"Lei 14.133/2021"}, "Lei 14.133/2021"),
    ({"Lei 8.666/1993"}, "Lei 8.666/1993"),
    ({"Lei 8.666/1993", "Lei 14.133/2021"}, "transicao 8.666/14.133"),
    ({"Lei 13.303/2016"}, "Lei 13.303/2016 (estatais)"),
])
def test_regimes(refs, esperado):
    assert regime_e_alerta(2020, refs, "")[0] == esperado


def test_concessao_tem_regime_proprio():
    reg, _ = regime_e_alerta(2010, {"Lei 8.987/1995"}, "Concessao, PPP e uso de bem")
    assert "8.987" in reg


def test_alerta_de_norma_revogada_na_8666():
    _, alerta = regime_e_alerta(2015, {"Lei 8.666/1993"}, "Licitacao")
    assert "revogada" in alerta and "14.133" in alerta


# ------------------------------------------------------------------ rodapé
def test_corta_o_rodape_do_sei():
    conc = ("Ante o exposto, opino pela possibilidade de adesão à Ata de Registro de "
            "Preços. Rio de Janeiro, 16 de outubro de 2024. FERNANDO BARBALHO MARTINS "
            "17/10/2024, 09:40 SEI/ERJ - 85545180 - Despacho de Encaminhamento")
    limpo = limpa_rodape(conc)
    assert limpo.endswith("FERNANDO BARBALHO MARTINS")
    assert "SEI/ERJ" not in limpo


def test_nao_corta_o_que_e_curto_demais():
    curto = "SEI/ERJ - 123 - Despacho"
    assert limpa_rodape(curto) == curto


def test_corte_e_idempotente():
    t = ("Diante do exposto, nada a opor à contratação pretendida pelo órgão consulente. "
         "Documento assinado eletronicamente por Fulano de Tal")
    assert limpa_rodape(limpa_rodape(t)) == limpa_rodape(t)
