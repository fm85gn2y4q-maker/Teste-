import pytest

from tcerj.config import Config
from tcerj.descoberta import (
    ChamadaCapturada,
    Relatorio,
    inferir_api,
    localizar_lista,
    pontuar,
)

RESPOSTA_JURISPRUDENCIA = {
    "content": [
        {
            "numeroAcordao": "1234",
            "ano": 2020,
            "relator": "Conselheiro Fulano",
            "ementa": "Licitação. Dispensa indevida.",
            "numeroProcesso": "210.123-4/2019",
        },
        {
            "numeroAcordao": "1235",
            "ano": 2020,
            "relator": "Conselheiro Beltrano",
            "ementa": "Contrato administrativo.",
            "numeroProcesso": "210.124-2/2019",
        },
    ],
    "totalElements": 4321,
    "number": 0,
}


def chamada(url="https://www.tcerj.tc.br/api/jurisprudencia/busca", **kwargs):
    base = dict(
        url=url,
        metodo="POST",
        cabecalhos={"content-type": "application/json", "cookie": "x=1"},
        corpo_requisicao={"page": 0, "size": 20, "termo": "licitação"},
        status=200,
        tipo_conteudo="application/json",
        amostra=RESPOSTA_JURISPRUDENCIA,
    )
    base.update(kwargs)
    return ChamadaCapturada(**base)


@pytest.mark.parametrize(
    "dados,caminho,quantidade",
    [
        ({"content": [{"a": 1}, {"b": 2}]}, "content", 2),
        ({"dados": {"itens": [{"a": 1}]}}, "dados.itens", 1),
        ([{"a": 1}], "", 1),
        ({"vazio": [], "cheio": [{"a": 1}]}, "cheio", 1),
        ({"numeros": [1, 2, 3]}, "", 0),
        ({"a": 1}, "", 0),
    ],
)
def test_localizar_lista(dados, caminho, quantidade):
    assert localizar_lista(dados) == (caminho, quantidade)


def test_localiza_a_maior_lista_de_objetos():
    dados = {"filtros": [{"id": 1}], "resultados": [{"id": i} for i in range(9)]}
    assert localizar_lista(dados) == ("resultados", 9)


def test_pontua_resposta_de_jurisprudencia_acima_de_ruido():
    jurisprudencia = pontuar(chamada())
    ruido = pontuar(
        chamada(
            url="https://www.tcerj.tc.br/api/menu",
            amostra={"itens": [{"rotulo": "Início"}, {"rotulo": "Contato"}]},
        )
    )
    assert jurisprudencia.pontuacao > ruido.pontuacao
    assert jurisprudencia.caminho_itens == "content"
    assert jurisprudencia.campo_total == "totalElements"
    assert jurisprudencia.quantidade_itens == 2


def test_resposta_sem_lista_nao_pontua():
    assert pontuar(chamada(amostra={"status": "ok"})).pontuacao == 0


def test_relatorio_escolhe_a_melhor_chamada():
    relatorio = Relatorio(
        chamadas=[
            pontuar(chamada(url="https://x/api/menu", amostra={"itens": [{"a": 1}]})),
            pontuar(chamada()),
        ]
    )
    melhor = relatorio.melhor()
    assert melhor is not None
    assert "jurisprudencia" in melhor.url


def test_relatorio_sem_candidatas_retorna_none():
    assert Relatorio(chamadas=[pontuar(chamada(amostra={"a": 1}))]).melhor() is None


def test_inferir_api_extrai_paginacao_do_corpo():
    api = inferir_api(pontuar(chamada()))
    assert api.url == "https://www.tcerj.tc.br/api/jurisprudencia/busca"
    assert api.metodo == "POST"
    assert api.campo_pagina == "page"
    assert api.campo_tamanho == "size"
    assert api.primeira_pagina == 0
    assert api.tamanho_pagina == 20
    assert api.caminho_itens == "content"
    assert api.caminho_total == "totalElements"


