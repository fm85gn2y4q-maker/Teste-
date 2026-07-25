import asyncio

import pytest

from tcerj.config import Config, ConfigApi
from tcerj.modelos import TipoDocumento
from tcerj.pipeline import caminhar, coletar_via_api


class RespostaFalsa:
    def __init__(self, dados):
        self._dados = dados

    def json(self):
        return self._dados


class ClienteFalso:
    """Substitui o cliente HTTP registrando as chamadas recebidas."""

    def __init__(self, paginas):
        self.paginas = paginas
        self.chamadas = []

    async def requisitar(self, metodo, url, *, params=None, json_body=None, headers=None):
        self.chamadas.append(
            {"metodo": metodo, "url": url, "params": params, "corpo": json_body}
        )
        indice = len(self.chamadas) - 1
        dados = self.paginas[indice] if indice < len(self.paginas) else {"content": []}
        return RespostaFalsa(dados)


def registros(inicio, quantidade):
    return [
        {
            "numeroAcordao": str(inicio + i),
            "ano": "2020",
            "tipoDocumento": "Acórdão",
            "ementa": f"Ementa {inicio + i}",
        }
        for i in range(quantidade)
    ]


def config_api(**kwargs):
    api = ConfigApi(url="https://exemplo/api/busca", caminho_itens="content", **kwargs)
    return Config(api=api, backend="api")


async def coletar(config, cliente, **kwargs):
    return [d async for d in coletar_via_api(config, cliente, **kwargs)]


@pytest.mark.parametrize(
    "dados,caminho,esperado",
    [
        ({"content": [1, 2]}, "content", [1, 2]),
        ({"dados": {"itens": [1]}}, "dados.itens", [1]),
        ([1, 2, 3], "", [1, 2, 3]),
        ({"a": 1}, "b", None),
        ({"a": {"b": None}}, "a.b.c", None),
        ({"lista": [{"x": 9}]}, "lista.0.x", 9),
    ],
)
def test_caminhar(dados, caminho, esperado):
    assert caminhar(dados, caminho) == esperado


def test_pagina_ate_o_fim_dos_resultados():
    cliente = ClienteFalso([
        {"content": registros(1, 3)},
        {"content": registros(4, 3)},
        {"content": []},
    ])
    docs = asyncio.run(coletar(config_api(tamanho_pagina=3), cliente))

    assert len(docs) == 6
    assert [d.numero for d in docs] == ["1", "2", "3", "4", "5", "6"]
    assert len(cliente.chamadas) == 3
    assert cliente.chamadas[0]["params"]["page"] == 0
    assert cliente.chamadas[1]["params"]["page"] == 1


def test_para_ao_atingir_o_total_informado():
    cliente = ClienteFalso([
        {"content": registros(1, 2), "totalElements": 2},
        {"content": registros(3, 2)},
    ])
    config = config_api(tamanho_pagina=2)
    config.api.caminho_total = "totalElements"
    docs = asyncio.run(coletar(config, cliente))

    assert len(docs) == 2
    assert len(cliente.chamadas) == 1  # não pediu a segunda página


def test_respeita_max_documentos():
    cliente = ClienteFalso([{"content": registros(1, 50)}])
    docs = asyncio.run(coletar(config_api(), cliente, max_documentos=5))
    assert len(docs) == 5


def test_respeita_max_paginas():
    cliente = ClienteFalso([{"content": registros(i, 2)} for i in range(1, 20)])
    docs = asyncio.run(coletar(config_api(tamanho_pagina=2), cliente, max_paginas=3))
    assert len(cliente.chamadas) == 3
    assert len(docs) == 6


def test_paginacao_por_deslocamento_avanca_em_registros():
    cliente = ClienteFalso([{"content": registros(1, 10)}, {"content": []}])
    config = config_api(campo_pagina="offset", campo_tamanho="limit", tamanho_pagina=10)
    asyncio.run(coletar(config, cliente))

    assert cliente.chamadas[0]["params"]["offset"] == 0
    assert cliente.chamadas[1]["params"]["offset"] == 10  # e não 1


def test_paginacao_vai_no_corpo_quando_a_requisicao_usa_post():
    cliente = ClienteFalso([{"content": registros(1, 2)}, {"content": []}])
    config = config_api(tamanho_pagina=2)
    config.api.metodo = "POST"
    config.api.corpo = {"page": 0, "size": 2, "filtro": "x"}
    asyncio.run(coletar(config, cliente))

    assert cliente.chamadas[1]["corpo"]["page"] == 1
    assert cliente.chamadas[1]["corpo"]["filtro"] == "x"  # preserva o filtro original
    assert "page" not in (cliente.chamadas[1]["params"] or {})


def test_tipo_esperado_e_aplicado_aos_registros():
    cliente = ClienteFalso([
        {"content": [{"numero": "7", "ano": "2021", "ementa": "texto"}]},
        {"content": []},
    ])
    docs = asyncio.run(coletar(config_api(), cliente, tipo=TipoDocumento.ENUNCIADO))
    assert docs[0].tipo is TipoDocumento.ENUNCIADO


def test_erro_claro_quando_endpoint_nao_configurado():
    config = Config(backend="api")
    with pytest.raises(ValueError, match="descobrir"):
        asyncio.run(coletar(config, ClienteFalso([])))


def test_resposta_sem_lista_encerra_sem_erro():
    cliente = ClienteFalso([{"mensagem": "sem resultados"}])
    assert asyncio.run(coletar(config_api(), cliente)) == []
