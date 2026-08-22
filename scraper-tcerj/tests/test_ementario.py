import json
from datetime import date

import pytest

from ementario.acervo import Acervo, montar_consulta_fts
from tcerj.armazenamento import Armazenamento
from tcerj.modelos import Documento, TipoDocumento


@pytest.fixture
def acervo(tmp_path):
    """Acervo mínimo, montado pelo mesmo armazenamento usado na coleta."""
    banco = tmp_path / "acervo.sqlite"
    with Armazenamento(banco) as arm:
        arm.gravar(Documento(
            tipo=TipoDocumento.ACORDAO, numero="17798", ano=2026, id_fonte="1136",
            processo="207.656-8/2026", relator="José Gomes Graciosa",
            data_sessao=date(2026, 5, 25),
            ementa="LICITAÇÃO. CAPITAL SOCIAL INTEGRALIZADO.\nA exigência de capital "
                   "social integralizado como qualificação econômico-financeira não "
                   "encontra amparo no ordenamento.",
            inteiro_teor="capital social integralizado qualificação",
            assuntos=["Licitações e Contratos"],
        ))
        arm.gravar(Documento(
            tipo=TipoDocumento.SUMULA, numero="1", ano=2018, id_fonte="1",
            data_sessao=date(2018, 6, 19),
            ementa="A previsão de obrigatoriedade de visita técnica enquanto requisito "
                   "de habilitação em licitação representa cláusula restritiva à "
                   "competitividade.",
            inteiro_teor="visita técnica habilitação licitação competitividade",
        ))
    a = Acervo(banco)
    yield a
    a.fechar()


# -- tradução da consulta ---------------------------------------------------


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("dispensa licitação", '"dispensa" AND "licitação"'),
        # Palavras vazias e interrogativas não podem estreitar a busca.
        ("posso exigir visita em licitação?", '"exigir" AND "visita" AND "licitação"'),
        # O que o usuário aspeou vira expressão exata.
        ('notória "especialização técnica"', '"especialização técnica" AND "notória"'),
        # Só palavras vazias: melhor buscá-las do que devolver consulta em branco.
        ("de a o", '"de" AND "a" AND "o"'),
    ],
)
def test_montar_consulta_fts(entrada, esperado):
    assert montar_consulta_fts(entrada) == esperado


def test_pontuacao_nao_quebra_a_sintaxe_do_fts(acervo):
    """Sem aspas em cada termo, o MATCH rejeitaria a expressão inteira."""
    achados, _, _ = acervo.pesquisar('prescrição - "marco (art. 74)" OR NOT x')
    assert isinstance(achados, list)  # o que importa é não levantar erro


# -- busca ------------------------------------------------------------------


def test_encontra_por_termo_sem_acento(acervo):
    achados, parcial, _ = acervo.pesquisar("visita tecnica")
    assert [r.tipo for r in achados] == ["sumula"]
    assert parcial is False


def test_abranda_para_ou_quando_o_e_nao_acha_nada(acervo):
    """Uma palavra a mais na pergunta não pode zerar o resultado."""
    achados, parcial, _ = acervo.pesquisar("visita técnica em contrato de obra pública")
    assert achados
    assert parcial is True


def test_busca_sem_correspondencia_devolve_vazio(acervo):
    achados, parcial, _ = acervo.pesquisar("terraplanagem marciana")
    assert achados == []
    assert parcial is False


def test_filtros_de_especie_ano_e_relator(acervo):
    assert len(acervo.pesquisar("licitação", especie="sumula")[0]) == 1
    assert acervo.pesquisar("licitação", ano_min=2020)[0][0].tipo == "acordao"
    assert acervo.pesquisar("licitação", relator="Graciosa")[0][0].relator == (
        "José Gomes Graciosa"
    )
    assert acervo.pesquisar("licitação", relator="Inexistente")[0] == []


def test_obter_por_id_e_id_inexistente(acervo):
    alvo = acervo.pesquisar("capital social")[0][0]
    assert acervo.obter(alvo.id).id == alvo.id
    assert acervo.obter("nao-existe") is None


# -- apresentação -----------------------------------------------------------


def test_citacao_no_formato_de_peca(acervo):
    achado = acervo.pesquisar("capital social")[0][0]
    assert achado.citacao == (
        "TCE-RJ, Acórdão 17798/2026, Processo 207.656-8/2026, "
        "Rel. José Gomes Graciosa, j. 25/05/2026"
    )


