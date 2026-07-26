"""Baixa o acervo comprimido publicado como asset de release.

O banco não vive no Git: é artefato de dados, gerado por programa e versionado
à parte. A imagem o busca na construção, com a versão fixada — assim um deploy
é reproduzível, o rollback é trocar a versão, e uma coleta ruim não altera
produção em silêncio.

    python baixar_acervo.py <url> <destino> [sha256]
"""

from __future__ import annotations

import gzip
import hashlib
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path


def baixar(url: str, destino: Path, esperado: str | None = None) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"Baixando {url}", file=sys.stderr)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".gz") as temporario:
        comprimido = Path(temporario.name)
    try:
        with urllib.request.urlopen(url, timeout=300) as resposta:
            with comprimido.open("wb") as saida:
                shutil.copyfileobj(resposta, saida, length=4 * 1024 * 1024)

        if esperado:
            digest = hashlib.sha256(comprimido.read_bytes()).hexdigest()
            if digest != esperado:
                raise SystemExit(
                    f"Conferência falhou.\n  esperado: {esperado}\n  obtido:   {digest}"
                )
            print("Integridade conferida.", file=sys.stderr)

        with gzip.open(comprimido, "rb") as entrada, destino.open("wb") as saida:
            shutil.copyfileobj(entrada, saida, length=4 * 1024 * 1024)
    finally:
        comprimido.unlink(missing_ok=True)

    print(f"Acervo em {destino} ({destino.stat().st_size / 1048576:.1f} MB)",
          file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    baixar(sys.argv[1], Path(sys.argv[2]),
           sys.argv[3] if len(sys.argv) > 3 else None)
