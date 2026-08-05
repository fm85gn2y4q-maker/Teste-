"""O prazo de validade — o risco próprio das manifestações referenciais.

Um referencial vencido e um em vigor têm o mesmo texto. A diferença está na
data, e usar o vencido para dispensar análise individualizada é vício no
processo administrativo. Estes testes existem para que essa diferença nunca
fique implícita.
"""

from __future__ import annotations

from datetime import date, timedelta

import autoridade
import pytest

from agu.acervo import Documento


def _referencial(validade: str | None) -> Documento:
    campos = {n: None for n in Documento.__dataclass_fields__}
    campos.update(codigo=1, fonte="referencial",
                  especie="Manifestação Jurídica Referencial",
                  citacao="PARECER REFERENCIAL Nº 00001/2020/CONJUR-X/CGU/AGU",
                  ano=2020, paginas=0, tem_texto=1, validade=validade,
                  trechos=[])
    return Documento(**campos)


def test_vencido_traz_aviso_que_impede_a_dispensa():
    ontem = (date.today() - timedelta(days=1)).isoformat()
    d = _referencial(ontem).para_dict()
    assert d["vencido"] is True
    assert "NÃO dispensa" in d["aviso_validade"]
    assert "vício no processo" in d["aviso_validade"]


def test_em_vigor_nao_finge_certeza_sobre_a_contagem_do_prazo():
    """O prazo corre da aprovação definitiva, que não está neste acervo."""
    amanha = (date.today() + timedelta(days=1)).isoformat()
    d = _referencial(amanha).para_dict()
    assert d["vencido"] is False
    assert "aprovação definitiva" in d["aviso_validade"]


def test_sem_prazo_nao_e_prazo_indeterminado():
    d = _referencial(None).para_dict()
    assert "vencido" not in d
    assert "não é prazo indeterminado" in d["aviso_validade"]


def test_o_vencimento_e_calculado_hoje_nao_gravado(acervo):
    """Gravar 'vencido' no índice congelaria a resposta na data em que o acervo
    foi construído, e ela envelheceria em silêncio."""
    colunas = [r[1] for r in acervo.con.execute("PRAGMA table_info(documentos)")]
    assert "validade" in colunas
    assert "vencido" not in colunas


def test_referencial_nao_e_tese_de_alcance_geral():
    chave, _, explicacao = autoridade.classificar(
        "Manifestação Jurídica Referencial", None)
    assert chave == "processo"
    assert "prazo de validade" in explicacao


def test_a_ferramenta_separa_em_vigor_de_vencido(acervo):
    r = acervo.referenciais("licitação contratação", limite=5)
    assert r["data_da_consulta"] == date.today().isoformat()
    for d in r["em_vigor"]:
        assert d["vencido"] is False
    for d in r["vencidos"]:
        assert d["vencido"] is True
        assert "vício no processo" in d["aviso_validade"]


def test_so_em_vigor_nao_devolve_vencido(acervo):
    r = acervo.referenciais("contratação", limite=5, so_validos=True)
    assert r["vencidos"] == []


def test_todos_os_referenciais_declaram_abrangencia(acervo):
    """Um referencial de órgão em Brasília não serve a órgão nos Estados."""
    sem = acervo.con.execute(
        "SELECT COUNT(*) FROM documentos WHERE fonte='referencial' "
        "AND (abrangencia IS NULL OR abrangencia = '')").fetchone()[0]
    assert sem <= 1, "a decodificação da abrangência regrediu"


def test_cobertura_declara_o_prazo_como_panorama_e_nao_como_resposta(acervo):
    cob = acervo.cobertura()
    assert "referenciais_por_prazo" in cob
    assert "data de hoje" in cob["nota_sobre_o_prazo"]
    limites = " ".join(cob["limites"])
    assert "PRAZO DE VALIDADE" in limites
