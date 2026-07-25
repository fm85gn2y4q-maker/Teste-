from datetime import date

import pytest

from tcerj.extracao import (
    corrigir_mojibake,
    documento_de_registro,
    documento_de_texto,
    extrair_assuntos,
    extrair_ementa,
    extrair_especie_e_numero,
    extrair_orgao,
    extrair_processo,
    extrair_relator,
    formatar_processo,
    html_para_texto,
    parse_data,
)
from tcerj.modelos import Documento, TipoDocumento

ACORDAO = """
TRIBUNAL DE CONTAS DO ESTADO DO RIO DE JANEIRO

ACÓRDÃO Nº 1.234/2020

Processo nº 210.123-4/2019
Relator: Conselheiro Marianna Montebello Willeman
Sessão de 12/03/2020
Publicação no D.O.E. de 20/03/2020
Assuntos: Licitação; Dispensa indevida; Responsabilidade solidária

EMENTA: Tomada de contas. Contrato de prestação de serviços. Dispensa de
licitação sem amparo legal. Dano ao erário configurado. Aplicação de multa.
Imputação de débito solidário ao gestor e à empresa contratada.

RELATÓRIO
Trata-se de tomada de contas instaurada em razão de irregularidades...

VOTO
Pelas razões expostas, voto pela irregularidade das contas.
"""


def test_extrai_especie_numero_e_ano():
    tipo, numero, ano = extrair_especie_e_numero(ACORDAO)
    assert tipo is TipoDocumento.ACORDAO
    assert numero == "1234"
    assert ano == 2020


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("DELIBERAÇÃO Nº 277/2020", (TipoDocumento.DELIBERACAO, "277", 2020)),
        ("Súmula 15", (TipoDocumento.SUMULA, "15", None)),
        ("Enunciado nº 7/22", (TipoDocumento.ENUNCIADO, "7", 2022)),
        ("PARECER PRÉVIO Nº 3/2021", (TipoDocumento.PARECER_PREVIO, "3", 2021)),
        ("Resolução nº 312 - 2019", (TipoDocumento.RESOLUCAO, "312", 2019)),
    ],
)
def test_especies_diversas(texto, esperado):
    assert extrair_especie_e_numero(texto) == esperado


@pytest.mark.parametrize(
    "texto,numero",
    [
        ("Acórdão nº 1234/2020", "1234"),   # 4 dígitos sem ponto de milhar
        ("Acórdão nº 1.234/2020", "1234"),  # mesmo número, com ponto
        ("Acórdão nº 12345/2020", "12345"),
        ("Acórdão nº 7/2020", "7"),
        ("Acórdão nº 277/2020", "277"),
    ],
)
def test_numero_nao_e_truncado(texto, numero):
    assert extrair_especie_e_numero(texto)[1] == numero


@pytest.mark.parametrize(
    "corrompido,esperado",
    [
        ("ACÃ“RDÃƒO NÂº 1234/2020", "ACÓRDÃO Nº 1234/2020"),
        ("licitaÃ§Ã£o", "licitação"),
        ("SessÃ£o de 12/03/2020", "Sessão de 12/03/2020"),
        ("JoÃ£o da Silva", "João da Silva"),
        # Texto já correto não pode ser alterado.
        ("ACÓRDÃO Nº 1234/2020", "ACÓRDÃO Nº 1234/2020"),
        ("Deliberação nº 277/2020", "Deliberação nº 277/2020"),
        ("Acordao sem acento", "Acordao sem acento"),
        ("", ""),
    ],
)
def test_corrige_mojibake(corrompido, esperado):
    assert corrigir_mojibake(corrompido) == esperado


def test_extracao_funciona_apos_corrigir_mojibake():
    corrompido = (
        "ACÃ“RDÃƒO NÂº 1234/2020\n"
        "Processo nÂº 210.123-4/2019\n"
        "Relator: Conselheiro JoÃ£o da Silva\n"
        "SessÃ£o de 12/03/2020\n"
    )
    doc = documento_de_texto(corrigir_mojibake(corrompido))
    assert doc.numero == "1234"
    assert doc.tipo is TipoDocumento.ACORDAO
    assert doc.relator == "João da Silva"
    assert doc.data_sessao == date(2020, 3, 12)


def test_html_sem_charset_declarado_e_recuperado():
    # O navegador entrega o texto já decodificado errado; o pipeline conserta.
    html = "<html><body><p>DELIBERAÃ‡ÃƒO NÂº 277/2020</p></body></html>"
    assert "DELIBERAÇÃO Nº 277/2020" in html_para_texto(html)


