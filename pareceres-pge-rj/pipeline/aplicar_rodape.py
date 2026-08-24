# -*- coding: utf-8 -*-
"""Corta o rodape do SEI do fim de `conclusao` e `fecho`.

Etapa 8 do pipeline. Roda sobre o que ja esta no banco -- nao relê PDF nem
pagina. Idempotente: rodar duas vezes nao muda nada na segunda.
"""
import os
import sqlite3
import sys

from rodape import limpa_rodape

from caminhos import DB


def main():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    ups = []
    for cod, c, f in con.execute(
            """SELECT codigo, conclusao, fecho FROM documentos
               WHERE COALESCE(conclusao,'') <> '' OR COALESCE(fecho,'') <> ''"""):
        nc, nf = limpa_rodape(c or ""), limpa_rodape(f or "")
        if nc != (c or "") or nf != (f or ""):
            ups.append((nc, nf, cod))
    con.executemany("UPDATE documentos SET conclusao=?, fecho=? WHERE codigo=?", ups)
    con.commit()
    media = con.execute(
        "SELECT AVG(LENGTH(conclusao)) FROM documentos WHERE conclusao <> ''").fetchone()[0]
    print("documentos ajustados: %d | conclusao media: %.0f caracteres"
          % (len(ups), media or 0))
    con.close()


if __name__ == "__main__":
    sys.exit(main())
