"""Etapa 2b — OCR dos PDFs que são digitalização sem camada de texto.

369 dos 609 inteiros teores públicos são imagem, concentrados entre 2010 e
2014 — justamente o período em que a extinta Câmara Nacional de Uniformização
mais produziu. Sem OCR eles são invisíveis à busca.

Grava o resultado em `ocr/<id>.json`, ao lado do acervo, e não toca no banco:
quem consome é o `indexar.py`, que passa a ler o texto de lá quando o PDF não
tem camada própria. Assim o OCR roda uma vez e a reindexação continua barata.

Retomável: pula o que já está gravado.

O modelo é o `tessdata_best` de português. O rápido erra acento e cedilha, e num
acervo jurídico isso não é detalhe: "não" vira "nao" e a busca literal perde o
documento.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ACERVO = Path.home() / "Documents" / "AGU_Acervo_Consultivo"
PDFS = ACERVO / "pdfs"
SAIDA = ACERVO / "ocr"
TESSDATA = ACERVO / "tessdata"
TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
BANCO = ACERVO / "agu_consultivo.db"

DPI = 300           # abaixo disso o corpo 10 do parecer digitalizado se perde
IDIOMA = "por"
TRABALHADORES = max(1, (os.cpu_count() or 4) - 2)


def _ocr_pagina(png: bytes) -> str:
    # psm 3 (segmentação automática, sem detecção de orientação) — medido nestes
    # documentos, psm 1 e 200/400 dpi dão exatamente o mesmo texto e custam mais.
    # O limite é a fonte: são fotocópias degradadas, e nenhum ajuste de
    # renderização recupera o que o papel já perdeu.
    r = subprocess.run(
        [str(TESSERACT), "stdin", "stdout", "-l", IDIOMA, "--psm", "3"],
        input=png, capture_output=True,
        env={**os.environ, "TESSDATA_PREFIX": str(TESSDATA)},
    )
    if r.returncode != 0:
        return ""
    return r.stdout.decode("utf-8", "ignore")


def processar(ident: int) -> tuple[int, int, int]:
    """(id, páginas, caracteres reconhecidos)."""
    destino = SAIDA / f"{ident}.json"
    if destino.exists():
        try:
            dados = json.loads(destino.read_text(encoding="utf-8"))
            return ident, len(dados), sum(len(p) for p in dados)
        except json.JSONDecodeError:
            pass  # arquivo truncado por interrupção: refaz
    import fitz
    paginas: list[str] = []
    try:
        with fitz.open(PDFS / f"{ident}.pdf") as doc:
            for pagina in doc:
                pix = pagina.get_pixmap(dpi=DPI)
                paginas.append(_ocr_pagina(pix.tobytes("png")))
    except Exception:
        return ident, 0, 0
    destino.write_text(json.dumps(paginas, ensure_ascii=False), encoding="utf-8")
    return ident, len(paginas), sum(len(p) for p in paginas)


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    if not TESSERACT.exists():
        sys.exit(f"Tesseract não encontrado em {TESSERACT}")
    if not (TESSDATA / f"{IDIOMA}.traineddata").exists():
        sys.exit(f"falta {IDIOMA}.traineddata em {TESSDATA}")

    alvos = sorted(int(p.stem) for p in PDFS.glob("*.pdf")
                   if not (SAIDA / f"{p.stem}.json").exists())
    alvos = [i for i in alvos if _precisa(i)]
    print(f"{len(alvos)} PDFs para reconhecer, {TRABALHADORES} processos")
    feitos = paginas = caracteres = 0
    with ProcessPoolExecutor(max_workers=TRABALHADORES) as pool:
        for ident, n, chars in pool.map(processar, alvos):
            feitos += 1
            paginas += n
            caracteres += chars
            if feitos % 25 == 0:
                print(f"  {feitos}/{len(alvos)}  {paginas} páginas  "
                      f"{caracteres/1000:.0f}k caracteres", flush=True)
    print(f"pronto: {feitos} documentos, {paginas} páginas, "
          f"{caracteres/1000:.0f}k caracteres em {SAIDA}")


def _precisa(ident: int) -> bool:
    """Só reconhece o que não tem camada de texto própria."""
    import fitz
    try:
        with fitz.open(PDFS / f"{ident}.pdf") as doc:
            return len("".join(p.get_text() or "" for p in doc).strip()) < 200
    except Exception:
        return False


if __name__ == "__main__":
    main()
