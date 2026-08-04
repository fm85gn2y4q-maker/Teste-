"""Entrada do servidor MCP do acervo consultivo da AGU.

    python -m agu                  # stdio, para o Claude Desktop
    python -m agu --http           # HTTP em 127.0.0.1:8767
"""

from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m agu",
        description="Servidor MCP sobre o acervo consultivo da Advocacia-Geral "
                    "da União: CONUNI, Orientações Normativas e Súmulas.",
    )
    parser.add_argument("--http", action="store_true",
                        help="serve por HTTP em vez de stdio")
    parser.add_argument("--host", default=os.environ.get("AGU_HOST", "127.0.0.1"))
    parser.add_argument("--porta", type=int, default=int(os.environ.get("PORT", "8767")))
    parser.add_argument("--banco", help="caminho do SQLite do acervo")
    parser.add_argument("--dominio", action="append", metavar="HOST",
                        help="domínio público por onde o servidor será acessado. "
                             "Sem isto, só requisições locais passam. Pode repetir.")
    args = parser.parse_args(argv)

    from .servidor import construir

    dominios = list(args.dominio or [])
    do_ambiente = os.environ.get("AGU_DOMINIOS", "")
    dominios += [d.strip() for d in do_ambiente.split(",") if d.strip()]

    ajustes = {"host": args.host, "port": args.porta} if args.http else {}
    try:
        servidor = construir(args.banco, dominios=dominios or None, **ajustes)
    except FileNotFoundError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    if args.http:
        alcance = ", ".join(dominios) if dominios else "somente local"
        print(f"Consultivo AGU em http://{args.host}:{args.porta}/mcp  ({alcance})",
              file=sys.stderr)

    servidor.run(transport="streamable-http" if args.http else "stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
