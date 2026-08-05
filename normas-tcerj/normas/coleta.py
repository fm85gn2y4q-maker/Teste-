"""Coleta dos atos normativos do TCE-RJ.

O portal de Normas e Publicações expõe uma API REST limpa, e ela entrega duas
coisas que raramente vêm de graça:

1. O **grafo de revogação**, dito pelo próprio Tribunal. Cada ato declara por
   quem foi revogado (`revogadaPorId`, `dataRevogacao`) e o que ele revogou
   (`revogadas`). Num acervo de normas a vigência é o risco central, e aqui ela
   é metadado oficial — não inferência sobre o texto.

2. O PDF de cada ato, por `arquivoId`, em `file/{id}`.

Sobre esse segundo ponto houve uma tentação e um erro, que ficam registrados
porque o erro é silencioso e voltaria.

O endpoint `{Especie}/arquivos` devolve um ZIP com TODOS os documentos da
espécie — seis requisições no lugar de 945, e muito mais educado com um
servidor público. Mas os arquivos vêm nomeados só pelo número (`002_ato.pdf`),
e **o número não identifica o ato**: a numeração recicla a cada ano. Medido no
portal: as 26 portarias usam 11 números; o Ato Normativo nº 2 aparece em quatro
arquivos distintos. Casar por número sobrescreve, e o texto acaba pendurado no
ato do ano errado — sem erro, sem aviso, e indistinguível de acerto.

Por isso a coleta baixa um arquivo por vez, por `arquivoId`, que é único. Custa
24 minutos em vez de 30 segundos. É o preço de o texto pertencer ao ato certo.
"""

from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from typing import Any, Iterator

BASE = "https://www.tcerj.tc.br/cadastro-publicacoes-webapi/api/"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36 (pesquisa-academica; contato via repositorio)"
)

# As seis espécies do portal, com o rótulo que o advogado reconhece.
#
# Súmula fica de fora da coleta de PDF de propósito: ela não tem documento
# próprio — o enunciado vem inteiro no JSON, e é o texto que vale.
ESPECIES = {
    "deliberacao": "Deliberação",
    "resolucao": "Resolução",
    "ato-normativo": "Ato Normativo",
    "portaria": "Portaria",
    "nota-tecnica": "Nota Técnica",
    "sumula": "Súmula",
}

# Nome do recurso na API para cada espécie.
RECURSO = {
    "deliberacao": "Deliberacao",
    "resolucao": "Resolucao",
    "ato-normativo": "AtoNormativo",
    "portaria": "Portaria",
    "nota-tecnica": "NotaTecnica",
    "sumula": "Sumula",
}

INTERVALO_SEG = 1.5


@dataclass(slots=True)
class Ato:
    especie: str
    numero: int
    ano: int
    titulo: str
    ementa: str
    data: str | None
    arquivo_id: int | None
    # Vigência declarada pela fonte.
    revogado_por_numero: int | None = None
    revogado_por_id: int | None = None
    revogado_em: str | None = None
    texto_revogacao: str = ""
    # O que este ato revogou: pares (espécie, número).
    revogou: list[tuple[str, int]] = field(default_factory=list)
    # Deliberação 338/2023 é a que aprova o Regimento Interno.
    e_regimento: bool = False
    bruto: str = ""

    @property
    def id(self) -> str:
        return f"{self.especie}-{self.numero}-{self.ano}"

    @property
    def revogado(self) -> bool:
        return self.revogado_por_id is not None

    @property
    def citacao(self) -> str:
        base = f"TCE-RJ, {ESPECIES.get(self.especie, self.especie)} nº {self.numero}"
        if self.ano:
            base += f"/{self.ano}"
        return base


