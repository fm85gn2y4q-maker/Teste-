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
    achados, _ = acervo.pesquisar('prescrição - "marco (art. 74)" OR NOT x')
    assert isinstance(achados, list)  # o que importa é não levantar erro


# -- busca ------------------------------------------------------------------


def test_encontra_por_termo_sem_acento(acervo):
    achados, parcial = acervo.pesquisar("visita tecnica")
    assert [r.tipo for r in achados] == ["sumula"]
    assert parcial is False


def test_abranda_para_ou_quando_o_e_nao_acha_nada(acervo):
    """Uma palavra a mais na pergunta não pode zerar o resultado."""
    achados, parcial = acervo.pesquisar("visita técnica em contrato de obra pública")
    assert achados
    assert parcial is True


def test_busca_sem_correspondencia_devolve_vazio(acervo):
    achados, parcial = acervo.pesquisar("terraplanagem marciana")
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
    assert {e["chave"] for e in c["por_especie"]} == {"acordao", "sumula"}
    assert c["macro_temas"] == ["Licitações e Contratos"]
    # A base é curadoria: o modelo precisa saber disso para não extrapolar.
    assert any("curadoria" in x.lower() or "não o conjunto" in x.lower()
               or "NÃO o conjunto" in x for x in c["limites_do_acervo"])


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
