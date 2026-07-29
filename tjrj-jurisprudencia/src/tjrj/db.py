"""Esquema do acervo (SQLite + FTS5) e acesso.

Decisões que valem explicação:

* **Uma linha por acórdão, muitas por página de inteiro teor.** A busca em
  ementa e a busca em inteiro teor respondem perguntas diferentes e precisam
  de índices separados — e a citação "consta do voto, à p. 27" só é possível
  se a página for uma entidade de primeira classe.
* **Julgadores são tabela, não string.** "Des. João da Silva", "JOÃO DA
  SILVA" e "Joao Silva" são a mesma pessoa; sem normalização não existe
  "entendimento do relator".
* **Partes ficam isoladas em `parte`, com `sigilo`.** É a tabela que você
  pode não exportar, não publicar e não indexar sem decidir antes. Ver
  docs/JURIDICO.md.
* **`coleta` e `lacuna` são parte do acervo, não log.** Sem elas você não
  consegue responder "isso não existe" — só "não achei", que é outra coisa.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

ESQUEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS acordao (
    id                TEXT PRIMARY KEY,     -- hash estável (ver models.id_acordao)
    numero_cnj        TEXT,
    numero_origem     TEXT,
    sistema           TEXT NOT NULL,        -- ejuris | eproc
    grau              TEXT,                 -- 1 | 2 | turma_recursal
    orgao_julgador    TEXT,
    orgao_id          INTEGER REFERENCES orgao(id),
    classe            TEXT,
    tipo_decisao      TEXT,                 -- acordao | monocratica
    data_julgamento   TEXT,                 -- ISO-8601
    data_publicacao   TEXT,
    ementa            TEXT,
    dispositivo       TEXT,
    segredo_justica   INTEGER NOT NULL DEFAULT 0,
    url_fonte         TEXT,
    hash_ementa       TEXT,
    hash_teor         TEXT,
    paginas           INTEGER NOT NULL DEFAULT 0,
    coletado_em       TEXT NOT NULL,
    atualizado_em     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_acordao_cnj    ON acordao(numero_cnj);
CREATE INDEX IF NOT EXISTS ix_acordao_data   ON acordao(data_julgamento);
CREATE INDEX IF NOT EXISTS ix_acordao_orgao  ON acordao(orgao_id, data_julgamento);
CREATE INDEX IF NOT EXISTS ix_acordao_hash   ON acordao(hash_teor);

CREATE TABLE IF NOT EXISTS orgao (
    id        INTEGER PRIMARY KEY,
    nome      TEXT NOT NULL,
    nome_norm TEXT NOT NULL UNIQUE,
    tipo      TEXT,                          -- camara_civel | camara_criminal | grupo | orgao_especial | ...
    grau      TEXT
);

CREATE TABLE IF NOT EXISTS julgador (
    id        INTEGER PRIMARY KEY,
    nome      TEXT NOT NULL,                 -- forma canônica escolhida
    nome_norm TEXT NOT NULL UNIQUE,          -- chave de deduplicação
    cargo     TEXT                           -- desembargador | juiz_convocado | ministro | ...
);

CREATE TABLE IF NOT EXISTS julgador_alias (
    alias_norm  TEXT PRIMARY KEY,
    julgador_id INTEGER NOT NULL REFERENCES julgador(id),
    origem      TEXT                          -- onde a variante foi vista
);

-- Quem participou do julgamento e em que qualidade. É esta tabela que
-- responde "quem mais julgou além do relator".
CREATE TABLE IF NOT EXISTS participacao (
    acordao_id  TEXT NOT NULL REFERENCES acordao(id) ON DELETE CASCADE,
    julgador_id INTEGER NOT NULL REFERENCES julgador(id),
    papel       TEXT NOT NULL,               -- relator | relator_designado | revisor | vogal | presidente | procurador
    vencido     INTEGER NOT NULL DEFAULT 0,
    ordem       INTEGER,
    confianca   REAL NOT NULL DEFAULT 1.0,   -- < 1 quando extraído por heurística
    fonte       TEXT,                        -- metadado | cabecalho | rodape | llm
    PRIMARY KEY (acordao_id, julgador_id, papel)
);
CREATE INDEX IF NOT EXISTS ix_part_julgador ON participacao(julgador_id, papel);

CREATE TABLE IF NOT EXISTS parte (
    acordao_id TEXT NOT NULL REFERENCES acordao(id) ON DELETE CASCADE,
    nome       TEXT NOT NULL,
    polo       TEXT,                         -- ativo | passivo | terceiro | mp
    tipo       TEXT,                         -- pessoa_fisica | pessoa_juridica | ente_publico
    advogados  TEXT,                         -- json
    sigilo     INTEGER NOT NULL DEFAULT 0,
    fonte      TEXT
);
CREATE INDEX IF NOT EXISTS ix_parte_acordao ON parte(acordao_id);

CREATE TABLE IF NOT EXISTS assunto (
    acordao_id TEXT NOT NULL REFERENCES acordao(id) ON DELETE CASCADE,
    codigo     TEXT,                         -- tabela unificada CNJ
    descricao  TEXT
);

CREATE TABLE IF NOT EXISTS documento (
    acordao_id TEXT NOT NULL REFERENCES acordao(id) ON DELETE CASCADE,
    pagina     INTEGER NOT NULL,
    texto      TEXT NOT NULL,
    origem     TEXT,                          -- pdf | html | rtf | ocr
    PRIMARY KEY (acordao_id, pagina)
);

-- Rastro de coleta: o que foi pedido, quando, e o que voltou.
CREATE TABLE IF NOT EXISTS coleta (
    id          INTEGER PRIMARY KEY,
    fonte       TEXT NOT NULL,
    fatia       TEXT NOT NULL,
    inicio      TEXT NOT NULL,
    fim         TEXT,
    encontrados INTEGER,
    novos       INTEGER,
    status      TEXT NOT NULL,               -- ok | erro | parcial
    detalhe     TEXT,
    UNIQUE (fonte, fatia)
);

-- Aquilo que o tribunal não deixou ver por inteiro. Alimenta o relatório
-- de cobertura exposto no MCP.
CREATE TABLE IF NOT EXISTS lacuna (
    id              INTEGER PRIMARY KEY,
    fonte           TEXT NOT NULL,
    fatia           TEXT NOT NULL,
    total_declarado INTEGER,
    teto            INTEGER,
    motivo          TEXT,
    registrado_em   TEXT NOT NULL
);

-- Os dois índices FTS são tabelas comuns (não `content=`) com uma tabela de
-- mapeamento ao lado. Duas razões: FTS5 externo não aceita DELETE por rowid,
-- o que tornaria a reindexação de um acórdão um remendo; e o rowid implícito
-- de `acordao` pode mudar num VACUUM, o que quebraria o vínculo em silêncio.
-- O rowid do mapa é INTEGER PRIMARY KEY, logo estável.
CREATE VIRTUAL TABLE IF NOT EXISTS ementa_fts USING fts5(
    ementa, dispositivo,
    tokenize="unicode61 remove_diacritics 2"
);
CREATE TABLE IF NOT EXISTS ementa_map (
    rowid      INTEGER PRIMARY KEY,
    acordao_id TEXT NOT NULL UNIQUE
);

CREATE VIRTUAL TABLE IF NOT EXISTS teor_fts USING fts5(
    texto,
    tokenize="unicode61 remove_diacritics 2"
);
-- A chave (acordao_id, pagina) fica em teor_map para que a busca em inteiro
-- teor devolva a página exata — é o que sustenta a citação "consta do voto,
-- à p. 27".
CREATE TABLE IF NOT EXISTS teor_map (
    rowid      INTEGER PRIMARY KEY,
    acordao_id TEXT NOT NULL,
    pagina     INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_teor_map ON teor_map(acordao_id, pagina);
"""


