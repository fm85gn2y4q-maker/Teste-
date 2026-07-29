"""Testes da extração de composição.

Os textos abaixo reproduzem as fórmulas de acórdão usadas no TJRJ. Depois da
calibração (ver docs/CALIBRACAO.md), acrescente aqui os casos reais que a
regex errar — este arquivo é o registro de cobertura do parser.
"""

from tjrj.parse.composicao import extrair, precisa_revisao
from tjrj.parse.normalize import chave_julgador, chave_orgao, cnj_valido, numero_cnj

ACORDAO_UNANIME = """
PODER JUDICIÁRIO DO ESTADO DO RIO DE JANEIRO
DÉCIMA CÂMARA CÍVEL
Apelação Cível nº 0012345-67.2019.8.19.0001
Relator: Des. João Carlos de Almeida

EMENTA. APELAÇÃO CÍVEL. RESPONSABILIDADE CIVIL...

ACÓRDÃO
Vistos, relatados e discutidos estes autos, ACORDAM os Desembargadores que
integram a Décima Câmara Cível do Tribunal de Justiça do Estado do Rio de
Janeiro, por unanimidade de votos, em DAR PROVIMENTO ao recurso, nos termos
do voto do Relator.

Rio de Janeiro, 12 de março de 2024.

Votaram os Desembargadores: Maria Helena Rocha e Pedro Álvares Cabral Neto.
Presidiu o julgamento o Desembargador Antônio Vieira Lima.

DES. JOÃO CARLOS DE ALMEIDA
Relator
"""

ACORDAO_MAIORIA = """
Apelação nº 0098765-43.2020.8.19.0209
Relator: Desembargadora Ana Lúcia Ferreira
Revisor: Des. Carlos Eduardo Mota

ACORDAM os Desembargadores que compõem a Quinta Câmara Criminal, por maioria
de votos, em NEGAR PROVIMENTO ao apelo, vencido o Desembargador Carlos
Eduardo Mota, que dava provimento parcial.

Relator designado para o acórdão o Desembargador Rui Barbosa de Souza.
Participaram do julgamento os Desembargadores Ana Lúcia Ferreira, Carlos
Eduardo Mota e Rui Barbosa de Souza.
"""


def test_relator_e_identificado():
    comp = extrair(ACORDAO_UNANIME)
    relator = [p for p in comp if p.papel == "relator"]
    assert len(relator) == 1
    assert relator[0].nome_norm == chave_julgador("JOÃO CARLOS DE ALMEIDA")
    assert relator[0].nome == "João Carlos de Almeida"


def test_demais_julgadores_e_presidente():
    comp = extrair(ACORDAO_UNANIME)
    papeis = {p.nome_norm: p.papel for p in comp}
    assert papeis[chave_julgador("Maria Helena Rocha")] == "vogal"
    assert papeis[chave_julgador("Pedro Álvares Cabral Neto")] == "vogal"
    assert papeis[chave_julgador("Antônio Vieira Lima")] == "presidente"
    assert not any(p.vencido for p in comp)


def test_vencido_e_marcado():
    comp = extrair(ACORDAO_MAIORIA)
    por_nome = {p.nome_norm: p for p in comp}
    assert por_nome[chave_julgador("Carlos Eduardo Mota")].vencido is True
    assert por_nome[chave_julgador("Ana Lúcia Ferreira")].vencido is False


def test_relator_designado_vence_o_relator_sorteado():
    comp = extrair(ACORDAO_MAIORIA)
    designado = [p for p in comp if p.papel == "relator_designado"]
    assert len(designado) == 1
    assert designado[0].nome_norm == chave_julgador("Rui Barbosa de Souza")


def test_um_julgador_um_papel():
    comp = extrair(ACORDAO_MAIORIA)
    nomes = [p.nome_norm for p in comp]
    assert len(nomes) == len(set(nomes))


def test_texto_pobre_pede_revisao():
    assert precisa_revisao(extrair("Acórdão sem qualquer identificação de julgadores."))
    assert not precisa_revisao(extrair(ACORDAO_UNANIME))


# --- normalização -----------------------------------------------------------


def test_orgao_colapsa_grafias():
    alvo = chave_orgao("DÉCIMA CÂMARA CÍVEL")
    assert chave_orgao("10ª Câmara Cível") == alvo
    assert chave_orgao("10a. Camara Civel") == alvo


def test_julgador_colapsa_titulos_e_caixa():
    alvo = chave_julgador("João Carlos de Almeida")
    for variante in ("DES. JOÃO CARLOS DE ALMEIDA", "Desembargador Joao Carlos de Almeida",
                     "JOAO CARLOS DE ALMEIDA - Relator"):
        assert chave_julgador(variante) == alvo


def test_numero_cnj():
    assert numero_cnj("0012345-67.2019.8.19.0001") == "0012345-67.2019.8.19.0001"
    assert numero_cnj("proc. 00123456720198190001 - apelação") == "0012345-67.2019.8.19.0001"
    assert numero_cnj("sem número") is None


def test_digito_verificador_cnj():
    assert cnj_valido("0000001-02.2020.8.19.0001") in (True, False)  # apenas contrato
    assert cnj_valido("123") is False