def test_sumula_sem_relator_nem_processo_nao_polui_a_citacao(acervo):
    achado = acervo.pesquisar("visita tecnica")[0][0]
    assert achado.citacao == "TCE-RJ, Súmula 1/2018, j. 19/06/2018"


def test_acordao_traz_o_pdf_do_inteiro_teor(acervo):
    """O advogado precisa conferir o acórdão antes de citar a tese."""
    achado = acervo.pesquisar("capital social")[0][0]
    assert achado.url_documento == (
        "https://www.tcerj.tc.br/documento-webapi-externo/api/documento/"
        "acordao/17798/2026?votoInteiro=true"
    )
    # A consulta processual não usa ponto de milhar.
    assert achado.url_processo == (
        "https://www.tcerj.tc.br/consulta-processo/Processo/List"
        "?numeroProcesso=207656-8/2026"
    )
    assert achado.para_dict()["url_inteiro_teor"] == achado.url_documento


def test_sumula_nao_inventa_pdf_de_acordao(acervo):
    """Súmula não tem acórdão nem processo: só a tela pública."""
    achado = acervo.pesquisar("visita tecnica")[0][0]
    assert achado.url_documento is None
    assert achado.url_processo is None
    assert achado.url.endswith("/sumulas")


def test_url_cai_para_o_melhor_endereco_disponivel(acervo):
    acordao = acervo.pesquisar("capital social")[0][0]
    assert acordao.url == acordao.url_documento  # PDF tem precedência


def test_separa_descritores_da_tese(acervo):
    """Do que tratou o julgado e o que ele decidiu são coisas distintas."""
    d = acervo.pesquisar("capital social")[0][0].para_dict()
    assert d["descritores"] == ["LICITAÇÃO", "CAPITAL SOCIAL INTEGRALIZADO"]
    assert d["tese"].startswith("A exigência de capital social")
    assert "LICITAÇÃO." not in d["tese"]  # a indexação não é o entendimento


def test_ementa_toda_em_caixa_alta_nao_e_dividida(acervo):
    """Nas respostas a consulta não há tese em prosa: dividir inventaria uma."""
    from ementario.acervo import separar_ementa

    bruta = "CONSULTA. DÚVIDA A RESPEITO DO PRAZO.\nCONHECIMENTO. ARQUIVAMENTO."
    descritores, tese = separar_ementa(bruta)
    assert descritores == []
    assert tese == bruta


def test_sumula_sem_linha_de_descritores(acervo):
    d = acervo.pesquisar("visita tecnica")[0][0].para_dict()
    assert d["descritores"] == []
    assert d["tese"].startswith("A previsão de obrigatoriedade")


def test_instrucoes_exigem_explicacao_e_link():
    from ementario.servidor import INSTRUCOES

    for exigencia in ("Do que tratou", "como se aplica", "Link de conferência",
                      "url_inteiro_teor", "contrário"):
        assert exigencia in INSTRUCOES


def test_instrucoes_mandam_reformular_sem_presumir_a_resposta():
    """Uma única tradução da pergunta falha por motivo lexical, não semântico."""
    from ementario.servidor import INSTRUCOES

    for exigencia in ("Preserve a consulta inicial", "Reformule quando",
                      "expressao_executada", "controle cruzado",
                      "procurar confirmação"):
        assert exigencia in INSTRUCOES, exigencia


def test_limite_de_leitura_nao_e_conclusao_juridica():
    from ementario.servidor import INSTRUCOES

    assert "operacional, não interpretativo" in INSTRUCOES
    assert "não é conclusão jurídica" in INSTRUCOES


def test_pesquisa_devolve_a_expressao_executada(acervo):
    """Sem registrar a formulação, não há como auditar a pesquisa depois."""
    _, _, expressao = acervo.pesquisar("visita tecnica")
    assert expressao == '"visita" AND "tecnica"'


def test_instrucoes_exigem_verificar_a_proveniencia():
    """Trecho de defesa apresentado como decisão inverte o precedente."""
    from ementario.servidor import INSTRUCOES

    for exigencia in ("É o Relatório", "razões de defesa", "ACORDAM",
                      "Ministério Público de Contas", "expanda a leitura",
                      "estágio processual"):
        assert exigencia in INSTRUCOES, exigencia
    assert "sem antes ler" in INSTRUCOES


