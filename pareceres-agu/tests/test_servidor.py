from __future__ import annotations

import asyncio

import pytest

from agu.servidor import INSTRUCOES, construir


@pytest.fixture(scope="module")
def servidor(acervo):
    return construir(str(acervo.caminho))


def _chamar(servidor, nome, args=None):
    args = args or {}
    r = asyncio.run(servidor.call_tool(nome, args))
    return r[1] if isinstance(r, tuple) else r


def test_as_dez_ferramentas_estao_no_ar(servidor):
    nomes = {t.name for t in asyncio.run(servidor.list_tools())}
    assert nomes == {
        "pesquisar_manifestacoes", "o_que_vincula", "pesquisar_inteiro_teor",
        "ler_paginas", "expandir_consulta", "obter_documento", "quem_citou",
        "situacao_do_ato", "listar_documentos", "cobertura_do_acervo"}


def test_instrucoes_fixam_a_regra_da_vinculacao():
    assert "GRAU DE VINCULAÇÃO" in INSTRUCOES
    assert "Município" in INSTRUCOES
    assert "Sapiens" in INSTRUCOES


def test_o_que_vincula_acha_a_on_do_servico_continuo(servidor):
    """A consulta do advogado é longa; o enunciado da ON tem uma linha. Sem o
    segundo passe com OU, a ferramenta falha no caso que ela existe para
    responder."""
    d = _chamar(servidor, "o_que_vincula",
                {"consulta": "prorrogação de contrato de serviço contínuo"})
    citacoes = [o["citacao"] for o in d["orientacoes_normativas"]]
    assert any("nº 1/2009" in c for c in citacoes), citacoes


def test_busca_ampliada_nao_finge_pertinencia(servidor):
    """Quando cai no OU, o total mede alcance, não pertinência. Anunciar '86
    súmulas sobre o tema' seria falso: são as 86 que existem."""
    d = _chamar(servidor, "o_que_vincula",
                {"consulta": "prorrogação de contrato de serviço contínuo"})
    assert d["criterio"].startswith("qualquer termo")
    assert "totais" not in d
    assert "alcancados_pela_busca_ampliada" in d
    assert "não a quantidade de atos pertinentes" in d["leitura_dos_totais"]


def test_toda_resposta_de_busca_traz_o_aviso_de_ente(servidor):
    for nome, args in (("pesquisar_manifestacoes", {"consulta": "licitação"}),
                       ("o_que_vincula", {"consulta": "licitação"}),
                       ("listar_documentos", {"fonte": "on", "limite": 3})):
        assert "Município" in _chamar(servidor, nome, args)["aviso_ente"], nome


def test_on_revogada_chega_com_ressalva_pela_ferramenta(servidor):
    d = _chamar(servidor, "situacao_do_ato", {"ato": "Orientação Normativa AGU nº 32"})
    achado = d["atos_encontrados"][0]
    assert "ressalvas_de_vigencia" in achado
    assert "NÃO é declaração de vigência" in d["advertencia"]


def test_links_do_ato_nao_viram_despacho(servidor):
    """ON e súmula não têm cadeia de despachos; rotular assim anunciaria
    despacho onde não há."""
    d = _chamar(servidor, "situacao_do_ato", {"ato": "Orientação Normativa AGU nº 32"})
    achado = d["atos_encontrados"][0]
    assert "links_do_ato" in achado
    assert "despachos" not in achado


def test_manifestacao_do_conuni_mantem_despachos(servidor):
    d = _chamar(servidor, "pesquisar_manifestacoes",
                {"consulta": "engenharia consultiva", "limite": 5})
    assert d["resultados"]
    assert any("despachos" in r for r in d["resultados"])


def test_cobertura_nao_esconde_o_que_falta(servidor):
    cob = _chamar(servidor, "cobertura_do_acervo")
    assert int(cob["sem_arquivo_publico"]) > 1000
    assert "Município" in cob["aviso_ente_federado"]


def test_documento_inexistente_devolve_erro_e_nao_estoura(servidor):
    assert "erro" in _chamar(servidor, "obter_documento", {"id": 999999})
    assert "erro" in _chamar(servidor, "ler_paginas",
                             {"id": 999999, "pagina_inicial": 1})