class Cliente:
    """Cliente mínimo, com o intervalo de cortesia entre requisições."""

    def __init__(self, intervalo: float = INTERVALO_SEG, tentativas: int = 4) -> None:
        self.intervalo = intervalo
        self.tentativas = tentativas
        self._ultimo = 0.0

    def obter(self, url: str) -> bytes:
        espera = self.intervalo - (time.monotonic() - self._ultimo)
        if espera > 0:
            time.sleep(espera)
        erro: Exception | None = None
        for tentativa in range(1, self.tentativas + 1):
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": USER_AGENT,
                                  "Accept": "application/json, */*"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    self._ultimo = time.monotonic()
                    return r.read()
            except urllib.error.HTTPError as e:
                # 4xx que não seja 429 não melhora com repetição.
                if e.code != 429 and 400 <= e.code < 500:
                    raise
                erro = e
            except Exception as e:  # noqa: BLE001 — rede é imprevisível
                erro = e
            if tentativa < self.tentativas:
                time.sleep(2 ** tentativa)
        raise RuntimeError(f"falha em {url}: {erro}")

    def json(self, url: str) -> Any:
        return json.loads(self.obter(url))


def _ano(texto: str | None) -> int:
    try:
        return int(str(texto)[:4])
    except (TypeError, ValueError):
        return 0


def _numero(valor: Any) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return 0


def _sem_data(valor: str | None) -> str | None:
    """A API usa 0001-01-01 para 'não revogado'. Isso não é uma data."""
    if not valor or valor.startswith("0001-01-01"):
        return None
    return valor[:10]


def _da_sumula(registro: dict) -> Ato:
    """Súmula tem esquema próprio: o enunciado é o texto, e não há PDF."""
    numero = _numero(registro.get("numero"))
    criacao = registro.get("criacao")
    return Ato(
        especie="sumula", numero=numero, ano=_ano(criacao),
        titulo=f"Súmula nº {numero}",
        ementa=(registro.get("enunciado") or registro.get("ementa") or "").strip(),
        data=_sem_data(criacao), arquivo_id=None,
        revogado_em=_sem_data(registro.get("cancelamento")),
        revogado_por_id=1 if registro.get("cancelado") else None,
        texto_revogacao="cancelada" if registro.get("cancelado") else "",
        bruto=json.dumps(registro, ensure_ascii=False),
    )


def _do_registro(especie: str, registro: dict) -> Ato:
    if especie == "sumula":
        return _da_sumula(registro)
    data = registro.get("data")
    return Ato(
        especie=especie,
        numero=_numero(registro.get("numero")),
        ano=_ano(data),
        titulo=(registro.get("nome") or registro.get("titulo") or "").strip(),
        ementa=(registro.get("descricao") or registro.get("objeto") or "").strip(),
        data=_sem_data(data),
        arquivo_id=registro.get("arquivoId"),
        revogado_por_numero=_numero(registro.get("numeroRevogacao")) or None,
        revogado_por_id=registro.get("revogadaPorId"),
        revogado_em=_sem_data(registro.get("dataRevogacao")),
        texto_revogacao=(registro.get("textoRevogacao") or "").strip(),
        revogou=[(especie, _numero(r.get("numero")))
                 for r in registro.get("revogadas") or []],
        e_regimento=bool(registro.get("regimentoInterno")),
        bruto=json.dumps(registro, ensure_ascii=False),
    )


def listar(cliente: Cliente, especie: str) -> list[Ato]:
    """Metadados de todos os atos de uma espécie, com o grafo de revogação."""
    registros = cliente.json(BASE + RECURSO[especie])
    return [_do_registro(especie, r) for r in registros]


def baixar_pdf(cliente: Cliente, arquivo_id: int) -> bytes:
    """O PDF de UM ato, pelo identificador de arquivo.

    Único caminho que garante que o texto pertence ao ato: `arquivoId` é chave
    do arquivo, enquanto o número do ato se repete entre anos.
    """
    dados = cliente.obter(f"{BASE}file/{arquivo_id}")
    if not dados.startswith(b"%PDF"):
        raise ValueError(f"resposta não é PDF ({dados[:16]!r})")
    return dados
