"""Entrada do servidor MCP do Ementário.

    python -m ementario                  # stdio, para o Claude
    python -m ementario --http           # HTTP em 127.0.0.1:8765, para o ChatGPT
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ementario",
        description="Servidor MCP sobre a jurisprudência do TCE-RJ.",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="serve por HTTP em vez de stdio (necessário para o ChatGPT)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta", type=int, default=8765)
    parser.add_argument("--banco", help="caminho do SQLite (padrão: dados/tcerj.sqlite)")
    parser.add_argument(
        "--dominio",
        action="append",
        metavar="HOST",
        help="domínio público por onde o servidor será acessado (túnel ou "
             "hospedagem). Sem isto, só requisições locais passam. Pode repetir.",
    )
    args = parser.parse_args(argv)

    from .servidor import construir

    ajustes = {"host": args.host, "port": args.porta} if args.http else {}
    try:
        servidor = construir(args.banco, dominios=args.dominio, **ajustes)
    except FileNotFoundError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    if args.http:
        alcance = ", ".join(args.dominio) if args.dominio else "somente local"
        print(f"Ementário em http://{args.host}:{args.porta}/mcp  ({alcance})",
              file=sys.stderr)

    servidor.run(transport="streamable-http" if args.http else "stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
