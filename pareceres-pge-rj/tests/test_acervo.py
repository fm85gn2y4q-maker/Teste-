"""Consulta ao acervo. Precisa do banco; sem ele, os testes são pulados."""

import pytest

from pareceres.acervo import montar_consulta_fts


# --------------------------------------------------- tradução para o FTS5
def test_expressao_vazia():
    assert montar_consulta_fts("") == ""
    assert montar_consulta_fts("   ") == ""


def test_liga_os_termos_pelo_operador():
    assert montar_consulta_fts("licitacao convenio") == "licitacao AND convenio"
    assert montar_consulta_fts("licitacao convenio", "OR") == "licitacao OR convenio"


def test_preserva_expressao_entre_aspas():
    assert montar_consulta_fts('"ata de registro de precos"') == '"ata de registro de precos"'


def test_pontuacao_nao_quebra_a_consulta():
    """Apóstrofo, hífen e afins viravam erro de sintaxe e a consulta falhava
    inteira em vez de simplesmente achar menos."""
    for entrada in ["reequilíbrio econômico-financeiro", "art. 25, I", "d'água", "50%"]:
        assert montar_consulta_fts(entrada)  # não levanta e não vem vazio


def test_operadores_escritos_pelo_usuario_passam_adiante():
    assert montar_consulta_fts("licitacao OR convenio") == "licitacao OR convenio"


# ------------------------------------------------------------- ficha e busca
def test_cobertura_declara_os_limites(acervo):
    c = acervo.cobertura()
    assert c["documentos"] == "14420"
    assert c["paginas"] == "177156"
    assert "PERSUASIVO" in c["autoridade"]
    assert "49.139" in c["recorte"]


def test_pesquisa_por_ementa(acervo):
    achados, expressao, total = acervo.pesquisar("organização social", limite=3)
    assert total > 0 and achados
    assert expressao
    assert all(p.titulo for p in achados)


def test_pesquisa_devolve_pagina_secao_e_transcricao(acervo):
    achados, _, total = acervo.pesquisar_paginas("licitação", limite=2, paginas_por_doc=1)
    assert total > 0
    for p in achados:
        for t in p.trechos:
            d = t.para_dict()
            assert d["pagina"] >= 1
            assert d["secao"]
            assert 0 <= d["transcricao_percent"] <= 100


def test_pagina_muito_transcrita_traz_aviso(acervo):
    achados, _, _ = acervo.pesquisar_paginas("in verbis doutrina licitação",
                                             limite=8, paginas_por_doc=1)
    avisos = [t.para_dict()["aviso_proveniencia"]
              for p in achados for t in p.trechos]
    assert any(a and "transcrição" in a for a in avisos)


def test_ler_paginas_contiguas(acervo):
    achados, _, _ = acervo.pesquisar_paginas("contrato de gestão", limite=1, paginas_por_doc=1)
    doc = achados[0]
    paginas = acervo.paginas_do_documento(doc.codigo, doc.trechos[0].pagina, 2)
    assert paginas and len(paginas[0]["texto"]) > 100


# ---------------------------------------------------------------- tesauro
@pytest.mark.parametrize("termo", ["organização social", "organizacao social",
                                   "ORGANIZAÇÃO SOCIAL"])
def test_tesauro_ignora_acento_e_caixa(acervo, termo):
    """A comparação tirava o acento só do lado da consulta, e as variantes
    estão gravadas acentuadas: o tesauro não achava nada."""
    r = acervo.sinonimos(termo)
    assert r and r[0]["conceito"] == "terceiro setor"


def test_tesauro_soma_as_variantes(acervo):
    r = acervo.sinonimos("reequilibrio")
    assert r[0]["soma_documentos"] > max(v["documentos"] for v in r[0]["variantes"])


def test_termo_fora_do_tesauro(acervo):
    assert acervo.sinonimos("zzzz inexistente") == []


# --------------------------------------------------------------- citações
def test_quem_citou_agrupa_qualificadores(acervo):
    r = acervo.quem_citou("Lei 14.133", limite=3)
    assert r["encontrado"]
    assert r["documentos_que_citam"] > 500
    assert r["documentos"]


def test_quem_citou_referencia_inexistente(acervo):
    assert not acervo.quem_citou("Lei 99.999/1899")["encontrado"]


# ---------------------------------------------------------------- listagem
def test_listar_por_eixo(acervo):
    assert acervo.listar(eixo="Terceiro setor", limite=3)


def test_documento_sem_pdf_avisa(acervo):
    linha = acervo.con.execute(
        "SELECT codigo FROM documentos WHERE paginas = 0 LIMIT 1").fetchone()
    d = acervo.obter(linha[0]).para_dict()
    assert "aviso" in d and "inteiro teor" in d["aviso"]
