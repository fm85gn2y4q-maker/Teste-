"""Coletor da jurisprudência do Tribunal de Contas do Estado do Rio de Janeiro."""

from .config import Config
from .modelos import Documento, TipoDocumento

__all__ = ["Config", "Documento", "TipoDocumento"]
__version__ = "0.1.0"
