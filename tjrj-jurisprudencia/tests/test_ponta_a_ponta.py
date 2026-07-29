"""Ponta a ponta com um coletor falso.

Exercita banco, ingestão, deduplicação, extração de composição e as
ferramentas do MCP sem tocar em rede. É este teste que garante que trocar o
coletor real por outro não quebra nada do resto.
"""

from datetime import date, timedelta

import pytest

from tjrj.crawl.base import Referencia, ResultadoBusca, Teor
from tjrj.crawl.planner import Fatia

TEOR = """
DÉCIMA CÂMARA CÍVEL
Apelação Cível nº {num}
Relator: Des. João Carlos de Almeida

EMENTA. CONSUMIDOR. NEGATIVAÇÃO INDEVIDA. DANO MORAL CONFIGURADO.
A inscrição indevida em cadastro restritivo gera dano moral in re ipsa.

ACORDAM os Desembargadores que integram a Décima Câmara Cível, por
unanimidade, em DAR PROVIMENTO ao recurso, nos termos do voto do Relator.

Votaram os Desembargadores: Maria Helena Rocha e Pedro Álvares Cabral Neto.
Presidiu o julgamento o Desembargador Antônio Vieira Lima.

Rio de Janeiro, {dia} de março de 2024.
"""


class ColetorFalso:
    nome = "ejuris"

    def __init__(self, por_dia: int = 3):
        self.por_dia = por_dia
        self.pedidos: list[str] = []

    def _numeros(self, d: date):
        for i in range(self.por_dia):
            seq = f"{d.toordinal() % 10000000:07d}"
            yield f"{seq}-{i:02d}.2024.8.19.0001", d

    def contar(self, fatia: Fatia) -> int:
        return self.por_dia * fatia.dias

    def listar(self, fatia: Fatia):
        self.pedidos.append(fatia.chave())
        for offset in range(fatia.dias):
            d = fatia.inicio + timedelta(days=offset)
            for num, dia in self._numeros(d):
                yield ResultadoBusca(
                    referencia=Referencia(id_externo=num, sistema="ejuris", url=f"x://{num}"),
                    numero_cnj=num,
                    orgao_julgador="DÉCIMA CÂMARA CÍVEL",
                    classe="Apelação Cível",
                    data_julgamento=dia,
                    ementa="CONSUMIDOR. NEGATIVAÇÃO INDEVIDA. DANO MORAL CONFIGURADO.",
                    url_fonte=f"https://exemplo/{num}",
                )

    def obter_teor(self, ref: Referencia):
        return Teor(
            referencia=ref,
            paginas=[TEOR.format(num=ref.id_externo, dia=12), "Segunda página do voto."],
            origem="pdf",
        )

    def valores_de_faceta(self, chave, fatia):
        return []


@pytest.fixture()
def acervo(tmp_path, monkeypatch):
    """Aponta a configuração global para um banco temporário.

    O MCP e o pipeline compartilham o mesmo objeto CFG, então basta trocar
    o caminho do banco — é assim que a CLI também faz.
    """
    from tjrj import db
    from tjrj.config import CFG

    banco = tmp_path / "acervo.db"
    monkeypatch.setattr(CFG, "banco", banco)
    monkeypatch.setattr(CFG, "cache", tmp_path / "cru")

    con = db.conectar(banco)
    db.migrar(con)
    con.close()
    return banco


def _coletar(acervo, coletor, dias=3):
    from tjrj.config import CFG
    from tjrj.pipeline.ingest import coletar

    return coletar(coletor, date(2024, 3, 1), date(2024, 3, dias), cfg=CFG, com_teor=True)


def test_coleta_grava_acordaos_e_teor(acervo):
    resumo = _coletar(acervo, ColetorFalso())
    assert resumo["encontrados"] == 9  # 3 dias x 3
    assert resumo["novos"] == 9
    assert resumo["com_teor"] == 9
    assert resumo["erros"] == 0


