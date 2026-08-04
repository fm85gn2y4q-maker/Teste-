from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "pipeline"))

from agu.acervo import Acervo  # noqa: E402


def _banco() -> Path:
    do_ambiente = os.environ.get("AGU_BANCO")
    if do_ambiente:
        return Path(do_ambiente)
    return Path(os.path.expanduser(
        "~/Documents/AGU_Acervo_Consultivo/agu_consultivo.db"))


@pytest.fixture(scope="session")
def acervo() -> Acervo:
    caminho = _banco()
    if not caminho.exists():
        pytest.skip(f"acervo não construído em {caminho}")
    a = Acervo(caminho)
    yield a
    a.fechar()
