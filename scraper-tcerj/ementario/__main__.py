"""Entrada do servidor MCP do Ementário.

    python -m ementario                  # stdio, para o Claude
    python -m ementario --http           # HTTP em 127.0.0.1:8765, para o ChatGPT
"""

from __future__ import annotations

import argparse
import os
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
    # Em hospedagem, host/porta/domínio vêm do ambiente: o serviço sorteia a
    # porta (PORT é o padrão do Cloud Run e afins) e o endereço público só se
    # conhece depois do primeiro deploy.
    parser.add_argument("--host", default=os.environ.get("EMENTARIO_HOST", "127.0.0.1"))
    parser.add_argument(
        "--porta", type=int, default=int(os.environ.get("PORT", "8765"))
    )
    parser.add_argument("--banco", help="caminho do SQLite (padrão: dados/tcerj.sqlite)")
    parser.add_argument(
        "--dominio",
        action="append",
        metavar="HOST",
        help="domínio público por onde o servidor será acessado (túnel ou "
             "hospedagem). Sem isto, só requisições locais passam. Pode repetir.",
    )
    parser.add_argument(
        "--url-publica",
        metavar="URL",
        help="endereço público completo. Ativa o fluxo OAuth, exigido pelo "
             "ChatGPT. O Claude conecta sem isto.",
    )
    args = parser.parse_args(argv)

    from .servidor import construir

    # EMENTARIO_DOMINIOS aceita vários separados por vírgula: em hospedagem o
    # endereço vem de fora, e não da linha de comando.
    dominios = list(args.dominio or [])
    do_ambiente = os.environ.get("EMENTARIO_DOMINIOS", "")
    dominios += [d.strip() for d in do_ambiente.split(",") if d.strip()]

    # Com URL pública declarada, o servidor também passa a ser servidor de
    # autorização OAuth — exigência do ChatGPT, dispensável no Claude.
    url_publica = args.url_publica or os.environ.get("EMENTARIO_URL_PUBLICA")
    if url_publica and not url_publica.startswith(("http://", "https://")):
        url_publica = f"https://{url_publica}"

    ajustes = {"host": args.host, "port": args.porta} if args.http else {}
    try:
        servidor = construir(
            args.banco,
            dominios=dominios or None,
            url_publica=url_publica,
            segredo_oauth=os.environ.get("EMENTARIO_SEGREDO_OAUTH"),
            **ajustes,
        )
    except FileNotFoundError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    if args.http:
        alcance = ", ".join(dominios) if dominios else "somente local"
        print(f"Ementário em http://{args.host}:{args.porta}/mcp  ({alcance})",
              file=sys.stderr)

    servidor.run(transport="streamable-http" if args.http else "stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
