"""Contrato comum dos coletores.

Cada sistema do TJRJ (eJURIS legado e eproc) tem HTML próprio, mas o resto
do projeto não deveria saber disso. Todo coletor entrega as mesmas três
operações — contar, listar, buscar o teor — e o planejador, o pipeline e o
MCP trabalham só contra este contrato.

É também aqui que fica a fronteira honesta do projeto: `contar` e `listar`
dependem de seletores de HTML que **precisam ser calibrados contra o site
real** (ver docs/CALIBRACAO.md). O restante do sistema é verificável offline;
esta camada, não.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterator, Protocol

from .planner import Fatia


@dataclass
class Referencia:
    """O bastante para reencontrar e baixar um documento."""

    id_externo: str
    sistema: str
    url: str | None = None
    numero_cnj: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResultadoBusca:
    """Uma linha da lista de resultados — o que a busca devolve sem abrir."""

    referencia: Referencia
    numero_cnj: str | None = None
    numero_origem: str | None = None
    orgao_julgador: str | None = None
    classe: str | None = None
    relator: str | None = None
    tipo_decisao: str | None = None
    data_julgamento: date | None = None
    data_publicacao: date | None = None
    ementa: str | None = None
    url_fonte: str | None = None
    bruto: dict[str, Any] = field(default_factory=dict)


@dataclass
class Teor:
    """O inteiro teor já paginado."""

    referencia: Referencia
    paginas: list[str]
    origem: str  # pdf | html | rtf | ocr
    url: str | None = None

    @property
    def texto(self) -> str:
        return "\n\n".join(self.paginas)


class Coletor(Protocol):
    nome: str

    def contar(self, fatia: Fatia) -> int:
        """Total declarado pelo buscador para a fatia (pode exceder o teto)."""
        ...

    def listar(self, fatia: Fatia) -> Iterator[ResultadoBusca]:
        """Percorre todas as páginas de resultado da fatia."""
        ...

    def obter_teor(self, ref: Referencia) -> Teor | None:
        """Baixa e pagina o inteiro teor. None quando indisponível."""
        ...

    def valores_de_faceta(self, chave: str, fatia: Fatia) -> list[str]:
        """Valores possíveis para fatiar quando o dia isolado estoura o teto."""
        ...


class NaoCalibrado(RuntimeError):
    """Levantado quando um seletor ainda não foi confirmado contra o site.

    Falhar alto é proposital. Um coletor que devolve lista vazia porque o
    seletor mudou é indistinguível de um dia sem julgamentos — e é assim que
    meses de lacuna entram na base sem ninguém notar.
    """

    def __init__(self, o_que: str, dica: str = ""):
        super().__init__(
            f"{o_que} não calibrado. Rode `python -m tjrj.tools.calibrar` e preencha "
            f"o seletor em crawl/. {dica}".strip()
        )
