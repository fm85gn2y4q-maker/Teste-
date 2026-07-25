import json
from datetime import date

import pytest

from tcerj.armazenamento import Armazenamento, exportar_csv, exportar_jsonl
from tcerj.modelos import Documento, TipoDocumento


@pytest.fixture()
def banco(tmp_path):
    with Armazenamento(tmp_path / "teste.sqlite") as arm:
        yield arm


def doc(numero="1234", **kwargs):
    base = dict(
        tipo=TipoDocumento.ACORDAO,
        numero=numero,
        ano=2020,
        processo="210.123-4/2019",
        relator="Fulano de Tal",
        data_sessao=date(2020, 3, 12),
        ementa="Licitação. Dispensa indevida.",
        inteiro_teor="Texto integral do acórdão sobre dispensa de licitação.",
        assuntos=["Licitação"],
        url=f"https://exemplo/{numero}",
    )
    base.update(kwargs)
    return Documento(**base)


def test_gravar_e_recuperar(banco):
    assert banco.gravar(doc()) is True
    recuperado = banco.obter("acordao-1234-2020")
    assert recuperado is not None
    assert recuperado.relator == "Fulano de Tal"
    assert recuperado.data_sessao == date(2020, 3, 12)
    assert recuperado.assuntos == ["Licitação"]


def test_regravar_o_mesmo_documento_nao_duplica(banco):
    assert banco.gravar(doc()) is True
    assert banco.gravar(doc()) is False
    assert banco.estatisticas()["total"] == 1


def test_regravar_completa_campos_vazios_sem_sobrescrever(banco):
    banco.gravar(doc(relator="Fulano de Tal", inteiro_teor=None))
    banco.gravar(
        doc(relator="Outro Nome", inteiro_teor="Inteiro teor recuperado depois.")
    )
    final = banco.obter("acordao-1234-2020")
    assert final.relator == "Fulano de Tal"  # valor original preservado
    assert final.inteiro_teor == "Inteiro teor recuperado depois."  # lacuna preenchida


def test_visitados_permite_retomada(banco):
    assert banco.ja_visitado("https://exemplo/1") is False
    banco.marcar_visitado("https://exemplo/1", "ok")
    assert banco.ja_visitado("https://exemplo/1") is True
    banco.marcar_visitado("https://exemplo/2", "erro", "timeout")
    assert banco.ja_visitado("https://exemplo/2") is False


def test_listar_com_filtros(banco):
    banco.gravar(doc("1", ano=2019))
    banco.gravar(doc("2", ano=2020))
    banco.gravar(doc("3", ano=2020, tipo=TipoDocumento.SUMULA))

    assert len(list(banco.listar(ano=2020))) == 2
    assert len(list(banco.listar(tipo=TipoDocumento.SUMULA))) == 1
    assert len(list(banco.listar(tipo=TipoDocumento.ACORDAO, ano=2020))) == 1
    assert len(list(banco.listar(limite=2))) == 2


def test_busca_textual_ignora_acentos(banco):
    banco.gravar(doc(inteiro_teor="Contrato com dispensa de licitação irregular."))
    assert banco.buscar("licitacao")  # sem acento
    assert banco.buscar("licitação")
    assert not banco.buscar("aposentadoria")


def test_busca_reflete_atualizacao_do_texto(banco):
    banco.gravar(doc(inteiro_teor="Texto original sobre convênio."))
    assert banco.buscar("convênio")
    # Regravar não pode deixar entrada órfã no índice.
    banco.gravar(doc())
    assert len(banco.buscar("convênio")) == 1


def test_estatisticas_por_tipo(banco):
    banco.gravar(doc("1"))
    banco.gravar(doc("2"))
    banco.gravar(doc("3", tipo=TipoDocumento.DELIBERACAO))
    estat = banco.estatisticas()
    assert estat["total"] == 3
    assert estat["acordao"] == 2
    assert estat["deliberacao"] == 1


def test_exportar_jsonl(banco, tmp_path):
    banco.gravar(doc())
    destino = tmp_path / "saida.jsonl"
    assert exportar_jsonl(banco.listar(), destino) == 1

    linha = json.loads(destino.read_text(encoding="utf-8").splitlines()[0])
    assert linha["id"] == "acordao-1234-2020"
    assert linha["data_sessao"] == "2020-03-12"
    assert linha["tipo"] == "acordao"


def test_exportar_csv(banco, tmp_path):
    banco.gravar(doc("1", assuntos=["Licitação", "Multa"]))
    destino = tmp_path / "saida.csv"
    assert exportar_csv(banco.listar(), destino) == 1

    conteudo = destino.read_text(encoding="utf-8-sig")
    assert "Licitação; Multa" in conteudo
    assert "inteiro_teor" not in conteudo.splitlines()[0]  # CSV é resumo


def test_persistencia_entre_sessoes(tmp_path):
    caminho = tmp_path / "persistente.sqlite"
    with Armazenamento(caminho) as arm:
        arm.gravar(doc())
    with Armazenamento(caminho) as arm:
        assert arm.estatisticas()["total"] == 1
        assert arm.obter("acordao-1234-2020") is not None
