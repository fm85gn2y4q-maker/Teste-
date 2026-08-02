# -*- coding: utf-8 -*-
"""Monta a tabela de fichas sobre o acervo INTEIRO (49.139), nao so o recorte.

Substitui o `indexar.py`, que so conhecia os 14.420 de contratacoes. Aqui:

  - toda ficha entra, com procurador, orgao, processo, ementa e assuntos;
  - o eixo tematico e calculado para todas, mas quem NAO estava no recorte
    original fica marcado com `no_recorte = 0`. O corte que tornava a base
    precisa continua disponivel como filtro, em vez de se perder na diluicao;
  - o indice de ficha nao guarda o inteiro teor: esse vive em `paginas_fts`,
    e duplica-lo custava 500 MB sem servir a nenhuma consulta.

Nao le PDF. As paginas, a conclusao e as citacoes vem na passada seguinte.
"""
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classificar import avalia  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
TOTAL = os.path.join(AQUI, "catalogo_pgerj_total.jsonl")
RECORTE = os.path.join(AQUI, "selecionados.jsonl")
DB = os.environ.get(
    "PARECERES_BANCO",
    r"C:\Users\Matheus Menegatti\Documents\PGE-RJ_Pareceres_Contratacoes\pge_rj_pareceres.db")

UP = "https://documentacao.pge.rj.gov.br/scripts/bnweb/bnmapi.exe?router=upload/%s"

DDL = """
PRAGMA journal_mode=WAL;
DROP TABLE IF EXISTS documentos;
CREATE TABLE documentos (
  codigo INTEGER PRIMARY KEY, tipo TEXT, titulo TEXT, numero TEXT, data TEXT, ano INTEGER,
  procuradores TEXT, setores TEXT, orgao TEXT, processo TEXT, ementa TEXT, assuntos TEXT,
  eixos TEXT, criterio TEXT, no_recorte INTEGER DEFAULT 0, precedentes_ficha TEXT,
  arquivo TEXT, paginas INTEGER DEFAULT 0, caracteres INTEGER DEFAULT 0,
  tem_texto INTEGER DEFAULT 0, conclusao TEXT DEFAULT '', conclusao_tipo TEXT DEFAULT '',
  conclusao_alheia INTEGER DEFAULT 0, fecho TEXT DEFAULT '', regime TEXT,
  alerta_vigencia TEXT, url_pdf TEXT, url_ficha TEXT);
CREATE INDEX ix_doc_ano ON documentos(ano);
CREATE INDEX ix_doc_recorte ON documentos(no_recorte);
DROP TABLE IF EXISTS busca;
CREATE VIRTUAL TABLE busca USING fts5(
  codigo UNINDEXED, titulo, ementa, assuntos,
  tokenize="unicode61 remove_diacritics 2");
"""
FICHA = "https://documentacao.pge.rj.gov.br/bnportal/pt-BR/detalhes/%s"


def main():
    recorte = set()
    with open(RECORTE, encoding="utf-8") as f:
        for linha in f:
            recorte.add(json.loads(linha)["codigo"])
    print("recorte tematico original: %d documentos" % len(recorte), flush=True)

    con = sqlite3.connect(DB)
    con.executescript(DDL)
    t0, n, com_eixo = time.time(), 0, 0
    linhas, fts = [], []
    with open(TOTAL, encoding="utf-8") as f:
        for linha in f:
            r = json.loads(linha)
            cod = r["codigo"]
            ax = [a for a in (r.get("anexos") or []) if not a.get("fonte")]
            procs = [m.get("nome", "") for m in (r.get("membros") or [])
                     if m.get("tipo_relacao") == 9]
            setores = sorted({m.get("nome_setor", "") for m in (r.get("membros") or [])
                              if m.get("nome_setor")})
            orgaos = [m.get("nome", "") for m in (r.get("membros") or [])
                      if m.get("tipo_relacao") == 10]
            assuntos = " | ".join(a.get("nome", "") for a in (r.get("assuntos") or []))
            _, eixos, criterio = avalia(r)
            if eixos:
                com_eixo += 1
            linhas.append((
                cod, r.get("tipo_nome"), r.get("titulo"), r.get("numero"), r.get("datadoc"),
                r.get("anodoc"), " | ".join(procs), " | ".join(setores), " | ".join(orgaos),
                r.get("processo"), r.get("ementa"), assuntos, "; ".join(eixos), criterio,
                1 if cod in recorte else 0,
                (r.get("precedentes") or "").replace("\n", " "),
                UP % ax[0]["cod_anexo"] if ax else "", FICHA % cod))
            fts.append((cod, r.get("titulo"), r.get("ementa"), assuntos))
            n += 1
            if len(linhas) >= 5000:
                gravar(con, linhas, fts)
                linhas, fts = [], []
                print("  %d..." % n, flush=True)
    gravar(con, linhas, fts)
    con.execute("INSERT INTO busca(busca) VALUES('optimize')")
    con.commit()
    print("\nfichas: %d | com eixo tematico: %d | no recorte original: %d | %.0f s"
          % (n, com_eixo, len(recorte), time.time() - t0), flush=True)
    con.close()


def gravar(con, linhas, fts):
    con.executemany(
        """INSERT INTO documentos
           (codigo,tipo,titulo,numero,data,ano,procuradores,setores,orgao,processo,
            ementa,assuntos,eixos,criterio,no_recorte,precedentes_ficha,url_pdf,url_ficha)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", linhas)
    con.executemany("INSERT INTO busca VALUES (?,?,?,?)", fts)
    con.commit()


if __name__ == "__main__":
    main()
