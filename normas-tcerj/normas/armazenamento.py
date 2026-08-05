"""Banco do acervo de normas do TCE-RJ.

Duas decisões de modelagem que valem explicação:

A revogação vive em tabela própria, e não só em coluna do ato. Um ato revoga
vários, e a fonte declara os dois lados da relação — guardar só o campo
"revogado por" perderia a pergunta inversa, que é a que o advogado faz quando
quer saber o que uma norma nova derrubou.

O texto é guardado por página, como no acervo de jurisprudência, porque é a
menor âncora conferível: citar "art. 5º da Deliberação 338, p. 3" permite
conferência; citar só o ato, não.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .coleta import Ato

ESQUEMA = """
CREATE TABLE IF NOT EXISTS atos (
    id                   TEXT PRIMARY KEY,
    especie              TEXT NOT NULL,
    numero               INTEGER NOT NULL,
    ano                  INTEGER,
    titulo               TEXT,
    ementa               TEXT,
    data                 TEXT,
    arquivo_id           INTEGER,
    revogado_por_numero  INTEGER,
    revogado_em          TEXT,
    texto_revogacao      TEXT,
    e_regimento          INTEGER DEFAULT 0,
    paginas_total        INTEGER DEFAULT 0,
    caracteres           INTEGER DEFAULT 0,
    bruto                TEXT,
    falha                TEXT,
    coletado_em          TEXT
);
CREATE INDEX IF NOT EXISTS ix_atos_especie   ON atos(especie, ano);
CREATE INDEX IF NOT EXISTS ix_atos_numero    ON atos(numero);
CREATE INDEX IF NOT EXISTS ix_atos_revogado  ON atos(revogado_por_numero);

-- Quem revogou quem, nos dois sentidos.
CREATE TABLE IF NOT EXISTS revogacoes (
    revogado_id      TEXT NOT NULL,
    revogador_id     TEXT NOT NULL,
    data             TEXT,
    PRIMARY KEY (revogado_id, revogador_id)
);
CREATE INDEX IF NOT EXISTS ix_rev_revogador ON revogacoes(revogador_id);

CREATE TABLE IF NOT EXISTS paginas (
    ato_id   TEXT NOT NULL,
    pagina   INTEGER NOT NULL,
    texto    TEXT NOT NULL,
    PRIMARY KEY (ato_id, pagina)
);

