"""Etapa 4 — publica o acervo como asset de release e fixa a versão na imagem.

Comprime o banco, calcula o sha256, cria a release no GitHub e reescreve as
duas linhas do `Dockerfile`. São duas porque a construção confere o hash: URL
sem hash correspondente falha o deploy, que é o comportamento desejado.

    python publicar.py 1.0.0
    python publicar.py 1.0.0 --so-preparar   # comprime e mostra, sem publicar
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
ACERVO = Path.home() / "Documents" / "AGU_Acervo_Consultivo"
BANCO = ACERVO / "agu_consultivo.db"
REPO = "fm85gn2y4q-maker/Teste-"
BLOCO = 4 * 1024 * 1024


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for pedaco in iter(lambda: f.read(BLOCO), b""):
            h.update(pedaco)
    return h.hexdigest()


def _numeros() -> dict[str, int]:
    con = sqlite3.connect(f"file:{BANCO.as_posix()}?mode=ro", uri=True)
    n = {
        "documentos": con.execute("SELECT COUNT(*) FROM documentos").fetchone()[0],
        "com_texto": con.execute(
            "SELECT COUNT(*) FROM documentos WHERE tem_texto = 1").fetchone()[0],
        "ocr": con.execute(
            "SELECT COUNT(*) FROM documentos WHERE origem_texto = 'ocr'").fetchone()[0],
        "paginas": con.execute("SELECT COUNT(*) FROM paginas").fetchone()[0],
    }
    con.close()
    return n


def comprimir(versao: str) -> tuple[Path, str]:
    destino = RAIZ / f"consultivo-agu-v{versao}.db.gz"
    with BANCO.open("rb") as entrada, gzip.open(destino, "wb", 6) as saida:
        shutil.copyfileobj(entrada, saida, BLOCO)
    return destino, _sha256(destino)


def fixar_no_dockerfile(versao: str, sha: str) -> None:
    caminho = RAIZ / "Dockerfile"
    texto = caminho.read_text(encoding="utf-8")
    url = (f"https://github.com/{REPO}/releases/download/"
           f"consultivo-agu-v{versao}/consultivo-agu-v{versao}.db.gz")
    texto, n1 = re.subn(r"(?m)^ARG ACERVO_URL=.*$", f"ARG ACERVO_URL={url}", texto)
    texto, n2 = re.subn(r"(?m)^ARG ACERVO_SHA256=.*$", f"ARG ACERVO_SHA256={sha}", texto)
    if n1 != 1 or n2 != 1:
        raise SystemExit(
            f"Dockerfile não tem as duas linhas esperadas (URL: {n1}, SHA: {n2}). "
            "Sem elas a imagem sobe sem acervo, e o motivo fica invisível.")
    caminho.write_text(texto, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(prog="python publicar.py")
    p.add_argument("versao")
    p.add_argument("--so-preparar", action="store_true",
                   help="comprime e mostra o hash, sem criar a release")
    args = p.parse_args()

    if not BANCO.exists():
        sys.exit(f"banco não encontrado em {BANCO}")
    n = _numeros()
    arquivo, sha = comprimir(args.versao)
    print(f"{arquivo.name}  {arquivo.stat().st_size/1048576:.0f} MB\nsha256 {sha}")
    print(f"acervo: {n['documentos']} documentos, {n['com_texto']} com texto "
          f"({n['ocr']} por OCR), {n['paginas']} páginas")

    if args.so_preparar:
        return

    notas = (f"{n['documentos']} documentos do acervo consultivo da AGU: CONUNI, "
             f"Orientações Normativas e Súmulas. {n['com_texto']} com texto "
             f"pesquisável, dos quais {n['ocr']} recuperados por OCR. "
             f"{n['paginas']} páginas indexadas.")
    subprocess.run(
        ["gh", "release", "create", f"consultivo-agu-v{args.versao}", str(arquivo),
         "--repo", REPO, "--title", f"Acervo consultivo AGU v{args.versao}",
         "--notes", notas],
        check=True)
    fixar_no_dockerfile(args.versao, sha)
    print(f"Dockerfile fixado em v{args.versao}. Falta commitar e enviar — é o "
          f"push que dispara a construção no Render.")


if __name__ == "__main__":
    main()
