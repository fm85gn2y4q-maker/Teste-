"""DataJud (CNJ) — a espinha de metadados.

**O que o DataJud é:** a única via realmente oficial e estável para saber
*quais processos existem* no TJRJ, com classe, assuntos, órgão julgador e
movimentos, via Elasticsearch público.

**O que o DataJud não é:** fonte de jurisprudência. Ele não traz ementa, não
traz inteiro teor, não traz o nome das partes (a Portaria CNJ 160/2020 e o
resguardo de sigilo os excluem) e não traz a composição do julgamento.

Por isso ele não substitui os coletores do eJURIS e do eproc — ele os
**audita**. Contando pelo DataJud quantos processos com movimento de
julgamento colegiado existem numa janela, você descobre quanto da janela o
seu coletor deixou passar. É a única forma barata de responder "a minha base
está completa?" sem confiar no próprio coletor.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterator

from ..config import CFG, Config
from ..http import Cliente

log = logging.getLogger("tjrj.datajud")

# Códigos da Tabela Processual Unificada do CNJ que indicam julgamento
# colegiado de mérito. Confira contra a TPU vigente antes de tratar os
# números como definitivos.
MOV_JULGAMENTO = (193, 196, 198, 199, 202, 203, 219, 235, 236, 237, 238, 239, 240, 242)


@dataclass
class Processo:
    numero_cnj: str
    classe: str | None
    classe_codigo: int | None
    orgao_julgador: str | None
    orgao_codigo: int | None
    grau: str | None
    data_ajuizamento: str | None
    assuntos: list[dict[str, Any]]
    movimentos: list[dict[str, Any]]
    bruto: dict[str, Any]

    @property
    def datas_de_julgamento(self) -> list[str]:
        return [
            m.get("dataHora", "")[:10]
            for m in self.movimentos
            if m.get("codigo") in MOV_JULGAMENTO and m.get("dataHora")
        ]


class DataJud:
    def __init__(self, cliente: Cliente | None = None, cfg: Config = CFG):
        self.cfg = cfg
        self.cliente = cliente or Cliente(cfg)
        if not cfg.datajud_chave:
            log.warning(
                "TJRJ_DATAJUD_KEY vazia — pegue a chave pública em "
                "https://datajud-wiki.cnj.jus.br/api-publica/acesso/"
            )

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"APIKey {self.cfg.datajud_chave}",
            "Content-Type": "application/json",
        }

    def buscar(self, corpo: dict[str, Any]) -> dict[str, Any]:
        r = self.cliente.pegar(
            self.cfg.datajud_url, metodo="POST", json_corpo=corpo, headers=self._headers
        )
        if r.status == 401:
            raise PermissionError(
                "DataJud recusou a chave (401). O CNJ rotaciona a chave pública sem aviso: "
                "confira o valor atual na wiki e atualize TJRJ_DATAJUD_KEY."
            )
        return r.json()

    def contar(self, inicio: date, fim: date, *, campo: str = "dataAjuizamento") -> int:
        """Total de processos na janela. Barato: `size: 0`."""
        r = self.buscar(
            {
                "size": 0,
                "query": {
                    "range": {campo: {"gte": inicio.isoformat(), "lte": fim.isoformat()}}
                },
                "track_total_hits": True,
            }
        )
        return int(r.get("hits", {}).get("total", {}).get("value", 0))

    def varrer(
        self, inicio: date, fim: date, *, campo: str = "dataAjuizamento", pagina: int = 1000
    ) -> Iterator[Processo]:
        """Percorre a janela inteira com `search_after`.

        `search_after` em vez de `from`/`size`: o Elasticsearch corta em
        10.000 documentos por paginação comum, e é exatamente aí que uma
        varredura ingênua começa a perder processos em silêncio.
        """
        marcador: list[Any] | None = None
        while True:
            corpo: dict[str, Any] = {
                "size": pagina,
                "query": {"range": {campo: {"gte": inicio.isoformat(), "lte": fim.isoformat()}}},
                "sort": [{campo: "asc"}, {"_id": "asc"}],
            }
            if marcador:
                corpo["search_after"] = marcador

            resposta = self.buscar(corpo)
            hits = resposta.get("hits", {}).get("hits", [])
            if not hits:
                return

            for h in hits:
                yield _para_processo(h.get("_source", {}))

            marcador = hits[-1].get("sort")
            if marcador is None:
                return

    def conferir_cobertura(
        self, inicio: date, fim: date, numeros_coletados: set[str]
    ) -> "Divergencia":
        """Compara o universo do DataJud com o que os coletores trouxeram.

        Devolve o que existe no CNJ e falta na sua base. É este método que
        transforma "acho que peguei tudo" em número.
        """
        esperados: set[str] = set()
        for p in self.varrer(inicio, fim, campo="dataAjuizamento"):
            if p.datas_de_julgamento:
                esperados.add(p.numero_cnj)
        faltando = esperados - numeros_coletados
        return Divergencia(inicio, fim, len(esperados), len(numeros_coletados), sorted(faltando))


@dataclass
class Divergencia:
    inicio: date
    fim: date
    esperados: int
    coletados: int
    faltando: list[str]

    @property
    def cobertura(self) -> float:
        return 1.0 if not self.esperados else 1 - len(self.faltando) / self.esperados

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"{self.inicio}..{self.fim}: {self.cobertura:.1%} "
            f"({self.esperados - len(self.faltando)}/{self.esperados})"
        )


def _para_processo(src: dict[str, Any]) -> Processo:
    orgao = src.get("orgaoJulgador") or {}
    classe = src.get("classe") or {}
    return Processo(
        numero_cnj=src.get("numeroProcesso", ""),
        classe=classe.get("nome"),
        classe_codigo=classe.get("codigo"),
        orgao_julgador=orgao.get("nome"),
        orgao_codigo=orgao.get("codigo"),
        grau=src.get("grau"),
        data_ajuizamento=src.get("dataAjuizamento"),
        assuntos=src.get("assuntos") or [],
        movimentos=src.get("movimentos") or [],
        bruto=src,
    )
