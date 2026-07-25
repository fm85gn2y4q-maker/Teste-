"""Persistência incremental em SQLite, com exportação para JSONL/CSV.

A coleta é retomável: cada documento gravado e cada URL visitada ficam
registrados, de modo que uma reexecução após interrupção não refaz o trabalho
nem duplica registros.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from .modelos import Documento, TipoDocumento

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS documentos (
    id                TEXT PRIMARY KEY,
    tipo              TEXT NOT NULL,
    numero            TEXT,
    ano               INTEGER,
    processo          TEXT,
    relator           TEXT,
    orgao_julgador    TEXT,
    data_sessao       TEXT,
    data_publicacao   TEXT,
    ementa            TEXT,
    inteiro_teor      TEXT,
    assuntos          TEXT,
    url               TEXT,
    url_pdf           TEXT,
    fonte             TEXT,
    coletado_em       TEXT NOT NULL,
    bruto             TEXT
);

CREATE INDEX IF NOT EXISTS ix_documentos_tipo ON documentos(tipo);
CREATE INDEX IF NOT EXISTS ix_documentos_ano ON documentos(ano);
CREATE INDEX IF NOT EXISTS ix_documentos_relator ON documentos(relator);
CREATE INDEX IF NOT EXISTS ix_documentos_processo ON documentos(processo);

-- Marca as URLs já processadas para permitir retomada.
CREATE TABLE IF NOT EXISTS visitados (
    url        TEXT PRIMARY KEY,
    status     TEXT NOT NULL,
    detalhe    TEXT,
    visto_em   TEXT NOT NULL
);

-- Busca textual sobre ementa e inteiro teor.
CREATE VIRTUAL TABLE IF NOT EXISTS documentos_fts
USING fts5(id UNINDEXED, ementa, inteiro_teor, tokenize='unicode61 remove_diacritics 2');
"""

_COLUNAS = (
    "id", "tipo", "numero", "ano", "processo", "relator", "orgao_julgador",
    "data_sessao", "data_publicacao", "ementa", "inteiro_teor", "assuntos",
    "url", "url_pdf", "fonte", "coletado_em", "bruto",
)


