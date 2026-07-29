"""Planejador de varredura — o núcleo do projeto.

O problema real de "puxar toda a jurisprudência" não é fazer a requisição:
é que **nenhum buscador judicial devolve mais do que N resultados por
consulta**. Se uma janela de datas tem mais acórdãos que o teto, o excedente
não é paginado — ele simplesmente não existe para você, em silêncio. É assim
que quase toda base "completa" de jurisprudência nasce incompleta sem que o
dono perceba.

A solução é não confiar em nenhuma consulta cujo total declarado encoste no
teto. Fatie-a. Fatie por data até o dia; se um único dia ainda estourar,
fatie por faceta (órgão julgador, depois classe). Se nem assim couber,
**registre a lacuna explicitamente** — uma lacuna anotada é um problema; uma
lacuna silenciosa é uma base mentirosa.

Este módulo não fala HTTP. Recebe uma função de contagem e devolve fatias
coletáveis, o que o torna testável sem rede.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Callable, Iterator, Sequence

# Ordem de facetamento quando o dia isolado ainda estoura o teto.
FACETAS_PADRAO: tuple[str, ...] = ("orgao_julgador", "classe", "tipo_decisao")


@dataclass(frozen=True)
class Fatia:
    """Uma consulta que se acredita caber abaixo do teto do buscador."""

    inicio: date
    fim: date
    facetas: dict[str, str] = field(default_factory=dict)

    @property
    def dias(self) -> int:
        return (self.fim - self.inicio).days + 1

    def dividir(self) -> tuple["Fatia", "Fatia"] | None:
        """Parte a fatia ao meio no eixo temporal. None se já é um dia só."""
        if self.inicio >= self.fim:
            return None
        meio = self.inicio + timedelta(days=self.dias // 2 - 1)
        return (
            replace(self, fim=meio),
            replace(self, inicio=meio + timedelta(days=1)),
        )

    def com_faceta(self, chave: str, valor: str) -> "Fatia":
        return replace(self, facetas={**self.facetas, chave: valor})

    def chave(self) -> str:
        f = ",".join(f"{k}={v}" for k, v in sorted(self.facetas.items()))
        return f"{self.inicio.isoformat()}..{self.fim.isoformat()}|{f}"

    def __str__(self) -> str:  # pragma: no cover - conveniência de log
        return self.chave()


@dataclass
class Lacuna:
    """Trecho que o buscador se recusou a revelar por inteiro.

    Existe para ser lida em voz alta no relatório de cobertura. Nunca a
    engula: ela é a diferença entre "não há acórdãos" e "não consegui vê-los".
    """

    fatia: Fatia
    total_declarado: int
    teto: int
    motivo: str

    def __str__(self) -> str:  # pragma: no cover
        return f"LACUNA {self.fatia} total={self.total_declarado} teto={self.teto} ({self.motivo})"


Contador = Callable[[Fatia], int]
"""Devolve quantos resultados o buscador declara para a fatia.

Deve ser barato (a consulta de contagem, não a de conteúdo) e devolver o
total **declarado pelo buscador**, mesmo que ele seja maior que o teto.
Buscadores que não declaram total exigem a sondagem de `total_por_sondagem`.
"""


def planejar(
    inicio: date,
    fim: date,
    contar: Contador,
    teto: int,
    *,
    valores_de_faceta: Callable[[str, Fatia], Sequence[str]] | None = None,
    facetas: Sequence[str] = FACETAS_PADRAO,
    margem: float = 0.9,
    lacunas: list[Lacuna] | None = None,
) -> Iterator[Fatia]:
    """Emite fatias que cabem sob o teto, cobrindo [inicio, fim] sem sobra.

    `margem` deixa folga: uma fatia com 98% do teto é suspeita, porque o
    total declarado por esses sistemas costuma ser aproximado e porque
    documentos novos podem entrar entre o planejamento e a coleta.
    """
    limite = max(1, int(teto * margem))
    pilha: list[Fatia] = [Fatia(inicio, fim)]

    while pilha:
        fatia = pilha.pop()
        total = contar(fatia)

        if total == 0:
            continue
        if total <= limite:
            yield fatia
            continue

        partes = fatia.dividir()
        if partes is not None:
            pilha.extend(reversed(partes))
            continue

        # Um único dia acima do teto. Passa a facetar.
        proxima = _proxima_faceta(fatia, facetas)
        if proxima is None or valores_de_faceta is None:
            _registrar(
                lacunas,
                Lacuna(fatia, total, teto, "dia único acima do teto e sem faceta disponível"),
            )
            yield fatia  # coleta o que der; o teto trunca, mas a lacuna ficou anotada
            continue

        valores = list(valores_de_faceta(proxima, fatia))
        if not valores:
            _registrar(
                lacunas,
                Lacuna(fatia, total, teto, f"faceta '{proxima}' sem valores para fatiar"),
            )
            yield fatia
            continue

        pilha.extend(fatia.com_faceta(proxima, v) for v in reversed(valores))


def _proxima_faceta(fatia: Fatia, facetas: Sequence[str]) -> str | None:
    for f in facetas:
        if f not in fatia.facetas:
            return f
    return None


def _registrar(destino: list[Lacuna] | None, lacuna: Lacuna) -> None:
    if destino is not None:
        destino.append(lacuna)


def total_por_sondagem(
    fatia: Fatia,
    pedir_pagina: Callable[[Fatia, int], int],
    teto: int,
    pagina: int,
) -> int:
    """Estima o total quando o buscador não o declara.

    Pede a última página teórica: se ela vem cheia, o total encosta no teto.
    Devolve `teto + 1` nesse caso, o que basta para o planejador fatiar.
    """
    ultima = max(1, teto // pagina)
    itens = pedir_pagina(fatia, ultima)
    if itens >= pagina:
        return teto + 1
    return (ultima - 1) * pagina + itens