def test_coleta_e_idempotente(acervo):
    coletor = ColetorFalso()
    _coletar(acervo, coletor)
    segunda = _coletar(acervo, coletor)
    assert segunda["puladas"] >= 1      # retomada pulou o que já terminou
    assert segunda["novos"] == 0        # e nada duplicou

    from tjrj.db import conectar

    con = conectar(acervo)
    assert con.execute("SELECT COUNT(*) FROM acordao").fetchone()[0] == 9
    con.close()


def test_composicao_foi_extraida_e_normalizada(acervo):
    _coletar(acervo, ColetorFalso())
    from tjrj.db import conectar

    con = conectar(acervo)
    papeis = dict(
        con.execute(
            "SELECT j.nome, p.papel FROM participacao p JOIN julgador j ON j.id = p.julgador_id"
            " JOIN acordao a ON a.id = p.acordao_id GROUP BY j.nome, p.papel"
        ).fetchall()
    )
    assert papeis["João Carlos de Almeida"] == "relator"
    assert papeis["Maria Helena Rocha"] == "vogal"
    assert papeis["Antônio Vieira Lima"] == "presidente"
    # Um julgador, uma linha em `julgador` — não um por acórdão.
    assert con.execute("SELECT COUNT(*) FROM julgador").fetchone()[0] == 4
    con.close()


def test_busca_em_ementa_e_em_teor_sao_diferentes(acervo):
    _coletar(acervo, ColetorFalso())
    from tjrj.mcp.server import pesquisar_inteiro_teor, pesquisar_jurisprudencia

    em_ementa = pesquisar_jurisprudencia("negativação indevida")
    assert em_ementa["total"] > 0
    assert em_ementa["resultados"][0]["origem_da_proposicao"] == "ementa"

    # "in re ipsa" só existe no corpo do voto, não na ementa gravada.
    assert pesquisar_jurisprudencia("in re ipsa")["total"] == 0
    no_teor = pesquisar_inteiro_teor("in re ipsa")
    assert no_teor["total"] > 0
    assert no_teor["resultados"][0]["pagina"] == 1
    assert "p. 1" in no_teor["resultados"][0]["origem_da_proposicao"]


def test_documento_traz_composicao_e_paginas(acervo):
    _coletar(acervo, ColetorFalso())
    from tjrj.mcp.server import ler_paginas, obter_documento, pesquisar_jurisprudencia

    ident = pesquisar_jurisprudencia("dano moral")["resultados"][0]["id"]
    doc = obter_documento(ident)
    assert doc["orgao_julgador"] == "DÉCIMA CÂMARA CÍVEL"
    assert doc["paginas_de_inteiro_teor"] == 2
    papeis = {p["papel"] for p in doc["composicao_do_julgamento"]}
    assert {"relator", "vogal", "presidente"} <= papeis

    paginas = ler_paginas(ident, 1, 5)
    assert paginas["total_de_paginas"] == 2
    assert paginas["paginas"][0]["origem_do_texto"] == "pdf"


def test_entendimento_do_relator(acervo):
    _coletar(acervo, ColetorFalso())
    from tjrj.mcp.server import entendimento_do_relator

    r = entendimento_do_relator("JOAO CARLOS DE ALMEIDA", consulta="dano moral")
    assert r["total"] == 9
    assert all(j["papel"] == "relator" for j in r["julgados"])


def test_cobertura_declara_limites(acervo):
    _coletar(acervo, ColetorFalso())
    from tjrj.mcp.server import cobertura_do_acervo

    cob = cobertura_do_acervo()
    assert cob["por_sistema"][0]["documentos"] == 9
    assert cob["por_sistema"][0]["com_inteiro_teor"] == 9
    assert cob["fatias_com_erro"] == 0
    assert any("não é prova de inexistência" in x for x in cob["limites_conhecidos"])


def test_consulta_malformada_nao_explode(acervo):
    _coletar(acervo, ColetorFalso())
    from tjrj.mcp.server import pesquisar_jurisprudencia

    # Aspas ímpares quebrariam o FTS5 se a consulta fosse repassada crua.
    assert pesquisar_jurisprudencia('dano "moral').get("total") is not None
    assert pesquisar_jurisprudencia("").get("total") == 0