CREATE VIRTUAL TABLE IF NOT EXISTS atos_fts USING fts5(
    titulo, ementa,
    content='atos', content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE VIRTUAL TABLE IF NOT EXISTS paginas_fts USING fts5(
    ato_id UNINDEXED, pagina UNINDEXED, texto,
    content='paginas', content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);
"""

GATILHOS = """
CREATE TRIGGER IF NOT EXISTS paginas_ai AFTER INSERT ON paginas BEGIN
  INSERT INTO paginas_fts(rowid, ato_id, pagina, texto)
  VALUES (new.rowid, new.ato_id, new.pagina, new.texto);
END;
CREATE TRIGGER IF NOT EXISTS paginas_ad AFTER DELETE ON paginas BEGIN
  INSERT INTO paginas_fts(paginas_fts, rowid, ato_id, pagina, texto)
  VALUES ('delete', old.rowid, old.ato_id, old.pagina, old.texto);
END;
CREATE TRIGGER IF NOT EXISTS paginas_au AFTER UPDATE ON paginas BEGIN
  INSERT INTO paginas_fts(paginas_fts, rowid, ato_id, pagina, texto)
  VALUES ('delete', old.rowid, old.ato_id, old.pagina, old.texto);
  INSERT INTO paginas_fts(rowid, ato_id, pagina, texto)
  VALUES (new.rowid, new.ato_id, new.pagina, new.texto);
END;
"""


class Armazenamento:
    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.conexao = sqlite3.connect(self.caminho)
        self.conexao.row_factory = sqlite3.Row
        self.conexao.execute("PRAGMA journal_mode=WAL")
        self.conexao.executescript(ESQUEMA)
        self.conexao.executescript(GATILHOS)
        self.conexao.commit()

    def __enter__(self) -> "Armazenamento":
        return self

    def __exit__(self, *_) -> None:
        self.fechar()

    def fechar(self) -> None:
        self.conexao.commit()
        self.conexao.close()

    # -- gravação ---------------------------------------------------------

    def gravar_atos(self, atos: Iterable[Ato]) -> int:
        agora = datetime.now(timezone.utc).isoformat()
        n = 0
        for a in atos:
            self.conexao.execute(
                "INSERT INTO atos (id, especie, numero, ano, titulo, ementa, data,"
                " arquivo_id, revogado_por_numero, revogado_em, texto_revogacao,"
                " e_regimento, bruto, coletado_em)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(id) DO UPDATE SET"
                "  titulo=excluded.titulo, ementa=excluded.ementa,"
                "  revogado_por_numero=excluded.revogado_por_numero,"
                "  revogado_em=excluded.revogado_em,"
                "  texto_revogacao=excluded.texto_revogacao,"
                "  bruto=excluded.bruto, coletado_em=excluded.coletado_em",
                (a.id, a.especie, a.numero, a.ano, a.titulo, a.ementa, a.data,
                 a.arquivo_id, a.revogado_por_numero, a.revogado_em,
                 a.texto_revogacao, int(a.e_regimento), a.bruto, agora),
            )
            for especie, numero in a.revogou:
                alvo = self._identificar(especie, numero)
                if alvo:
                    self.conexao.execute(
                        "INSERT OR REPLACE INTO revogacoes (revogado_id, revogador_id,"
                        " data) VALUES (?,?,?)", (alvo, a.id, a.revogado_em or a.data))
            n += 1
        self.conexao.commit()
        self._reindexar_atos()
        return n

    def _identificar(self, especie: str, numero: int) -> str | None:
        linha = self.conexao.execute(
            "SELECT id FROM atos WHERE especie=? AND numero=? ORDER BY ano LIMIT 1",
            (especie, numero)).fetchone()
        return linha["id"] if linha else None

    def _reindexar_atos(self) -> None:
        # O índice de ementas usa conteúdo externo sem gatilhos: a lista inteira
        # cabe numa reconstrução, e assim não há chance de ficar fora de sincronia.
        self.conexao.execute("INSERT INTO atos_fts(atos_fts) VALUES('rebuild')")
        self.conexao.commit()

    def gravar_paginas(self, ato_id: str, paginas: list[str]) -> int:
        self.conexao.execute("DELETE FROM paginas WHERE ato_id=?", (ato_id,))
        total = 0
        for i, texto in enumerate(paginas, start=1):
            if not texto.strip():
                continue
            self.conexao.execute(
                "INSERT INTO paginas (ato_id, pagina, texto) VALUES (?,?,?)",
                (ato_id, i, texto))
            total += 1
        self.conexao.execute(
            "UPDATE atos SET paginas_total=?, caracteres=? WHERE id=?",
            (total, sum(len(p) for p in paginas), ato_id))
        self.conexao.commit()
        return total

    # -- leitura ----------------------------------------------------------

    def sem_texto(self) -> list[dict[str, Any]]:
        """Atos que ainda não têm texto e podem tê-lo.

        Quem já falhou por ausência de arquivo na fonte não volta à fila
        sozinho: repetir a mesma requisição sabendo que ela falha é insistir
        contra servidor público sem nada a ganhar.
        """
        return [dict(l) for l in self.conexao.execute(
            "SELECT id, especie, numero, ano, arquivo_id FROM atos "
            "WHERE especie <> 'sumula' AND paginas_total = 0 "
            "  AND (falha IS NULL OR falha = '') "
            "ORDER BY especie, ano DESC, numero DESC")]

    def marcar_sem_arquivo(self, ato_id: str, motivo: str) -> None:
        self.conexao.execute("UPDATE atos SET falha=? WHERE id=?", (motivo, ato_id))
        self.conexao.commit()

    def estatisticas(self) -> dict[str, Any]:
        por_especie = [dict(l) for l in self.conexao.execute(
            "SELECT especie, COUNT(*) atos,"
            " SUM(CASE WHEN revogado_por_numero IS NOT NULL"
            "          OR revogado_em IS NOT NULL THEN 1 ELSE 0 END) revogados,"
            " SUM(CASE WHEN paginas_total > 0 THEN 1 ELSE 0 END) com_texto,"
            " MIN(ano) de, MAX(ano) ate"
            " FROM atos GROUP BY especie ORDER BY atos DESC")]
        p, c = self.conexao.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(texto)),0) FROM paginas").fetchone()
        return {
            "por_especie": por_especie,
            "atos": self.conexao.execute("SELECT COUNT(*) FROM atos").fetchone()[0],
            "paginas": p,
            "caracteres": c,
            "revogacoes": self.conexao.execute(
                "SELECT COUNT(*) FROM revogacoes").fetchone()[0],
        }
