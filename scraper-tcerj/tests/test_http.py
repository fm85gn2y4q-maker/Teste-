"""O freio de série: quando o servidor recusa, a coleta para em vez de insistir.

A repetição por requisição resolve a falha isolada. O que ela não resolve — e
o que estes testes fixam — é o servidor passando a recusar tudo: sem freio, uma
fila de vinte e três mil acórdãos insistiria por horas contra um servidor
público que está pedindo para parar.
"""

import asyncio

import httpx
import pytest

from tcerj.config import Config
from tcerj.http import ErroHttp, ServidorRecusando


def montar(respostas, *, maximo=3):
    """Um cliente cujas respostas vêm de uma lista, sem rede nem robots.txt."""
    from tcerj.http import Cliente

    config = Config(intervalo_seg=0, tentativas=1, timeout_seg=1)
    cliente = Cliente(config)
    cliente.recusas_maximas = maximo
    fila = list(respostas)

    def responder(requisicao):
        status = fila.pop(0) if fila else 200
        return httpx.Response(status, content=b"ok")

    cliente._cliente = httpx.AsyncClient(transport=httpx.MockTransport(responder))
    # O robots.txt é assunto de outra camada; aqui interessa só a série.
    cliente.permitido = lambda url: asyncio.sleep(0, result=True)
    return cliente


async def pedir(cliente, quantas):
    vistos = []
    for i in range(quantas):
        try:
            await cliente.obter(f"https://exemplo.test/{i}")
            vistos.append("ok")
        except ErroHttp:
            vistos.append("erro")
    return vistos


def test_recusas_seguidas_encerram_a_coleta():
    cliente = montar([429, 429, 429, 429], maximo=3)
    with pytest.raises(ServidorRecusando, match="3 recusas seguidas"):
        asyncio.run(pedir(cliente, 4))


def test_acesso_negado_tambem_conta():
    """403 é recusa tanto quanto 429 — insistir contra ele é pior ainda."""
    cliente = montar([403, 403, 403], maximo=3)
    with pytest.raises(ServidorRecusando, match="403"):
        asyncio.run(pedir(cliente, 3))


def test_sucesso_no_meio_zera_a_contagem():
    """Oscilação não é recusa em série; senão o freio dispararia à toa."""
    cliente = montar([429, 429, 200, 429, 429], maximo=3)
    assert asyncio.run(pedir(cliente, 5)) == ["erro", "erro", "ok", "erro", "erro"]


def test_documento_inexistente_nao_conta_como_recusa():
    """404 é resposta legítima: o Tribunal não publicou aquele acórdão.

    Um servidor que ainda distingue o que existe do que não existe não está
    negando acesso — e a fila tem 404 de sobra, que travariam a coleta inteira.
    """
    cliente = montar([404] * 20, maximo=3)
    assert asyncio.run(pedir(cliente, 20)) == ["erro"] * 20


def test_a_parada_nao_e_confundida_com_falha_de_um_documento():
    """Quem coleta trata `ErroHttp` por documento e segue; isto não pode ser.

    Se `ServidorRecusando` herdasse de `ErroHttp`, o `except` que existe no
    laço de coleta a engoliria e a fila continuaria — anulando o freio.
    """
    assert not issubclass(ServidorRecusando, ErroHttp)
