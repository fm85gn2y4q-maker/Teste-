"""Extração do texto dos PDFs, página a página.

A página é a menor âncora conferível de um ato normativo: permite dizer "art.
5º, p. 3" e o advogado abrir e ver. Sem ela, a citação obriga a confiar.
"""

from __future__ import annotations

import re

import fitz  # PyMuPDF

# Quebra de linha no meio de palavra hifenizada é artefato de diagramação, e
# não do texto: junta-se, senão a busca por "responsabilidade" perde o que o
# PDF quebrou como "responsabi-\nlidade".
_HIFEN = re.compile(r"(\w)-\s*\n\s*(\w)")


def limpar(texto: str) -> str:
    texto = _HIFEN.sub(r"\1\2", texto)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def paginas_do_pdf(conteudo: bytes) -> list[str]:
    with fitz.open(stream=conteudo, filetype="pdf") as doc:
        return [limpar(p.get_text("text") or "") for p in doc]
