"""python -m servidor  →  stdio;  --http  →  streamable-HTTP."""
import argparse
import os

from .servidor import construir

p = argparse.ArgumentParser(prog="servidor")
p.add_argument("-b", "--banco")
p.add_argument("--http", action="store_true")
p.add_argument("--host", default=os.environ.get("NORMAS_HOST", "127.0.0.1"))
p.add_argument("--porta", type=int, default=int(os.environ.get("PORT", 8080)))
p.add_argument("--dominio", action="append", default=[
    d for d in (os.environ.get("NORMAS_DOMINIOS") or "").split(",") if d])
a = p.parse_args()

ajustes = {"host": a.host, "port": a.porta} if a.http else {}
mcp = construir(a.banco, a.dominio, **ajustes)
mcp.run(transport="streamable-http" if a.http else "stdio")
