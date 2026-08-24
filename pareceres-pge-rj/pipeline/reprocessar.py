# -*- coding: utf-8 -*-
"""Etapa 9: recalcula conclusao e regime sobre o que ja esta no banco.

  - conclusao: passa a rejeitar peca de terceiro reproduzida no fim do parecer
    (decisao do TCE, manifestacao do MPC), marcando `conclusao_alheia` quando
    nao houver alternativa;
  - regime: reconhece a materia de terceiro setor antes da de licitacao.

Le as paginas do indice numa varredura sequencial; nao rele PDF.
"""
import collections
import os
import sqlite3
import time

from conclusao import conclusao_de
from regime import regime_e_alerta
from rodape import limpa_rodape

from caminhos import DB


def main():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    try:
        con.execute("ALTER TABLE documentos ADD COLUMN conclusao_alheia INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    t0 = time.time()
    print("[1] conclusao: relendo o texto das paginas", flush=True)
    porcod = collections.defaultdict(list)
    for cod, pag, txt in con.execute(
            "SELECT codigo, pagina, texto FROM paginas_fts ORDER BY codigo, pagina"):
        porcod[cod].append(txt or "")
    print("    %d documentos em %.0fs" % (len(porcod), time.time() - t0), flush=True)

    ups, tipos, alheias, mudou = [], collections.Counter(), 0, 0
    antigas = dict(con.execute("SELECT codigo, conclusao FROM documentos"))
    for cod, pags in porcod.items():
        txt = "\n".join(pags)
        conc, tipo, alheio = conclusao_de(txt)
        conc = limpa_rodape(conc)
        tipos[tipo or "(nenhuma)"] += 1
        if alheio:
            alheias += 1
        if (antigas.get(cod) or "") != conc:
            mudou += 1
        ups.append((conc, tipo, 1 if alheio else 0,
                    limpa_rodape(" ".join(txt[-1500:].split())), cod))
    con.executemany("""UPDATE documentos SET conclusao=?, conclusao_tipo=?,
                       conclusao_alheia=?, fecho=? WHERE codigo=?""", ups)
    con.commit()
    print("    conclusoes alteradas: %d | marcadas como peca de terceiro: %d"
          % (mudou, alheias), flush=True)
    print("    por tipo: %s" % tipos.most_common(), flush=True)

    print("\n[2] regime: terceiro setor antes de licitacao", flush=True)
    refs = collections.defaultdict(set)
    for cod, r in con.execute("SELECT codigo, referencia FROM citacoes WHERE especie='norma'"):
        refs[cod].add(r)
    ups, regs, antes = [], collections.Counter(), dict(
        con.execute("SELECT codigo, regime FROM documentos"))
    trocou = 0
    for cod, ano, eixos in con.execute("SELECT codigo, ano, eixos FROM documentos"):
        reg, al = regime_e_alerta(ano, refs.get(cod, set()), eixos or "")
        regs[reg] += 1
        if antes.get(cod) != reg:
            trocou += 1
        ups.append((reg, al, cod))
    con.executemany("UPDATE documentos SET regime=?, alerta_vigencia=? WHERE codigo=?", ups)
    con.commit()
    print("    documentos que mudaram de regime: %d" % trocou, flush=True)
    for r, n in regs.most_common():
        print("      %-46s %5d" % (r, n), flush=True)
    print("\nFIM em %.0f min" % ((time.time() - t0) / 60), flush=True)
    con.close()


if __name__ == "__main__":
    main()
