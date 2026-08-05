"""Coleta dos atos normativos do TCE-RJ.

    python -m normas coletar          metadados + grafo de revogação
    python -m normas textos           PDFs (6 requisições) e extração
    python -m normas situacao         o que a coleta revelou
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .armazenamento import Armazenamento
from .coleta import ESPECIES, Cliente, baixar_pdf, listar

BANCO = "dados/normas-tcerj.sqlite"


def cmd_coletar(args) -> int:
    cliente = Cliente(intervalo=args.intervalo)
    with Armazenamento(args.banco) as arm:
        for chave, rotulo in ESPECIES.items():
            atos = listar(cliente, chave)
            n = arm.gravar_atos(atos)
            revogados = sum(1 for a in atos if a.revogado or a.revogado_em)
            print(f"  {rotulo:<14} {n:>4} atos   revogados: {revogados}", flush=True)
        e = arm.estatisticas()
    print(f"\n  total: {e['atos']} atos, {e['revogacoes']} relações de revogação")
    return 0


def cmd_textos(args) -> int:
    from .extracao import paginas_do_pdf

    cliente = Cliente(intervalo=args.intervalo)
    with Armazenamento(args.banco) as arm:
        fila = arm.sem_texto()
        print(f"  na fila: {len(fila)} atos  (~{len(fila)*args.intervalo/60:.0f} min)\n",
              flush=True)
        feitos = falhas = paginas = 0
        for item in fila:
            if not item["arquivo_id"]:
                arm.marcar_sem_arquivo(item["id"], "ato sem arquivoId na fonte")
                falhas += 1
                continue
            try:
                pdf = baixar_pdf(cliente, item["arquivo_id"])
                p = paginas_do_pdf(pdf)
            except Exception as erro:  # noqa: BLE001 — rede e PDF de terceiro
                arm.marcar_sem_arquivo(item["id"], str(erro)[:200])
                print(f"    falhou {item['id']}: {str(erro)[:90]}", flush=True)
                falhas += 1
                continue
            paginas += arm.gravar_paginas(item["id"], p)
            feitos += 1
            if feitos % 50 == 0:
                print(f"    ... {feitos}/{len(fila)}  {paginas} páginas", flush=True)
        print(f"\n  coletados: {feitos} atos, {paginas} páginas"
              f"{f', {falhas} falhas' if falhas else ''}")
        pendentes = arm.sem_texto()
    if pendentes:
        print(f"\n  sem texto: {len(pendentes)}")
        for p in pendentes[:10]:
            print(f"    {p['especie']} {p['numero']}/{p['ano']}")
    return 0


def cmd_situacao(args) -> int:
    with Armazenamento(args.banco) as arm:
        e = arm.estatisticas()
        print(f"  {'espécie':<16}{'atos':>6}{'revogados':>11}{'c/ texto':>10}"
              f"   período")
        for l in e["por_especie"]:
            print(f"  {ESPECIES.get(l['especie'], l['especie']):<16}"
                  f"{l['atos']:>6}{l['revogados']:>11}{l['com_texto']:>10}"
                  f"   {l['de']}–{l['ate']}")
        print(f"\n  páginas ......... {e['paginas']:,}")
        print(f"  caracteres ...... {e['caracteres']:,}")
        print(f"  revogações ...... {e['revogacoes']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="normas", description=__doc__)
    p.add_argument("-b", "--banco", default=BANCO, type=Path)
    p.add_argument("--intervalo", type=float, default=1.5,
                   help="segundos entre requisições (servidor público)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("coletar").set_defaults(func=cmd_coletar)
    sub.add_parser("textos").set_defaults(func=cmd_textos)
    sub.add_parser("situacao").set_defaults(func=cmd_situacao)
    args = p.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrompido. O que foi gravado permanece.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
