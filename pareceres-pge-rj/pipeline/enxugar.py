# -*- coding: utf-8 -*-
"""Etapa 10: tira do banco o indice de texto por DOCUMENTO.

O inteiro teor estava guardado duas vezes: uma em `paginas_fts`, que e o que
o servidor usa e o que permite citar folha, e outra na coluna `texto` de
`busca`. Essa segunda nunca e consultada -- a busca por ficha filtra as
colunas com `{titulo ementa assuntos}`, e a busca no inteiro teor vai para
`paginas_fts`. Era peso morto.

Sai de 1,3 GB para algo perto da metade, sem perder funcao nenhuma.
"""
import os
import sqlite3
import time

DB = os.environ.get(
    "PARECERES_BANCO",
    r"C:\Users\Matheus Menegatti\Documents\PGE-RJ_Pareceres_Contratacoes\pge_rj_pareceres.db")


def main():
    antes = os.path.getsize(DB)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    t0 = time.time()

    tem_texto = any(c[1] == "texto" for c in con.execute("PRAGMA table_info(busca)"))
    if not tem_texto:
        print("indice ja esta enxuto")
    else:
        print("refazendo o indice de ficha sem a coluna texto...", flush=True)
        con.execute("""CREATE VIRTUAL TABLE busca_nova USING fts5(
                       codigo UNINDEXED, titulo, ementa, assuntos,
                       tokenize="unicode61 remove_diacritics 2")""")
        con.execute("""INSERT INTO busca_nova (codigo, titulo, ementa, assuntos)
                       SELECT codigo, titulo, ementa, assuntos FROM documentos""")
        con.execute("DROP TABLE busca")
        con.execute("ALTER TABLE busca_nova RENAME TO busca")
        con.execute("INSERT INTO busca(busca) VALUES('optimize')")
        con.commit()

    print("compactando...", flush=True)
    con.execute("PRAGMA journal_mode=DELETE")
    con.commit()
    con.execute("VACUUM")
    con.close()

    depois = os.path.getsize(DB)
    print("%.0f MB -> %.0f MB (%.0f%% menor) em %.0f s"
          % (antes / 1e6, depois / 1e6, 100 * (1 - depois / antes), time.time() - t0))


if __name__ == "__main__":
    main()
