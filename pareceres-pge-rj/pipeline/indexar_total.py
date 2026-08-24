# -*- coding: utf-8 -*-
"""Monta a tabela de fichas sobre o acervo INTEIRO, nao so o recorte.

Substitui o `indexar.py`, que so conhecia os 14.420 de contratacoes. Aqui:

  - toda ficha entra, com procurador, orgao, processo, ementa e assuntos;
  - o eixo tematico e calculado para todas, mas quem NAO estava no recorte
    original fica marcado com `no_recorte = 0`. O corte que tornava a base
    precisa continua disponivel como filtro, em vez de se perder na diluicao;
  - o indice de ficha nao guarda o inteiro teor: esse vive em `paginas_fts`,
    e duplica-lo custava 500 MB sem servir a nenhuma consulta.

Nao le PDF. As paginas, a conclusao e as citacoes vem na passada seguinte.

    python indexar_total.py           # refaz tudo, do zero
    python indexar_total.py --novos   # so os codigos de novos.txt

No modo `--novos` as tabelas nao sao derrubadas e codigo ja presente e
IGNORADO, nao regravado: a linha de `documentos` carrega colunas preenchidas
pelas passadas seguintes (conclusao, regime, paginas), e reinseri-la aqui as
zeraria sem que nada mais tornasse a preenche-las.
"""
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from caminhos import DB  # noqa: E402
from classificar import avalia  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
TOTAL = os.path.join(AQUI, "catalogo_pgerj_total.jsonl")
RECORTE = os.path.join(AQUI, "selecionados.jsonl")
NOVOS = os.path.join(AQUI, "novos.txt")

UP = "https://documentacao.pge.rj.gov.br/scripts/bnweb/bnmapi.exe?router=upload/%s"
FICHA = "https://documentacao.pge.rj.gov.br/bnportal/pt-BR/detalhes/%s"

ZERAR = """
DROP TABLE IF EXISTS documentos;
DROP TABLE IF EXISTS busca;
"""
CRIAR = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS documentos (
  codigo INTEGER PRIMARY KEY, tipo TEXT, titulo TEXT, numero TEXT, data TEXT, ano INTEGER,
  procuradores TEXT, setores TEXT, orgao TEXT, processo TEXT, ementa TEXT, assuntos TEXT,
  eixos TEXT, criterio TEXT, no_recorte INTEGER DEFAULT 0, precedentes_ficha TEXT,
  arquivo TEXT, paginas INTEGER DEFAULT 0, caracteres INTEGER DEFAULT 0,
  tem_texto INTEGER DEFAULT 0, conclusao TEXT DEFAULT '', conclusao_tipo TEXT DEFAULT '',
  conclusao_alheia INTEGER DEFAULT 0, fecho TEXT DEFAULT '', regime TEXT,
  alerta_vigencia TEXT, url_pdf TEXT, url_ficha TEXT);
CREATE INDEX IF NOT EXISTS ix_doc_ano ON documentos(ano);
CREATE INDEX IF NOT EXISTS ix_doc_recorte ON documentos(no_recorte);
CREATE VIRTUAL TABLE IF NOT EXISTS busca USING fts5(
  codigo UNINDEXED, titulo, ementa, assuntos,
  tokenize="unicode61 remove_diacritics 2");
"""


def ficha(r, recorte):
    """Um registro do catalogo vira (linha de `documentos`, linha de `busca`)."""
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
    linha = (
        cod, r.get("tipo_nome"), r.get("titulo"), r.get("numero"), r.get("datadoc"),
        r.get("anodoc"), " | ".join(procs), " | ".join(setores), " | ".join(orgaos),
        r.get("processo"), r.get("ementa"), assuntos, "; ".join(eixos), criterio,
        1 if cod in recorte else 0,
        (r.get("precedentes") or "").replace("\n", " "),
        UP % ax[0]["cod_anexo"] if ax else "", FICHA % cod)
    return linha, (cod, r.get("titulo"), r.get("ementa"), assuntos), bool(eixos)


def ler_novos():
    if not os.path.exists(NOVOS):
        print("sem %s: nao ha o que incrementar." % NOVOS, file=sys.stderr, flush=True)
        raise SystemExit(1)
    with open(NOVOS, encoding="utf-8") as f:
        return {int(l) for l in f if l.strip()}


def gravar(con, linhas, fts):
    con.executemany(
        """INSERT INTO documentos
           (codigo,tipo,titulo,numero,data,ano,procuradores,setores,orgao,processo,
            ementa,assuntos,eixos,criterio,no_recorte,precedentes_ficha,url_pdf,url_ficha)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", linhas)
    con.executemany("INSERT INTO busca VALUES (?,?,?,?)", fts)
    con.commit()


def main():
    alvo = ler_novos() if "--novos" in sys.argv else None

    recorte = set()
    with open(RECORTE, encoding="utf-8") as f:
        for linha in f:
            recorte.add(json.loads(linha)["codigo"])
    print("recorte tematico original: %d documentos" % len(recorte), flush=True)

    con = sqlite3.connect(DB)
    if alvo is None:
        con.executescript(ZERAR)
    con.executescript(CRIAR)

    ja = set()
    if alvo is not None:
        ja = {c for (c,) in con.execute("SELECT codigo FROM documentos")}
        print("modo incremental: %d codigos novos, %d fichas ja no banco"
              % (len(alvo), len(ja)), flush=True)

    t0, n, com_eixo, pulados = time.time(), 0, 0, 0
    linhas, fts = [], []
    with open(TOTAL, encoding="utf-8") as f:
        for linha in f:
            r = json.loads(linha)
            if alvo is not None:
                if r["codigo"] not in alvo:
                    continue
                if r["codigo"] in ja:
                    pulados += 1
                    continue
            doc, indice, tem_eixo = ficha(r, recorte)
            linhas.append(doc)
            fts.append(indice)
            com_eixo += 1 if tem_eixo else 0
            n += 1
            if len(linhas) >= 5000:
                gravar(con, linhas, fts)
                linhas, fts = [], []
                print("  %d..." % n, flush=True)
    gravar(con, linhas, fts)
    con.execute("INSERT INTO busca(busca) VALUES('optimize')")
    con.commit()
    print("\nfichas gravadas: %d | com eixo tematico: %d | ja existentes, puladas: %d | %.0f s"
          % (n, com_eixo, pulados, time.time() - t0), flush=True)
    print("total em documentos: %d"
          % con.execute("SELECT COUNT(*) FROM documentos").fetchone()[0], flush=True)
    con.close()


if __name__ == "__main__":
    main()
