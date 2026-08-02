# -*- coding: utf-8 -*-
"""Refaz o banco inteiro sobre o acervo completo, na ordem certa.

    fichas -> paginas/conclusao/citacoes -> tesauro/proveniencia/regime
    -> corte de rodape -> situacao das normas -> compactacao

Cada etapa ja existe e ja foi testada isoladamente; aqui elas rodam em
sequencia, com o relatorio de cada uma, para nao depender de eu lembrar a
ordem numa proxima vez.
"""
import os
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))

ETAPAS = [
    ("fichas do acervo inteiro", "indexar_total.py"),
    ("paginas, conclusao e citacoes", "passada2.py"),
    ("tesauro, proveniencia e regime", "passada3.py"),
    ("corte do rodape do SEI", "aplicar_rodape.py"),
    ("situacao das normas", "situacao_normas.py"),
    ("compactacao", "enxugar.py"),
]


def main():
    inicio = time.time()
    for i, (rotulo, script) in enumerate(ETAPAS, 1):
        print("\n" + "=" * 70, flush=True)
        print("[%d/%d] %s  (%s)" % (i, len(ETAPAS), rotulo, script), flush=True)
        print("=" * 70, flush=True)
        t0 = time.time()
        r = subprocess.run([sys.executable, "-u", os.path.join(AQUI, script)],
                           cwd=AQUI, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print("\nFALHOU em %s (codigo %d). Parando." % (script, r.returncode),
                  file=sys.stderr, flush=True)
            return r.returncode
        print("  -- %s: %.0f min" % (rotulo, (time.time() - t0) / 60), flush=True)
    print("\nTUDO PRONTO em %.0f min" % ((time.time() - inicio) / 60), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
