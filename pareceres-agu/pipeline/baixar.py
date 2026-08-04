"""Etapa 2 — baixa os inteiros teores que a AGU publica em arquivo.

Das 1.724 manifestações do CONUNI, só uma parte tem PDF acessível sem senha.
As demais apontam para o Sapiens, sistema interno da AGU, cuja rota pública
devolve a tela de login. Este script não tenta contornar isso: baixa o que é
público, registra o que não é, e o número entra na cobertura do acervo.

Retomável: pula o que já está em disco.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fontes  # noqa: E402

AQUI = Path(__file__).resolve().parent
ACERVO = Path.home() / "Documents" / "AGU_Acervo_Consultivo"
PDFS = ACERVO / "pdfs"
CONCORRENCIA = 4  # servidor da AGU; não aumente


def alvos() -> list[tuple[int, str]]:
    """(id, url) das manifestações com arquivo público."""
    saida = []
    for linha in (AQUI / "conuni.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(linha)
        url = r.get("url_inteiro_teor")
        # origem 3 é o repositório de arquivos da CGU/AGU: PDF direto.
        # origem 2 é o Sapiens, que exige autenticação.
        if url and "/decor/arquivos/" in url:
            saida.append((r["id"], url))
    return saida


def baixar(item: tuple[int, str]) -> tuple[int, str]:
    ident, url = item
    destino = PDFS / f"{ident}.pdf"
    if destino.exists() and destino.stat().st_size > 1024:
        return ident, "ja_tinha"
    try:
        dados = fontes._abrir(url, timeout=180)
    except Exception as e:
        return ident, f"falha: {type(e).__name__}"
    if not dados.startswith(b"%PDF"):
        return ident, "nao_e_pdf"
    destino.write_bytes(dados)
    time.sleep(0.3)
    return ident, "baixado"


def main() -> None:
    PDFS.mkdir(parents=True, exist_ok=True)
    lista = alvos()
    print(f"{len(lista)} manifestações com arquivo público")
    contagem: dict[str, int] = {}
    falhas: list[str] = []
    with ThreadPoolExecutor(max_workers=CONCORRENCIA) as pool:
        for n, (ident, estado) in enumerate(pool.map(baixar, lista), 1):
            chave = estado.split(":")[0]
            contagem[chave] = contagem.get(chave, 0) + 1
            if chave == "falha" or estado == "nao_e_pdf":
                falhas.append(f"{ident}\t{estado}")
            if n % 100 == 0:
                print(f"  {n}/{len(lista)}  {contagem}")
    print(contagem)
    if falhas:
        (ACERVO / "_falhas_download.txt").write_text("\n".join(falhas), encoding="utf-8")
        print(f"falhas registradas em {ACERVO / '_falhas_download.txt'}")


if __name__ == "__main__":
    main()
