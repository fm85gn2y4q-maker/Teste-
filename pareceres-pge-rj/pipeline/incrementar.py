# -*- coding: utf-8 -*-
"""Incorpora ao banco o que o `atualizar.py` colheu -- so isso.

O `reindexar_tudo.py` refaz o acervo inteiro: 23 mil PDFs relidos, horas de
maquina. Para algumas dezenas de documentos novos isso e absurdo, e o remedio
NAO foi escrever um segundo pipeline: as etapas caras ganharam o modo
`--novos` e sao as mesmas de sempre. Duas copias da mesma logica foi o que
produziu os tres defeitos de indexacao da vez passada.

  1. baixar_resto.py        pula o que ja esta em disco; baixa so o que falta
  2. indexar_total --novos  fichas dos codigos de novos.txt
  3. passada2 --novos       PDF -> paginas, conclusao e citacoes
  4. passada3               tesauro, proveniencia, regime e cobertura
  5. aplicar_rodape         corte do rodape do SEI (idempotente)
  6. situacao_normas        tabela de inconstitucionalidade e revogacao
  7. enxugar                compactacao

As quatro ultimas rodam sobre o banco inteiro, sem reler PDF: sao minutos, e
recalcular tudo evita a pergunta "esta parte ficou de fora?".

    python atualizar.py && python incrementar.py
"""
import os
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
NOVOS = os.path.join(AQUI, "novos.txt")

ETAPAS = [
    ("PDFs que faltam", "baixar_resto.py", []),
    ("fichas dos novos", "indexar_total.py", ["--novos"]),
    ("paginas, conclusao e citacoes", "passada2.py", ["--novos"]),
    ("tesauro, proveniencia, regime e cobertura", "passada3.py", []),
    ("corte do rodape do SEI", "aplicar_rodape.py", []),
    ("situacao das normas", "situacao_normas.py", []),
    ("compactacao", "enxugar.py", []),
]


def main():
    if not os.path.exists(NOVOS):
        print("nao ha %s. Rode antes:  python atualizar.py" % NOVOS,
              file=sys.stderr, flush=True)
        return 1
    quantos = sum(1 for l in open(NOVOS, encoding="utf-8") if l.strip())
    if not quantos:
        print("novos.txt vazio: nada a incorporar.", flush=True)
        return 0
    print("documentos novos a incorporar: %d" % quantos, flush=True)

    # Retomar de uma etapa: as sete sao re-executaveis por construcao (as duas
    # incrementais pulam o que ja esta no banco, as outras reconstroem), entao
    # repetir e seguro -- mas a etapa 1 gasta 10 min so conferindo disco, e nao
    # ha razao para paga-la de novo quando quem falhou foi a etapa 5.
    de = 1
    for a in sys.argv[1:]:
        if a.startswith("--de="):
            de = int(a.split("=", 1)[1])

    inicio = time.time()
    for i, (rotulo, script, args) in enumerate(ETAPAS, 1):
        if i < de:
            print("[%d/%d] %s  -- pulada (--de=%d)" % (i, len(ETAPAS), rotulo, de), flush=True)
            continue
        print("\n" + "=" * 70, flush=True)
        print("[%d/%d] %s  (%s %s)" % (i, len(ETAPAS), rotulo, script, " ".join(args)),
              flush=True)
        print("=" * 70, flush=True)
        t0 = time.time()
        # Uma segunda chance. O `optimize` do FTS5 reescreve o indice inteiro e
        # ja morreu uma vez com "disk I/O error" que nao se repetiu no retry --
        # antivirus segurando o arquivo, nao defeito do banco. Derrubar sete
        # etapas por causa disso e desperdicio; insistir uma vez, nao.
        for tentativa in (1, 2):
            r = subprocess.run([sys.executable, "-u", os.path.join(AQUI, script)] + args,
                               cwd=AQUI, text=True, encoding="utf-8", errors="replace")
            if r.returncode == 0:
                break
            if tentativa == 1:
                print("\n  %s falhou (codigo %d). Segunda tentativa em 30 s."
                      % (script, r.returncode), file=sys.stderr, flush=True)
                time.sleep(30)
        if r.returncode != 0:
            print("\nFALHOU em %s (codigo %d), duas vezes. Parando.\n"
                  "Depois de resolver, retome com:  python incrementar.py --de=%d"
                  % (script, r.returncode, i), file=sys.stderr, flush=True)
            return r.returncode
        print("  -- %s: %.1f min" % (rotulo, (time.time() - t0) / 60), flush=True)

    print("\nPRONTO em %.0f min" % ((time.time() - inicio) / 60), flush=True)
    print("Confira a cobertura antes de publicar:  python cobertura.py", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