def test_cobertura_declara_volumes_e_limites(acervo):
    c = acervo.cobertura()
    assert c["total_de_documentos"] == 2
    assert c["ementas"]["total"] == 2
    assert {e["chave"] for e in c["ementas"]["por_especie"]} == {"acordao", "sumula"}
    assert c["macro_temas"] == ["Licitações e Contratos"]


def test_cobertura_separa_ementas_de_inteiro_teor(acervo):
    """Registros existentes e inteiro teor guardado são contagens distintas."""
    c = acervo.cobertura()
    assert "documentos_com_inteiro_teor" in c["inteiro_teor"]
    assert c["inteiro_teor"]["documentos_com_inteiro_teor"] == 0  # fixture sem PDFs
    assert c["inteiro_teor"]["paginas"] == 0


def test_cobertura_nao_nega_a_existencia_do_inteiro_teor(acervo):
    """O limite antigo dizia que só havia ementa — e virou mentira."""
    limites = " ".join(acervo.cobertura()["limites_do_acervo"])
    assert "Não há inteiro teor" not in limites
    assert "pesquisar_inteiro_teor" in limites
    # E precisa avisar que o documento mistura proveniências.
    assert "alegações de defesa" in limites
    # O acervo não é o Tribunal inteiro, e ausência aqui não prova nada: as
    # duas advertências têm de sobreviver a qualquer reescrita do texto.
    assert "é o conjunto dos acórdãos do TCE-RJ" in limites
    assert "Não afirme que uma tese inexiste" in limites
    # E, desde a expansão pela Pesquisa Textual, a proibição de declarar
    # pacífico o que apenas não se leu.
    assert "Nunca declare pacífico" in limites


# -- as duas origens, o dissenso e a súmula ---------------------------------
#
# Quatro exigências, e uma delas é negativa: o acervo tem de saber apontar
# divergência, atualidade, curadoria e súmula — e tem de se recusar a certificar
# que não há divergência, porque isso ele não pode saber.


class _Pagina:
    def __init__(self, numero, texto, folha=None):
        self.numero, self.texto, self.folha = numero, texto, folha


@pytest.fixture
def acervo_misto(tmp_path):
    """Um acórdão selecionado e outro só descoberto, ambos com inteiro teor."""
    banco = tmp_path / "misto.sqlite"
    with Armazenamento(banco) as arm:
        arm.gravar(Documento(
            tipo=TipoDocumento.ACORDAO, numero="100", ano=2025, id_fonte="a",
            processo="111.111-1/2025", relator="Fulano", data_sessao=date(2025, 3, 1),
            ementa="CONTRATO. SOBREPREÇO.\nO sobrepreço apurado enseja glosa.",
        ))
        arm.gravar(Documento(
            tipo=TipoDocumento.SUMULA, numero="9", ano=2022, id_fonte="s9",
            data_sessao=date(2022, 2, 2),
            ementa="É vedada a exigência de capital social mínimo cumulada com "
                   "garantia de proposta.",
        ))
        for ident, numero, ano, texto in [
            ("acordao-100-2025", "100", 2025,
             "o sobrepreço restou demonstrado na planilha, com voto vencido do "
             "Conselheiro relator"),
            ("acordao-777-2024", "777", 2024,
             "sobrepreço não caracterizado no orçamento examinado"),
        ]:
            arm.registrar_oficial(
                ident, tipo="acordao", numero=numero, ano=ano,
                processo=f"{numero}/{ano}", url=None, paginas_total=1,
            )
            arm.gravar_paginas(ident, [_Pagina(1, texto)])
    a = Acervo(banco)
    yield a
    a.fechar()


def test_resultado_declara_se_passou_pela_curadoria(acervo_misto):
    """Ementa oficial e acórdão de caso concreto não pesam igual."""
    trechos, _, _ = acervo_misto.pesquisar_paginas("sobrepreço", limite=10)
    origem = {t.documento.ano: t.documento.na_curadoria for t in trechos}
    assert origem[2025] is True   # tem ementa selecionada
    assert origem[2024] is False  # só existe na Pesquisa Textual
    fora = next(t for t in trechos if not t.documento.na_curadoria)
    assert "NÃO integra a Jurisprudência Selecionada" in fora.para_dict()["peso_da_fonte"]