def test_extrai_processo_com_e_sem_rotulo():
    assert extrair_processo(ACORDAO) == "210.123-4/2019"
    assert extrair_processo("TCE-RJ 104.567-9/22") == "104.567-9/22"
    assert extrair_processo("| 100.123-0/2018 | Acórdão |") == "100.123-0/2018"
    assert extrair_processo("sem processo aqui") is None


def test_extrai_relator_removendo_titulo():
    assert extrair_relator(ACORDAO) == "Marianna Montebello Willeman"
    assert extrair_relator("Rel. Cons. José da Silva Neto") == "José da Silva Neto"
    assert extrair_relator("nada por aqui") is None


def test_relator_nao_captura_prosa_em_minusculas():
    """A palavra "relator" no meio de uma frase não anuncia um nome próprio."""
    tese = (
        "A faculdade de retirada de pauta pelo relator antes de iniciada a "
        "sessão não alcança o processo já julgado."
    )
    assert extrair_relator(tese) is None


def test_extrai_orgao_julgador():
    assert extrair_orgao("Decisão do Plenário em sessão ordinária") == "Plenário"
    assert extrair_orgao("Primeira Câmara") == "Primeira Câmara"
    assert extrair_orgao("texto qualquer") is None


def test_extrai_ementa_ate_a_proxima_secao():
    ementa = extrair_ementa(ACORDAO)
    assert ementa.startswith("Tomada de contas.")
    assert "Imputação de débito solidário" in ementa
    # Não pode vazar para o relatório.
    assert "Trata-se de tomada" not in ementa


def test_extrai_assuntos_separados():
    assert extrair_assuntos(ACORDAO) == [
        "Licitação",
        "Dispensa indevida",
        "Responsabilidade solidária",
    ]
    assert extrair_assuntos("sem rotulo") == []


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("12/03/2020", date(2020, 3, 12)),
        ("2020-03-12", date(2020, 3, 12)),
        ("5 de setembro de 2019", date(2019, 9, 5)),
        ("01.02.22", date(2022, 2, 1)),
        ("30/02/2020", None),  # data inválida
        ("", None),
        (None, None),
    ],
)
def test_parse_data(entrada, esperado):
    assert parse_data(entrada) == esperado


def test_documento_de_texto_completo():
    doc = documento_de_texto(ACORDAO, url="https://exemplo/1")
    assert doc.tipo is TipoDocumento.ACORDAO
    assert doc.numero == "1234"
    assert doc.ano == 2020
    assert doc.processo == "210.123-4/2019"
    assert doc.relator == "Marianna Montebello Willeman"
    assert doc.data_sessao == date(2020, 3, 12)
    assert doc.data_publicacao == date(2020, 3, 20)
    assert doc.id == "acordao-1234-2020"
    assert "TCE-RJ, Acórdão 1234/2020" in doc.citacao


def test_data_de_sessao_e_publicacao_nao_se_confundem():
    doc = documento_de_texto(ACORDAO)
    assert doc.data_sessao != doc.data_publicacao


def test_html_para_texto_remove_scripts():
    html = "<html><body><script>var x=1</script><p>Acórdão 1/2020</p></body></html>"
    texto = html_para_texto(html)
    assert "var x" not in texto
    assert "Acórdão 1/2020" in texto


def test_documento_de_registro_json():
    registro = {
        "numeroAcordao": "1234",
        "ano": "2020",
        "tipoDocumento": "Acórdão",
        "numeroProcesso": "210.123-4/2019",
        "nomeRelator": "Fulano de Tal",
        "dataSessao": "12/03/2020",
        "ementa": "Licitação. Dispensa indevida.",
        "urlPdf": "https://exemplo/doc.pdf",
    }
    doc = documento_de_registro(registro)
    assert doc.tipo is TipoDocumento.ACORDAO
    assert doc.numero == "1234"
    assert doc.ano == 2020
    assert doc.relator == "Fulano de Tal"
    assert doc.data_sessao == date(2020, 3, 12)
    assert doc.url_pdf == "https://exemplo/doc.pdf"
    assert doc.bruto == registro


def test_registro_usa_tipo_esperado_quando_ausente():
    doc = documento_de_registro(
        {"numero": "9", "ano": "2021", "ementa": "texto"},
        tipo_esperado=TipoDocumento.ENUNCIADO,
    )
    assert doc.tipo is TipoDocumento.ENUNCIADO


def test_id_estavel_por_hash_quando_sem_numero():
    a = Documento(url="https://exemplo/x")
    b = Documento(url="https://exemplo/x")
    assert a.id == b.id
    assert Documento(url="https://exemplo/y").id != a.id


def test_documento_sem_identificacao_falha():
    with pytest.raises(ValueError):
        Documento().id


