"""Integração do backend `navegador` contra um portal falso servido localmente.

Não substitui a validação contra o site real do Tribunal, mas exercita o
caminho completo — abrir a página, buscar, paginar, abrir o detalhe e extrair
os metadados — com um navegador de verdade.
"""

from __future__ import annotations

import asyncio
import functools
import http.server
import threading
from pathlib import Path

import pytest

from tcerj.config import Config, ConfigSeletores
from tcerj.modelos import TipoDocumento

playwright_sync = pytest.importorskip("playwright.sync_api")


LISTAGEM = """
<html><body>
  <h1>Consulta de Jurisprudência</h1>
  <form><input type="search" name="q" placeholder="Busque um termo"></form>
  <table><tbody>
    <tr><td>1234</td><td><a href="acordao-1234.html">Acórdão 1234/2020</a></td></tr>
    <tr><td>1235</td><td><a href="acordao-1235.html">Acórdão 1235/2020</a></td></tr>
    <tr><td>7</td><td><a href="deliberacao-7.html">Deliberação 7/2021</a></td></tr>
    <tr><td>-</td><td><a href="/ajuda">Ajuda</a></td></tr>
  </tbody></table>
  <a rel="next" href="pagina2.html">Próxima</a>
</body></html>
"""

PAGINA2 = """
<html><body>
  <table><tbody>
    <tr><td><a href="acordao-9999.html">Acórdão 9999/2022</a></td></tr>
  </tbody></table>
</body></html>
"""

DETALHE = """
<html><body><main>
  <h2>ACÓRDÃO Nº {numero}/{ano}</h2>
  <p>Processo nº 210.123-4/2019</p>
  <p>Relator: Conselheiro Marianna Montebello Willeman</p>
  <p>Sessão de 12/03/2020</p>
  <p>EMENTA: Tomada de contas. Dispensa de licitação sem amparo legal.
     Dano ao erário. Aplicação de multa ao gestor responsável.</p>
  <p>RELATÓRIO</p>
  <p>Trata-se de tomada de contas instaurada para apurar irregularidades.</p>
</main></body></html>
"""

DELIBERACAO = """
<html><body><main>
  <h2>DELIBERAÇÃO Nº 7/2021</h2>
  <p>Assuntos: Controle externo; Prestação de contas</p>
  <p>EMENTA: Dispõe sobre os prazos de remessa de prestação de contas
     pelos jurisdicionados do Tribunal de Contas do Estado.</p>
</main></body></html>
"""


@pytest.fixture(scope="module")
def portal(tmp_path_factory):
    """Sobe um servidor HTTP local com o portal falso."""
    raiz = tmp_path_factory.mktemp("portal")
    (raiz / "index.html").write_text(LISTAGEM, encoding="utf-8")
    (raiz / "pagina2.html").write_text(PAGINA2, encoding="utf-8")
    (raiz / "acordao-1234.html").write_text(
        DETALHE.format(numero="1234", ano="2020"), encoding="utf-8"
    )
    (raiz / "acordao-1235.html").write_text(
        DETALHE.format(numero="1235", ano="2020"), encoding="utf-8"
    )
    (raiz / "acordao-9999.html").write_text(
        DETALHE.format(numero="9999", ano="2022"), encoding="utf-8"
    )
    (raiz / "deliberacao-7.html").write_text(DELIBERACAO, encoding="utf-8")
    (raiz / "ajuda").write_text("<html><body>ajuda</body></html>", encoding="utf-8")

    manipulador = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(raiz)
    )
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), manipulador)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    porta = servidor.server_address[1]
    try:
        yield f"http://127.0.0.1:{porta}"
    finally:
        servidor.shutdown()
        servidor.server_close()


def config_local(base: str) -> Config:
    return Config(
        base_url=base,
        portais=["/index.html"],
        backend="navegador",
        intervalo_seg=0.05,
        respeitar_robots=False,
        seletores=ConfigSeletores(item_resultado="table tbody tr"),
    )


def coletar(config, **kwargs):
    from tcerj import navegador

    async def executar():
        return [d async for d in navegador.coletar(config, **kwargs)]

    return asyncio.run(executar())


@pytest.mark.integracao
def test_coleta_completa_no_portal_falso(portal):
    documentos = coletar(config_local(portal), max_paginas=1)

    # O link "Ajuda" não casa com o vocabulário de documento e fica de fora.
    assert len(documentos) == 3

    acordao = next(d for d in documentos if d.numero == "1234")
    assert acordao.tipo is TipoDocumento.ACORDAO
    assert acordao.ano == 2020
    assert acordao.processo == "210.123-4/2019"
    assert acordao.relator == "Marianna Montebello Willeman"
    assert acordao.data_sessao.isoformat() == "2020-03-12"
    assert acordao.ementa.startswith("Tomada de contas.")
    assert "Trata-se de tomada" not in acordao.ementa
    assert acordao.id == "acordao-1234-2020"

    deliberacao = next(d for d in documentos if d.tipo is TipoDocumento.DELIBERACAO)
    assert deliberacao.numero == "7"
    assert deliberacao.assuntos == ["Controle externo", "Prestação de contas"]


@pytest.mark.integracao
def test_pagina_seguinte_e_percorrida(portal):
    documentos = coletar(config_local(portal), max_paginas=2)
    assert {d.numero for d in documentos} == {"1234", "1235", "7", "9999"}


@pytest.mark.integracao
def test_max_documentos_interrompe_a_coleta(portal):
    assert len(coletar(config_local(portal), max_documentos=2, max_paginas=2)) == 2


@pytest.mark.integracao
def test_urls_ja_visitadas_sao_puladas(portal):
    vistos = {f"{portal}/acordao-1234.html"}
    documentos = coletar(config_local(portal), max_paginas=1, ja_visitado=vistos.__contains__)
    assert "1234" not in {d.numero for d in documentos}
    assert len(documentos) == 2


@pytest.mark.integracao
def test_busca_por_termo_nao_quebra_quando_nao_ha_formulario(portal):
    # O portal falso tem campo de busca mas nenhum resultado filtrado: a coleta
    # deve seguir normalmente em vez de abortar.
    assert coletar(config_local(portal), termo="licitação", max_paginas=1)


@pytest.mark.integracao
def test_seletor_de_item_invalido_cai_para_varredura_de_links(portal):
    config = config_local(portal)
    config.seletores.item_resultado = ".nao-existe-neste-layout"
    documentos = coletar(config, max_paginas=1)
    assert len(documentos) == 3


@pytest.mark.integracao
def test_grava_no_banco_e_permite_retomada(portal, tmp_path):
    from tcerj.armazenamento import Armazenamento
    from tcerj.pipeline import executar

    banco = tmp_path / "coleta.sqlite"
    config = config_local(portal)

    with Armazenamento(banco) as arm:
        novos, atualizados = asyncio.run(executar(config, arm, max_paginas=1))
        assert (novos, atualizados) == (3, 0)

    # Segunda passada: tudo já visitado, nada novo é baixado.
    with Armazenamento(banco) as arm:
        novos, atualizados = asyncio.run(executar(config, arm, max_paginas=1))
        assert novos == 0
        assert arm.estatisticas()["total"] == 3
        assert arm.buscar("licitação")