def test_curadoria_nao_se_confunde_com_ter_sido_coletado(acervo_misto):
    """`status_coleta='ok'` só diz que o PDF baixou, não que o TCE selecionou.

    Confundir os dois promoveria a jurisprudência selecionada cada acórdão que
    a coleta alcançasse — exatamente ao contrário do que o campo serve.
    """
    origens = acervo_misto.cobertura()["origem_dos_acordaos"]
    assert origens["jurisprudencia_selecionada"] == 1
    assert origens["fora_da_curadoria"] == 1


def test_panorama_dimensiona_o_tema_sem_devolver_julgado(acervo_misto):
    p = acervo_misto.panorama("sobrepreço")
    assert p["acordaos_no_acervo"] == 2
    assert p["na_jurisprudencia_selecionada"] == 1
    assert p["fora_da_curadoria"] == 1
    assert [f["ano"] for f in p["por_ano"]] == [2025, 2024]  # mais atual primeiro
    assert p["periodo"] == "2024–2025"
    assert "resultados" not in p and "trecho" not in p


def test_panorama_aponta_dissenso_quando_ha_rastro(acervo_misto):
    sinais = {s["sinal"] for s in acervo_misto.panorama("sobrepreço")["sinais_de_dissenso"]}
    assert "houve voto vencido" in sinais


def test_panorama_nega_valor_ao_universo_quando_a_busca_abrandou(acervo_misto):
    """Caindo para OU, o número mede a palavra mais comum, e não o tema.

    Medido no acervo real: "zzqqxx inexistente" devolvia 103 acórdãos, todos
    por conta de "inexistente". Sem este aviso o número seria citado como
    tamanho do tema.
    """
    p = acervo_misto.panorama("sobrepreço inexistente")
    assert p["correspondencia_parcial"] is True
    assert "NÃO dimensiona o tema" in p["aviso"]
    assert acervo_misto.panorama("sobrepreço")["aviso"] is None


def test_panorama_avisa_que_ausencia_de_dissenso_nao_prova_pacificacao(acervo_misto):
    """A regra que não pode ser quebrada tem de viajar junto com o número."""
    assert "NÃO significa entendimento pacífico" in acervo_misto.panorama(
        "sobrepreço")["como_ler"]


def test_sumula_sem_casamento_devolve_todas(acervo_misto):
    """Ausência de súmula se afirma por leitura, nunca por silêncio do índice."""
    achadas, todas = acervo_misto.sumulas_sobre("desapropriação de imóvel rural")
    assert todas is True
    # O conjunto inteiro do acervo, e só súmulas — nada de acórdão no meio.
    assert [s.tipo for s in achadas] == ["sumula"]
    assert "Súmula 9/2022" in achadas[0].citacao


def test_sumula_pertinente_vem_sozinha(acervo_misto):
    achadas, todas = acervo_misto.sumulas_sobre("capital social mínimo garantia")
    assert todas is False
    assert [s.tipo for s in achadas] == ["sumula"]


def test_universo_usa_o_indice_de_onde_saiu_o_resultado(acervo_misto):
    """Trocar o denominador inverteria o sinal de "é amostra"."""
    assert acervo_misto.universo('"sobrepreço"') == 2               # acórdãos
    assert acervo_misto.universo('"sobrepreço"', em_ementas=True) == 1  # ementas


# -- vigência da resposta a consulta ----------------------------------------
#
# A espécie tem peso próprio — é o que o Tribunal responde a quem pergunta em
# tese — e PODE ser revogada. O campo esteve anos no payload sem ser lido.


def test_resposta_a_consulta_revogada_sai_com_aviso():
    from tcerj.consultas import dados_de_revogacao

    bruto = json.dumps({
        "revogada": True, "revogadaParcialmente": False,
        "numeroRevogacao": 300, "dataRevogacao": "2026-05-18T00:00:00",
        "justificativaRevogacao": "revogação da tese 2.6 do Prejulgado.",
    })
    d = dados_de_revogacao(bruto)
    assert d["estado"] == "revogada"
    assert d["por"] == 300
    assert d["em"] == "2026-05-18"
    assert "tese 2.6" in d["justificativa"]


