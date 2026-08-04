"""O pipeline não pode falhar em silêncio.

Cada teste aqui corresponde a um erro que já aconteceu, e todos são da mesma
família: o programa termina com código zero, anuncia sucesso, e destrói ou
esconde alguma coisa.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import indexar
import pytest


def test_indexar_recusa_matéria_prima_ausente(tmp_path, monkeypatch):
    """O erro que custou uma recoleta: os .jsonl ficam fora do Git e ao lado
    dos scripts. Apagada a pasta, o indexador rodava até o fim, anunciava
    sucesso com zero documentos — e, como apaga o banco antes de reconstruir,
    levava o acervo bom junto."""
    banco = tmp_path / "acervo.db"
    sqlite3.connect(banco).close()
    monkeypatch.setattr(indexar, "AQUI", tmp_path)      # sem nenhum .jsonl
    monkeypatch.setattr(indexar, "BANCO", banco)
    monkeypatch.setattr(indexar, "ACERVO", tmp_path)

    with pytest.raises(SystemExit) as erro:
        indexar.main()

    assert "coletar.py" in str(erro.value)
    assert banco.exists(), "o banco anterior foi apagado apesar da falha"


def test_confianca_do_ocr_reconhece_texto_do_proprio_acervo():
    vocab = indexar._vocabulario(
        ["A Administração deve motivar seus atos conforme a legislação vigente"])
    bom = " ".join(["administração", "deve", "motivar", "seus", "atos",
                    "conforme", "legislação", "vigente"] * 3)
    assert indexar._confianca_ocr(bom, vocab) == 100


def test_confianca_do_ocr_denuncia_reconhecimento_ruim():
    vocab = indexar._vocabulario(["Administração motivar legislação vigente atos"])
    ruim = " ".join(["Luouiaçõo", "COFPESDONRQERIC", "FergNCHAÇÕO", "nmanestação",
                     "fodofosal", "fomanecel", "PEROVENTO", "wH0S", "snbDECOR",
                     "ARGL", "Ado", "podera", "ceda", "vetor", "parcela",
                     "inferior", "cento", "dez", "por", "cada", "outro"])
    assert indexar._confianca_ocr(ruim, vocab) < 30


def test_texto_curto_demais_nao_recebe_nota_de_confianca():
    """Página quase vazia acertaria por acaso e a nota mentiria."""
    vocab = indexar._vocabulario(["administração legislação"])
    assert indexar._confianca_ocr("administração legislação", vocab) == 0


def test_regime_de_8666_sem_14133_gera_alerta():
    regime, alerta = indexar._regime("aplicável a Lei nº 8.666, de 1993")
    assert "8.666" in regime
    assert alerta and "revogada" in alerta


def test_regime_de_transicao_nao_alerta_como_se_fosse_so_8666():
    """Citando as duas, o documento pode estar tratando da transição — o alerta
    de norma revogada seria enganoso."""
    regime, alerta = indexar._regime("cotejo entre a Lei 8.666/1993 e a Lei 14.133/2021")
    assert "8.666" in regime and "14.133" in regime
    assert alerta is None