def test_inferir_api_extrai_paginacao_da_query_string():
    api = inferir_api(
        pontuar(
            chamada(
                url="https://www.tcerj.tc.br/api/acordaos?pagina=1&tamanho=100&termo=obra",
                metodo="GET",
                corpo_requisicao=None,
            )
        )
    )
    assert api.url == "https://www.tcerj.tc.br/api/acordaos"  # sem a query
    assert api.campo_pagina == "pagina"
    assert api.campo_tamanho == "tamanho"
    assert api.primeira_pagina == 1
    assert api.tamanho_pagina == 100
    assert api.parametros["termo"] == "obra"


def test_inferir_api_identifica_o_campo_do_termo_de_busca():
    # A sonda buscou "licitação"; o campo que carrega esse valor é o de texto.
    api = inferir_api(pontuar(chamada()), termo="licitação")
    assert api.campo_termo == "termo"

    api = inferir_api(
        pontuar(chamada(corpo_requisicao={"page": 0, "size": 20, "palavraChave": "obra"})),
        termo="obra",
    )
    assert api.campo_termo == "palavraChave"


def test_campo_do_termo_cai_no_padrao_quando_nao_identificado():
    assert inferir_api(pontuar(chamada()), termo=None).campo_termo == "termo"


def test_inferir_api_marca_paginacao_embutida_na_rota():
    """O portal do TCE-RJ pagina pelo caminho, não por parâmetro."""
    api = inferir_api(
        pontuar(
            chamada(
                url="https://www.tcerj.tc.br/liana-processo-webapi/consulta"
                    "/pagina/1/tamanhoPagina/10",
                corpo_requisicao={"texto": "licitação"},
            )
        ),
        termo="licitação",
    )
    assert api.url == (
        "https://www.tcerj.tc.br/liana-processo-webapi/consulta"
        "/pagina/{pagina}/tamanhoPagina/{tamanho}"
    )
    assert api.primeira_pagina == 1
    assert api.tamanho_pagina == 10
    # O termo da sonda não pode ficar gravado filtrando a coleta.
    assert api.corpo == {}
    assert api.campo_termo == "texto"


def test_inferir_api_preserva_filtros_que_nao_sao_o_termo():
    api = inferir_api(
        pontuar(chamada(corpo_requisicao={"page": 0, "size": 20, "orgao": "plenario"})),
        termo="licitação",
    )
    assert api.corpo["orgao"] == "plenario"


def test_inferir_api_nao_propaga_cabecalhos_sensiveis():
    api = inferir_api(pontuar(chamada()))
    assert "cookie" not in {k.lower() for k in api.cabecalhos}
    assert api.cabecalhos["content-type"] == "application/json"


def test_relatorio_salva_sem_credenciais(tmp_path):
    caminho = Relatorio(chamadas=[pontuar(chamada())]).salvar(tmp_path / "d.json")
    conteudo = caminho.read_text(encoding="utf-8")
    assert "jurisprudencia" in conteudo
    # O relatório é gravado em disco: não pode carregar cookie de sessão.
    assert "cookie" not in conteudo.lower()
    assert "content-type" in conteudo.lower()  # cabeçalhos úteis permanecem


def test_config_ida_e_volta(tmp_path):
    config = Config()
    config.api = inferir_api(pontuar(chamada()))
    config.backend = "api"
    destino = tmp_path / "config.json"
    config.salvar(destino)

    recarregada = Config.carregar(destino)
    assert recarregada.backend == "api"
    assert recarregada.api.url == config.api.url
    assert recarregada.api.caminho_itens == "content"


def test_config_rejeita_chave_desconhecida():
    with pytest.raises(ValueError, match="desconhecidas"):
        Config.de_dict({"base_url": "https://x", "chave_invalida": 1})


def test_url_absoluta():
    config = Config(base_url="https://www.tcerj.tc.br")
    assert config.url_absoluta("/a/b") == "https://www.tcerj.tc.br/a/b"
    assert config.url_absoluta("https://outro/x") == "https://outro/x"
