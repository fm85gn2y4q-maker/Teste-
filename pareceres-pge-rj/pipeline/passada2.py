# -*- coding: utf-8 -*-
"""Segunda passada sobre o acervo da PGE-RJ, lendo os PDFs uma unica vez:

  1. indexa POR PAGINA (para citar "p. 27", nao so "consta do parecer")
  2. extrai a conclusao com um conjunto maior de formulas, classificada por
     tipo, e guarda tambem o fecho literal do documento
  3. reextrai as citacoes com o regex corrigido (numero truncado, ruido de
     OCR, variantes duplicadas de sumula/acordao/precedente)

Ler do PDF e muito mais rapido que reler o texto de dentro do FTS.
"""
import collections
import glob
import os
import re
import sqlite3
import time

import fitz

from conclusao import conclusao_de
from corrigir import extrai

BASE = r"C:\Users\Matheus Menegatti\Documents\PGE-RJ_Pareceres_Contratacoes"
DB = os.path.join(BASE, "pge_rj_pareceres.db")

DDL = """
CREATE TABLE IF NOT EXISTS paginas (
  codigo INTEGER, pagina INTEGER, caracteres INTEGER, PRIMARY KEY (codigo, pagina));
CREATE VIRTUAL TABLE IF NOT EXISTS paginas_fts USING fts5(
  codigo UNINDEXED, pagina UNINDEXED, texto,
  tokenize="unicode61 remove_diacritics 2");
"""


def main():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript(DDL)
    for col in ("conclusao_tipo", "fecho"):
        try:
            con.execute("ALTER TABLE documentos ADD COLUMN %s TEXT" % col)
        except sqlite3.OperationalError:
            pass
    con.execute("DELETE FROM paginas")
    con.execute("DELETE FROM paginas_fts")
    con.execute("DROP TABLE IF EXISTS citacoes")
    con.execute("""CREATE TABLE citacoes (codigo INTEGER, especie TEXT, referencia TEXT,
                   qualificador TEXT, ocorrencias INTEGER)""")
    con.commit()

    porcod = collections.defaultdict(list)
    for f in glob.glob(os.path.join(BASE, "PDFs", "**", "*.pdf"), recursive=True):
        m = re.match(r"(\d+)_", os.path.basename(f))
        if m:
            porcod[int(m.group(1))].append(f)
    codigos = sorted(porcod, reverse=True)
    print("documentos com PDF: %d (arquivos: %d)"
          % (len(codigos), sum(len(v) for v in porcod.values())), flush=True)

    t0, tipos, npag = time.time(), collections.Counter(), 0
    for i, cod in enumerate(codigos, 1):
        paginas = []
        for f in sorted(porcod[cod]):
            try:
                d = fitz.open(f)
            except Exception as e:
                print("ERRO %s: %s" % (f, e), flush=True)
                continue
            for p in range(d.page_count):
                paginas.append(d[p].get_text())
            d.close()
        txt = "\n".join(paginas)

        # Colunas nomeadas: a tabela ganha `secao` e `transcricao` na passada
        # seguinte, e a insercao por posicao quebrava na reexecucao.
        con.executemany("INSERT OR REPLACE INTO paginas (codigo, pagina, caracteres) VALUES (?,?,?)",
                        [(cod, n, len(t.strip())) for n, t in enumerate(paginas, 1)])
        con.executemany("INSERT INTO paginas_fts (codigo, pagina, texto) VALUES (?,?,?)",
                        [(cod, n, t) for n, t in enumerate(paginas, 1)])
        npag += len(paginas)

        # conclusao_de devolve TRES valores desde que passou a rejeitar
        # peca de terceiro reproduzida no fim do parecer.
        conc, tipo, alheia = conclusao_de(txt)
        tipos[tipo or "(nenhuma)"] += 1
        con.execute("""UPDATE documentos SET conclusao=?, conclusao_tipo=?,
                       conclusao_alheia=?, fecho=?, paginas=?, caracteres=?, tem_texto=?
                       WHERE codigo=?""",
                    (conc, tipo, 1 if alheia else 0,
                     re.sub(r"\s+", " ", txt[-1500:]).strip(),
                     len(paginas), len(txt.strip()),
                     # 200 caracteres e o piso: abaixo disso e
                     # digitalizacao sem camada de texto
                     1 if len(txt.strip()) > 200 else 0, cod))

        if len(txt) > 100:
            cits = [(cod, e, r, q, o) for e, r, q, o in extrai(txt)]
            if cits:
                con.executemany("INSERT INTO citacoes VALUES (?,?,?,?,?)", cits)

        if i % 500 == 0:
            con.commit()
            print("  %d/%d  %.0f/min  paginas=%d"
                  % (i, len(codigos), i / max(time.time() - t0, 1) * 60, npag), flush=True)
    con.commit()

    # --- consolida normas citadas sem ano -----------------------------------
    modal = {}
    for tn, ano, s in con.execute("""SELECT substr(referencia,1,instr(referencia,'/')-1),
             substr(referencia,instr(referencia,'/')+1), SUM(ocorrencias) FROM citacoes
             WHERE especie='norma' AND instr(referencia,'/')>0 GROUP BY 1,2"""):
        if tn not in modal or s > modal[tn][1]:
            modal[tn] = (ano, s)
    corr = 0
    for (ref,) in con.execute("""SELECT DISTINCT referencia FROM citacoes WHERE especie='norma'
             AND instr(referencia,'/')=0 AND referencia NOT LIKE 'Constituicao%'""").fetchall():
        if ref in modal:
            con.execute("UPDATE citacoes SET referencia=? WHERE especie='norma' AND referencia=?",
                        (ref + "/" + modal[ref][0], ref))
            corr += 1
    con.execute("""DELETE FROM citacoes WHERE rowid NOT IN
                   (SELECT MIN(rowid) FROM citacoes GROUP BY codigo,especie,referencia,qualificador)""")
    for ddl in ("CREATE INDEX IF NOT EXISTS ix_cit_ref ON citacoes(referencia)",
                "CREATE INDEX IF NOT EXISTS ix_cit_cod ON citacoes(codigo)",
                "CREATE INDEX IF NOT EXISTS ix_cit_esp ON citacoes(especie)",
                "CREATE INDEX IF NOT EXISTS ix_pag_cod ON paginas(codigo)"):
        con.execute(ddl)
    con.commit()
    con.execute("INSERT INTO paginas_fts(paginas_fts) VALUES('optimize')")
    con.commit()

    print("\nFIM em %.0f min | paginas indexadas: %d | normas sem ano consolidadas: %d"
          % ((time.time() - t0) / 60, npag, corr), flush=True)
    print("conclusao por tipo:", tipos.most_common(), flush=True)
    con.close()


if __name__ == "__main__":
    main()
