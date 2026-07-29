"""Linha de comando do acervo."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta

from .config import CFG


def _data(s: str) -> date:
    return date.fromisoformat(s)


def cmd_coletar(args) -> int:
    from .crawl.ejuris import EJuris
    from .crawl.eproc import EProc
    from .pipeline.ingest import coletar

    coletores = {"ejuris": EJuris, "eproc": lambda: EProc(grau=args.grau)}
    if args.fonte not in coletores:
        print(f"fonte desconhecida: {args.fonte}")
        return 2

    coletor = coletores[args.fonte]()
    resumo = coletar(
        coletor, args.de, args.ate, com_teor=not args.sem_teor, retomar=not args.recomecar
    )
    print(resumo)
    return 0


def cmd_cobertura(args) -> int:
    import json

    from .mcp.server import cobertura_do_acervo

    print(json.dumps(cobertura_do_acervo(), ensure_ascii=False, indent=2))
    return 0


def cmd_auditar(args) -> int:
    """Compara a base local com o universo do DataJud."""
    from .crawl.datajud import DataJud
    from .db import conectar, migrar

    con = conectar(CFG.banco)
    migrar(con)
    coletados = {
        r["numero_cnj"]
        for r in con.execute(
            "SELECT DISTINCT numero_cnj FROM acordao WHERE numero_cnj IS NOT NULL"
            " AND data_julgamento BETWEEN ? AND ?",
            (args.de.isoformat(), args.ate.isoformat()),
        )
    }
    con.close()
    div = DataJud().conferir_cobertura(args.de, args.ate, coletados)
    print(div)
    for n in div.faltando[:50]:
        print("  faltando:", n)
    if len(div.faltando) > 50:
        print(f"  ... mais {len(div.faltando) - 50}")
    return 0


def cmd_reprocessar(args) -> int:
    from .pipeline.ingest import reprocessar

    print(f"{reprocessar()} acórdãos reprocessados")
    return 0


def cmd_mcp(args) -> int:
    from .mcp.server import main as mcp_main

    mcp_main()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser("tjrj", description="Acervo de jurisprudência do TJRJ")
    p.add_argument("-v", "--verboso", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    ontem = date.today() - timedelta(days=1)

    c = sub.add_parser("coletar", help="varre um período e grava no acervo")
    c.add_argument("fonte", choices=["ejuris", "eproc"])
    c.add_argument("--de", type=_data, default=CFG.inicio_historico)
    c.add_argument("--ate", type=_data, default=ontem)
    c.add_argument("--grau", default="2")
    c.add_argument("--sem-teor", action="store_true", help="só ementas (varredura rápida)")
    c.add_argument("--recomecar", action="store_true", help="ignora fatias já concluídas")
    c.set_defaults(func=cmd_coletar)

    a = sub.add_parser("auditar", help="mede a cobertura contra o DataJud/CNJ")
    a.add_argument("--de", type=_data, required=True)
    a.add_argument("--ate", type=_data, required=True)
    a.set_defaults(func=cmd_auditar)

    sub.add_parser("cobertura", help="relatório do acervo").set_defaults(func=cmd_cobertura)
    sub.add_parser("reprocessar", help="reextrai composição do texto já baixado").set_defaults(
        func=cmd_reprocessar
    )
    sub.add_parser("mcp", help="sobe o servidor MCP").set_defaults(func=cmd_mcp)

    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verboso else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