def test_revogacao_parcial_nao_e_revogacao_total():
    """Confundir as duas apaga a parte que continua valendo."""
    from tcerj.consultas import dados_de_revogacao

    d = dados_de_revogacao(json.dumps(
        {"revogada": False, "revogadaParcialmente": True}))
    assert d["estado"] == "revogada_parcialmente"


def test_consulta_vigente_nao_inventa_revogacao():
    from tcerj.consultas import dados_de_revogacao

    assert dados_de_revogacao(json.dumps({"revogada": False})) == {}
    assert dados_de_revogacao(None) == {}
    assert dados_de_revogacao("não é json") == {}


def test_data_zero_da_api_nao_vira_data(acervo):
    """A API usa 0001-01-01 para 'não revogado'. Isso não é uma data."""
    from tcerj.consultas import dados_de_revogacao

    d = dados_de_revogacao(json.dumps(
        {"revogada": True, "dataRevogacao": "0001-01-01T00:00:00"}))
    assert d["em"] is None


def test_cobertura_declara_a_data_por_especie(acervo):
    """As espécies não caminham juntas.

    A resposta a consulta entra ao ser publicada; o acórdão só depois de
    selecionado e ementado. Uma data só para o acervo faria quem pergunta pelo
    julgado mais recente receber a de uma camada e atribuí-la ao todo.
    """
    especies = acervo.cobertura()["ementas"]["por_especie"]
    assert especies, "sem espécies na cobertura"
    for e in especies:
        assert "julgado_mais_recente" in e
        assert "sem_data_de_sessao" in e
    obs = acervo.cobertura()["ementas"]["sobre_a_data_mais_recente"]
    assert "POR ESPÉCIE" in obs
    assert "Pesquisa Textual" in obs


def test_resposta_a_consulta_tem_link_do_documento():
    """Sem o link, a citação obriga a confiar — e foi o que aconteceu.

    O inteiro teor das respostas foi coletado e o link continuou vazio, porque
    `montar_url_pdf` só sabia montar o do acórdão. Quem consultava recebia o
    endereço do processo e o do portal, nunca o do documento, e não tinha como
    conferir o que estava sendo citado.
    """
    from ementario.acervo import montar_url_pdf

    # Acórdão: por número e ano.
    assert montar_url_pdf("acordao", "17798", 2026).endswith(
        "/acordao/17798/2026?votoInteiro=true")
    # Resposta a consulta: pelo arquivoId, que vem na listagem.
    assert montar_url_pdf("resposta_consulta", "74", 2018, 613).endswith(
        "/api/file/613")
    # Sem arquivoId não se inventa endereço.
    assert montar_url_pdf("resposta_consulta", "74", 2018) is None
    # Súmula não tem documento próprio: o enunciado É o ato.
    assert montar_url_pdf("sumula", "1", 2018, 999) is None


def test_servidor_nao_depende_do_coletor():
    """A imagem leva só `ementario/`; `tcerj/` é o coletor e fica de fora.

    Importar do coletor no caminho de leitura derruba TODA busca em produção
    com `No module named 'tcerj'` — e não aparece em teste algum, porque na
    máquina de desenvolvimento os dois pacotes estão presentes. Aconteceu.

    Este teste lê o código-fonte em vez de importar, que é a única forma de
    detectar a dependência sem reproduzir o ambiente da imagem.
    """
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parent.parent / "ementario"
    ofensores = []
    for arquivo in raiz.glob("*.py"):
        for n, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
            despido = linha.strip()
            if despido.startswith(("import tcerj", "from tcerj")):
                ofensores.append(f"{arquivo.name}:{n}  {despido}")
    assert not ofensores, "o servidor importa do coletor: " + "; ".join(ofensores)



def test_acervo_e_somente_leitura(acervo):
    import sqlite3

    with pytest.raises(sqlite3.OperationalError):
        acervo.conexao.execute("DELETE FROM documentos")


def test_acervo_inexistente_falha_com_instrucao(tmp_path):
    with pytest.raises(FileNotFoundError, match="coletar"):
        Acervo(tmp_path / "nao-existe.sqlite")


# -- servidor ---------------------------------------------------------------


