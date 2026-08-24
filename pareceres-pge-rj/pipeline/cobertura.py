# -*- coding: utf-8 -*-
"""Mostra a cobertura declarada pelo banco -- o que o servidor vai dizer.

E a conferencia depois de qualquer coleta: se o numero de documentos aqui nao
subiu, o que quer que tenha rodado nao chegou ao banco que o servidor abre.
"""
import sqlite3

from caminhos import DB

con = sqlite3.connect(DB)
print(DB)
for chave, valor in con.execute("SELECT chave, valor FROM cobertura"):
    print("%-22s %s" % (chave, valor[:110]))
con.close()