def test_mesclar_nao_sobrescreve_valores_existentes():
    base = Documento(tipo=TipoDocumento.ACORDAO, numero="1", relator="Antigo")
    extra = Documento(numero="2", relator="Novo", processo="210.123-4/2019")
    base.mesclar(extra)
    assert base.numero == "1"
    assert base.relator == "Antigo"
    assert base.processo == "210.123-4/2019"


# ---------------------------------------------------------------------------
# Formatos observados na API real do portal (calibração de 2026-07-25)
# ---------------------------------------------------------------------------

# Registro tal como a base de Jurisprudência Selecionada o devolve.
REGISTRO_REAL = {
    "jurisprudenciaId": 1140,
    "numeroProcesso": "23414202025",
    "dispositivo": "O fato de se estabelecer prazo máximo de idade de equipamentos...",
    "dispositivoCompleto": "LICITAÇÃO. LIMITE MÁXIMO. EQUIPAMENTOS.\\nO fato de se "
                           "estabelecer prazo máximo de idade de equipamentos...",
    "relator": "José Gomes Graciosa                          ",
    "dataDoVoto": "2026-05-25T00:00:00-03:00",
    "macroTemaNome": "Licitações e Contratos",
    "numeroAcordao": 17795,
    "anoAcordao": 2026,
}


def test_registro_da_api_real_preenche_os_campos():
    doc = documento_de_registro(REGISTRO_REAL, tipo_esperado=TipoDocumento.ACORDAO)
    assert doc.numero == "17795"
    assert doc.ano == 2026
    assert doc.relator == "José Gomes Graciosa"  # sem o preenchimento à direita
    assert doc.processo == "234.142-0/2025"  # número achatado, reformatado
    assert doc.data_sessao == date(2026, 5, 25)  # carimbo ISO com "T"
    assert doc.assuntos == ["Licitações e Contratos"]
    assert doc.ementa.startswith("LICITAÇÃO.")
    assert "\\n" not in doc.ementa  # a quebra escapada virou quebra de verdade
    assert "\n" in doc.ementa


def test_ementas_distintas_do_mesmo_acordao_nao_colidem():
    """Um acórdão pode render várias teses selecionadas, uma por macro-tema."""
    primeira = documento_de_registro(
        {**REGISTRO_REAL, "jurisprudenciaId": 1123, "macroTemaNome": "Recurso"},
        tipo_esperado=TipoDocumento.ACORDAO,
    )
    segunda = documento_de_registro(
        {**REGISTRO_REAL, "jurisprudenciaId": 1124, "macroTemaNome": "Direito Processual"},
        tipo_esperado=TipoDocumento.ACORDAO,
    )
    assert primeira.numero == segunda.numero  # mesmo acórdão
    assert primeira.id != segunda.id  # registros distintos mesmo assim


def test_numero_zero_e_tratado_como_ausente():
    """A base marca com zero a ementa ainda sem acórdão publicado."""
    doc = documento_de_registro(
        {**REGISTRO_REAL, "numeroAcordao": 0, "anoAcordao": 0},
        tipo_esperado=TipoDocumento.ACORDAO,
    )
    assert doc.numero is None
    assert doc.ano == 2026  # do ano do voto, e não o 2000 vindo do zero
    assert "Acórdão s/n" in doc.citacao  # e não "Acórdão 0/2000"
    assert doc.id  # ainda assim identificável, pelo id de origem


def test_ano_zero_sem_data_nao_vira_ano_2000():
    doc = documento_de_registro(
        {"numeroAcordao": 7, "anoAcordao": 0, "ementa": "texto"},
        tipo_esperado=TipoDocumento.ACORDAO,
    )
    assert doc.ano is None


def test_id_ignora_id_de_fonte_quando_ausente():
    """Documentos vindos de texto continuam com o identificador enxuto."""
    assert documento_de_texto(ACORDAO).id == "acordao-1234-2020"


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("21973182025", "219.731-8/2025"),
        ("219.731-8/2025", "219.731-8/2025"),  # já formatado, passa intacto
        ("12345", "12345"),  # tamanho inesperado, não inventa formato
        (None, None),
    ],
)
def test_formatar_processo(entrada, esperado):
    assert formatar_processo(entrada) == esperado


@pytest.mark.parametrize(
    "rotulo,esperado",
    [
        ("Acórdãos", TipoDocumento.ACORDAO),
        ("ACORDAO", TipoDocumento.ACORDAO),
        ("Parecer Prévio", TipoDocumento.PARECER_PREVIO),
        ("Resposta a Consulta", TipoDocumento.RESPOSTA_CONSULTA),
        ("Deliberações", TipoDocumento.DELIBERACAO),
        ("qualquer coisa", TipoDocumento.INDEFINIDO),
        (None, TipoDocumento.INDEFINIDO),
    ],
)
def test_classificacao_de_tipo(rotulo, esperado):
    assert TipoDocumento.de_texto(rotulo) is esperado
