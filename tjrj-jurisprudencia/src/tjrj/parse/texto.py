"""Conversão do documento bruto em páginas de texto.

O inteiro teor chega em três formas, e a diferença entre elas não é
cosmética:

* **PDF com camada de texto** — o caso bom.
* **HTML** — não tem páginas; fatiamos por tamanho para que a citação
  "à p. N" continue significando alguma coisa estável.
* **PDF digitalizado** (acórdãos antigos, principalmente pré-2010) — não tem
  texto nenhum. Sem OCR, esses documentos entram na base como acórdãos
  vazios e desaparecem de toda busca por inteiro teor, silenciosamente. É a
  segunda maior fonte de lacuna invisível do projeto, depois do teto de
  resultados.

Por isso `paginar` devolve também a origem (`pdf`/`html`/`rtf`/`ocr`): ela
vai para o banco e aparece no relatório de cobertura.
"""

from __future__ import annotations

import io
import logging
import re

log = logging.getLogger("tjrj.texto")

# Abaixo disto, uma "página" de PDF é considerada sem camada de texto.
MIN_CARACTERES_PAGINA = 40
TAMANHO_PAGINA_HTML = 3000


def paginar(conteudo: bytes, content_type: str = "") -> tuple[list[str], str]:
    """Devolve (páginas, origem)."""
    tipo = (content_type or "").lower()
    if conteudo[:5] == b"%PDF-" or "pdf" in tipo:
        return _de_pdf(conteudo)
    if conteudo[:5] == b"{\\rtf" or "rtf" in tipo:
        return _de_rtf(conteudo), "rtf"
    return _de_html(conteudo), "html"


def _de_pdf(conteudo: bytes) -> tuple[list[str], str]:
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover
        raise RuntimeError("instale pypdf para ler inteiro teor em PDF")

    leitor = PdfReader(io.BytesIO(conteudo))
    paginas = [limpar(p.extract_text() or "") for p in leitor.pages]

    uteis = [p for p in paginas if len(p) >= MIN_CARACTERES_PAGINA]
    if uteis:
        return paginas, "pdf"

    # Nenhuma página com texto: é digitalização.
    ocr = _ocr(conteudo)
    if ocr:
        return ocr, "ocr"
    log.warning("PDF sem camada de texto e sem OCR disponível (%d páginas)", len(paginas))
    return paginas, "pdf_sem_texto"


def _ocr(conteudo: bytes) -> list[str] | None:
    """OCR sob demanda. Devolve None se as ferramentas não estiverem presentes.

    Não é chamado em massa por acidente: só entra quando o PDF não tem texto.
    Ainda assim, meça — OCR é ordens de grandeza mais caro que extração.
    """
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
    except ImportError:
        return None
    try:
        imagens = convert_from_bytes(conteudo, dpi=300)
        return [limpar(pytesseract.image_to_string(im, lang="por")) for im in imagens]
    except Exception as e:  # pragma: no cover - depende de binários externos
        log.warning("OCR falhou: %s", e)
        return None


def _de_rtf(conteudo: bytes) -> list[str]:
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError:  # pragma: no cover
        raise RuntimeError("instale striprtf para ler inteiro teor em RTF")
    return _fatiar(limpar(rtf_to_text(conteudo.decode("latin-1", errors="replace"))))


def _de_html(conteudo: bytes) -> list[str]:
    try:
        from selectolax.parser import HTMLParser
    except ImportError:  # pragma: no cover
        raise RuntimeError("instale selectolax para ler inteiro teor em HTML")
    texto = HTMLParser(conteudo.decode("utf-8", errors="replace")).text(separator="\n", strip=True)
    return _fatiar(limpar(texto))


_RE_ESPACO = re.compile(r"[ \t ]+")
_RE_LINHAS = re.compile(r"\n{3,}")
# Numeração de página e carimbo de assinatura digital poluem toda busca por
# inteiro teor; saem antes da indexação.
_RE_RODAPE = re.compile(
    r"^\s*(?:f?ls?\.?\s*\d+|p[áa]g(?:ina)?\.?\s*\d+(?:\s*/\s*\d+)?|"
    r"Documento assinado digitalmente.*|Assinado eletronicamente por.*|"
    r"A autenticidade (?:deste|do) documento.*)\s*$",
    re.I | re.M,
)


def limpar(texto: str) -> str:
    t = (texto or "").replace("\r\n", "\n").replace("\r", "\n").replace("\xad", "")
    t = _RE_RODAPE.sub("", t)
    t = _RE_ESPACO.sub(" ", t)
    # Palavra hifenizada quebrada entre linhas: "responsabi-\nlidade".
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
    return _RE_LINHAS.sub("\n\n", t).strip()


def _fatiar(texto: str, tamanho: int = TAMANHO_PAGINA_HTML) -> list[str]:
    """Quebra em blocos, sempre em fim de parágrafo, para citação estável."""
    if len(texto) <= tamanho:
        return [texto] if texto else []
    paginas, atual = [], []
    contador = 0
    for par in texto.split("\n\n"):
        if contador + len(par) > tamanho and atual:
            paginas.append("\n\n".join(atual))
            atual, contador = [], 0
        atual.append(par)
        contador += len(par) + 2
    if atual:
        paginas.append("\n\n".join(atual))
    return paginas
