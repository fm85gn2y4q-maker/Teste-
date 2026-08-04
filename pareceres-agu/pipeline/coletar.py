"""Etapa 1 — colhe as três fontes e grava JSONL ao lado deste script."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fontes  # noqa: E402

AQUI = Path(__file__).resolve().parent


def gravar(nome: str, registros: list[dict]) -> Path:
    destino = AQUI / nome
    with destino.open("w", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return destino


def main() -> None:
    for nome, coletor in (("conuni.jsonl", fontes.conuni),
                          ("ons.jsonl", fontes.ons),
                          ("sumulas.jsonl", fontes.sumulas)):
        registros = coletor()
        destino = gravar(nome, registros)
        print(f"{nome:16} {len(registros):>6} registros  ->  {destino.name}"
              f"  ({destino.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