class Armazenamento:
    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.conexao = sqlite3.connect(self.caminho)
        self.conexao.row_factory = sqlite3.Row
        self.conexao.execute("PRAGMA journal_mode=WAL")
        self.conexao.execute("PRAGMA synchronous=NORMAL")
        self.conexao.executescript(_ESQUEMA)
        self.conexao.commit()

    def __enter__(self) -> "Armazenamento":
        return self

    def __exit__(self, *_) -> None:
        self.fechar()

    def fechar(self) -> None:
        self.conexao.commit()
        self.conexao.close()

    # -- escrita ----------------------------------------------------------

    def gravar(self, documento: Documento) -> bool:
        """Insere ou completa um documento. Retorna True se era inédito.

        Quando o documento já existe, os campos vazios do registro antigo são
        preenchidos com os novos valores, sem descartar o que já havia (o mesmo
        acórdão pode chegar primeiro pela listagem e depois pelo detalhe).
        """
        documento.coletado_em = documento.coletado_em or datetime.now(timezone.utc).isoformat()
        existente = self.obter(documento.id)
        if existente is not None:
            documento = existente.mesclar(documento)
            inedito = False
        else:
            inedito = True

        dados = documento.para_dict()
        dados["assuntos"] = json.dumps(dados["assuntos"], ensure_ascii=False)
        dados["bruto"] = json.dumps(dados["bruto"], ensure_ascii=False, default=str)

        marcadores = ", ".join(f":{c}" for c in _COLUNAS)
        self.conexao.execute(
            f"INSERT OR REPLACE INTO documentos ({', '.join(_COLUNAS)}) VALUES ({marcadores})",
            {c: dados.get(c) for c in _COLUNAS},
        )
        self.conexao.execute("DELETE FROM documentos_fts WHERE id = ?", (documento.id,))
        self.conexao.execute(
            "INSERT INTO documentos_fts (id, ementa, inteiro_teor) VALUES (?, ?, ?)",
            (documento.id, documento.ementa or "", documento.inteiro_teor or ""),
        )
        self.conexao.commit()
        return inedito

    def gravar_muitos(self, documentos: Iterable[Documento]) -> tuple[int, int]:
        novos = atualizados = 0
        for documento in documentos:
            if self.gravar(documento):
                novos += 1
            else:
                atualizados += 1
        return novos, atualizados

    def marcar_visitado(self, url: str, status: str, detalhe: str | None = None) -> None:
        self.conexao.execute(
            "INSERT OR REPLACE INTO visitados (url, status, detalhe, visto_em) "
            "VALUES (?, ?, ?, ?)",
            (url, status, detalhe, datetime.now(timezone.utc).isoformat()),
        )
        self.conexao.commit()

    def ja_visitado(self, url: str) -> bool:
        cursor = self.conexao.execute(
            "SELECT 1 FROM visitados WHERE url = ? AND status = 'ok'", (url,)
        )
        return cursor.fetchone() is not None

    # -- leitura ----------------------------------------------------------

    def obter(self, id_documento: str) -> Documento | None:
        linha = self.conexao.execute(
            "SELECT * FROM documentos WHERE id = ?", (id_documento,)
        ).fetchone()
        return _linha_para_documento(linha) if linha else None

    def listar(
        self,
        *,
        tipo: TipoDocumento | None = None,
        ano: int | None = None,
        limite: int | None = None,
    ) -> Iterator[Documento]:
        clausulas, parametros = [], []
        if tipo:
            clausulas.append("tipo = ?")
            parametros.append(tipo.value)
        if ano:
            clausulas.append("ano = ?")
            parametros.append(ano)

        sql = "SELECT * FROM documentos"
        if clausulas:
            sql += " WHERE " + " AND ".join(clausulas)
        sql += " ORDER BY ano DESC, numero DESC"
        if limite:
            sql += f" LIMIT {int(limite)}"

        with closing(self.conexao.execute(sql, parametros)) as cursor:
            for linha in cursor:
                yield _linha_para_documento(linha)

    def buscar(self, termo: str, limite: int = 50) -> list[Documento]:
        """Busca textual com o índice FTS5."""
        linhas = self.conexao.execute(
            "SELECT d.* FROM documentos_fts f JOIN documentos d ON d.id = f.id "
            "WHERE documentos_fts MATCH ? ORDER BY rank LIMIT ?",
            (termo, limite),
        ).fetchall()
        return [_linha_para_documento(linha) for linha in linhas]

    def estatisticas(self) -> dict[str, int]:
        total = self.conexao.execute("SELECT COUNT(*) FROM documentos").fetchone()[0]
        por_tipo = {
            linha["tipo"]: linha["n"]
            for linha in self.conexao.execute(
                "SELECT tipo, COUNT(*) AS n FROM documentos GROUP BY tipo ORDER BY n DESC"
            )
        }
        return {"total": total, **por_tipo}


def _linha_para_documento(linha: sqlite3.Row) -> Documento:
    def data(valor: str | None) -> date | None:
        return date.fromisoformat(valor) if valor else None

    return Documento(
        tipo=TipoDocumento(linha["tipo"]),
        numero=linha["numero"],
        ano=linha["ano"],
        processo=linha["processo"],
        relator=linha["relator"],
        orgao_julgador=linha["orgao_julgador"],
        data_sessao=data(linha["data_sessao"]),
        data_publicacao=data(linha["data_publicacao"]),
        ementa=linha["ementa"],
        inteiro_teor=linha["inteiro_teor"],
        assuntos=json.loads(linha["assuntos"] or "[]"),
        url=linha["url"],
        url_pdf=linha["url_pdf"],
        fonte=linha["fonte"],
        coletado_em=linha["coletado_em"],
        bruto=json.loads(linha["bruto"] or "{}"),
    )


# ---------------------------------------------------------------------------
# Exportação
# ---------------------------------------------------------------------------


def exportar_jsonl(documentos: Iterable[Documento], destino: str | Path) -> int:
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with caminho.open("w", encoding="utf-8") as arquivo:
        for documento in documentos:
            arquivo.write(json.dumps(documento.para_dict(), ensure_ascii=False) + "\n")
            total += 1
    return total


_CAMPOS_CSV = (
    "id", "tipo", "numero", "ano", "processo", "relator", "orgao_julgador",
    "data_sessao", "data_publicacao", "ementa", "assuntos", "url", "url_pdf",
)


def exportar_csv(documentos: Iterable[Documento], destino: str | Path) -> int:
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=_CAMPOS_CSV, extrasaction="ignore")
        escritor.writeheader()
        for documento in documentos:
            linha = documento.para_dict()
            linha["assuntos"] = "; ".join(linha["assuntos"])
            escritor.writerow(linha)
            total += 1
    return total