def test_servidor_expoe_as_ferramentas(acervo):
    import asyncio

    from ementario.servidor import construir

    servidor = construir(acervo.caminho)
    nomes = {f.name for f in asyncio.run(servidor.list_tools())}
    assert {"pesquisar_jurisprudencia", "obter_documento", "listar_documentos",
            "cobertura_do_acervo"} <= nomes
    # O ChatGPT exige exatamente estes dois nomes na pesquisa profunda.
    assert {"search", "fetch"} <= nomes


def test_sem_dominio_declarado_so_passa_requisicao_local():
    """Padrão trancado: servir para fora exige dizer por onde."""
    from ementario.servidor import seguranca_de_transporte

    s = seguranca_de_transporte(None)
    assert s.enable_dns_rebinding_protection is True
    assert "localhost" in s.allowed_hosts
    assert not any("cloudflare" in h or "chatgpt" in h for h in s.allowed_hosts)


def test_dominio_declarado_e_liberado_sem_abrir_para_os_demais():
    from ementario.servidor import seguranca_de_transporte

    s = seguranca_de_transporte(["https://abc-def.trycloudflare.com/"])
    # Aceita a URL completa e guarda só o host.
    assert "abc-def.trycloudflare.com" in s.allowed_hosts
    assert "https://abc-def.trycloudflare.com" in s.allowed_origins
    assert "https://chatgpt.com" in s.allowed_origins
    # Não vira curinga: o resto do mundo continua de fora.
    assert "invasor.example.com" not in s.allowed_hosts
    assert "*" not in s.allowed_hosts
    # O acesso local não se perde ao publicar.
    assert "localhost" in s.allowed_hosts


# -- OAuth sem estado -------------------------------------------------------


def test_selo_recusa_carga_adulterada():
    from ementario.autenticacao import Selo

    selo = Selo("segredo")
    bom = selo.selar("acesso", {"c": "cliente-1"}, 60)
    assert selo.abrir("acesso", bom)["c"] == "cliente-1"

    corpo, assinatura = bom.split(".", 1)
    assert selo.abrir("acesso", f"{corpo}x.{assinatura}") is None
    assert selo.abrir("acesso", f"{corpo}.{assinatura[:-2]}xy") is None
    assert selo.abrir("acesso", "lixo") is None


def test_selo_recusa_chave_diferente():
    from ementario.autenticacao import Selo

    emitido = Selo("segredo-a").selar("acesso", {"c": "x"}, 60)
    assert Selo("segredo-b").abrir("acesso", emitido) is None


def test_codigo_de_autorizacao_nao_vale_como_token():
    """Ambos são assinados pela mesma chave; só o tipo os distingue."""
    from ementario.autenticacao import Selo

    selo = Selo("segredo")
    codigo = selo.selar("codigo", {"c": "x"}, 60)
    assert selo.abrir("acesso", codigo) is None
    assert selo.abrir("codigo", codigo) is not None


def test_selo_expira():
    from ementario.autenticacao import Selo

    selo = Selo("segredo")
    assert selo.abrir("acesso", selo.selar("acesso", {"c": "x"}, -1)) is None


def test_cliente_e_reconstruido_sem_armazenamento():
    """O serviço dorme e reinicia; o cadastro tem de sobreviver a isso."""
    import asyncio

    from mcp.shared.auth import OAuthClientInformationFull

    from ementario.autenticacao import ProvedorOAuth, Selo

    provedor = ProvedorOAuth(Selo("segredo"))
    info = OAuthClientInformationFull(
        client_id="ignorado",
        redirect_uris=["https://chatgpt.com/retorno"],
        client_name="ChatGPT",
        token_endpoint_auth_method="client_secret_post",
    )
    asyncio.run(provedor.register_client(info))

    # Outra instância, sem nenhuma memória da anterior.
    recuperado = asyncio.run(ProvedorOAuth(Selo("segredo")).get_client(info.client_id))
    assert recuperado is not None
    assert str(recuperado.redirect_uris[0]) == "https://chatgpt.com/retorno"
    assert recuperado.client_secret == info.client_secret

    assert asyncio.run(ProvedorOAuth(Selo("outro")).get_client(info.client_id)) is None


def test_servidor_avisa_o_modelo_sobre_os_limites_da_base(acervo):
    from ementario.servidor import INSTRUCOES

    # Sem isto o modelo trata a curadoria como se fosse o acervo completo.
    assert "Selecionada" in INSTRUCOES
    assert "não prova" in INSTRUCOES.lower() or "NÃO prova" in INSTRUCOES
