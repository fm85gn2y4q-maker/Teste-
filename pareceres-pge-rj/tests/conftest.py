"""Configuração comum dos testes.

Os módulos do `pipeline/` não formam um pacote — são scripts executáveis, e é
assim que rodam. Para testá-los, o diretório entra no caminho de importação.
"""

import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "pipeline"))

BANCO = Path(os.environ.get(
    "PARECERES_BANCO",
    os.path.expanduser("~/Documents/PGE-RJ_Pareceres_Contratacoes/pge_rj_pareceres.db")))


@pytest.fixture(scope="session")
def acervo():
    """O acervo real. Os testes que dependem dele são pulados se o banco não
    estiver na máquina — ele é artefato de dados, não vai para o repositório."""
    if not BANCO.exists():
        pytest.skip(f"acervo não encontrado em {BANCO}")
    from pareceres.acervo import Acervo
    a = Acervo(BANCO)
    yield a
    a.fechar()


@pytest.fixture(scope="session")
def servidor():
    if not BANCO.exists():
        pytest.skip(f"acervo não encontrado em {BANCO}")
    from pareceres.servidor import construir
    return construir(str(BANCO))


def corpo(*trechos, enchimento=400):
    """Monta um documento longo o bastante para a extração de conclusão, que
    ignora textos com menos de 400 caracteres e só olha a metade final."""
    return ("Fundamentação jurídica do parecer. " * enchimento) + " ".join(trechos)