def conectar(caminho: Path | str) -> sqlite3.Connection:
    con = sqlite3.connect(str(caminho), timeout=60)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def migrar(con: sqlite3.Connection) -> None:
    con.executescript(ESQUEMA)
    con.commit()


@contextmanager
def transacao(con: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise


def indexar_ementa(con: sqlite3.Connection, acordao_id: str) -> None:
    linha = con.execute(
        "SELECT ementa, dispositivo FROM acordao WHERE id = ?", (acordao_id,)
    ).fetchone()
    if linha is None:
        return

    mapa = con.execute(
        "SELECT rowid FROM ementa_map WHERE acordao_id = ?", (acordao_id,)
    ).fetchone()
    if mapa is None:
        rid = con.execute(
            "INSERT INTO ementa_map(acordao_id) VALUES (?)", (acordao_id,)
        ).lastrowid
    else:
        rid = mapa["rowid"]
        con.execute("DELETE FROM ementa_fts WHERE rowid = ?", (rid,))

    con.execute(
        "INSERT INTO ementa_fts(rowid, ementa, dispositivo) VALUES (?, ?, ?)",
        (rid, linha["ementa"] or "", linha["dispositivo"] or ""),
    )


def indexar_paginas(con: sqlite3.Connection, acordao_id: str) -> None:
    antigos = [
        r["rowid"] for r in con.execute("SELECT rowid FROM teor_map WHERE acordao_id = ?", (acordao_id,))
    ]
    for rid in antigos:
        con.execute("DELETE FROM teor_fts WHERE rowid = ?", (rid,))
    con.execute("DELETE FROM teor_map WHERE acordao_id = ?", (acordao_id,))

    for r in con.execute(
        "SELECT pagina, texto FROM documento WHERE acordao_id = ? ORDER BY pagina", (acordao_id,)
    ):
        cur = con.execute(
            "INSERT INTO teor_map(acordao_id, pagina) VALUES (?, ?)", (acordao_id, r["pagina"])
        )
        con.execute("INSERT INTO teor_fts(rowid, texto) VALUES (?, ?)", (cur.lastrowid, r["texto"]))


def registrar_lacuna(con: sqlite3.Connection, fonte: str, lacuna: Any, quando: str) -> None:
    con.execute(
        "INSERT INTO lacuna(fonte, fatia, total_declarado, teto, motivo, registrado_em)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (fonte, str(lacuna.fatia), lacuna.total_declarado, lacuna.teto, lacuna.motivo, quando),
    )


def dump_json(valor: Any) -> str:
    return json.dumps(valor, ensure_ascii=False, separators=(",", ":"))
