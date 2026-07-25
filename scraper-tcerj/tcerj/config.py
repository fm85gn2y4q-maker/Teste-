"""Configuração do coletor.

O portal do TCE-RJ é uma aplicação JavaScript cujo endpoint interno não é
público nem documentado. Em vez de fixar esses detalhes no código, eles ficam
neste arquivo de configuração: o comando `descobrir` os preenche
automaticamente a partir do tráfego real do navegador.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

BASE_PADRAO = "https://www.tcerj.tc.br"

# Páginas conhecidas do Tribunal. `descobrir` visita cada uma para achar as
# chamadas de rede que alimentam as listagens.
PORTAIS_PADRAO: tuple[str, ...] = (
    "/sistema-jurisprudencia/public/consultas",
    "/cadastro-publicacoes/public/portal-jurisprudencia",
    "/consulta-processo/Acordaos",
    "/consulta-processo/PesquisaTextual/",
)


@dataclass(slots=True)
class ConfigApi:
    """Endpoint JSON descoberto, quando existir."""

    url: str | None = None
    metodo: str = "GET"
    cabecalhos: dict[str, str] = field(default_factory=dict)
    parametros: dict[str, Any] = field(default_factory=dict)
    corpo: dict[str, Any] | None = None
    # Nome do parâmetro de paginação no formato usado pelo servidor.
    campo_pagina: str = "page"
    campo_tamanho: str = "size"
    # Nome do parâmetro que carrega o termo de busca livre.
    campo_termo: str = "termo"
    primeira_pagina: int = 0
    tamanho_pagina: int = 50
    # Caminho, separado por pontos, até a lista de itens dentro da resposta
    # (ex.: "content", "dados.itens", "" para uma lista na raiz).
    caminho_itens: str = "content"
    caminho_total: str = "totalElements"


@dataclass(slots=True)
class ConfigSeletores:
    """Seletores CSS usados na coleta via navegador."""

    campo_busca: str = "input[type='search'], input[type='text']"
    botao_buscar: str = "button[type='submit']"
    item_resultado: str = "table tbody tr, .resultado, .card, li.item"
    link_detalhe: str = "a[href]"
    proxima_pagina: str = "a[rel='next'], .pagination .next, button[aria-label*='rox']"
    corpo_detalhe: str = "main, .conteudo, article, body"


@dataclass(slots=True)
class Config:
    base_url: str = BASE_PADRAO
    portais: list[str] = field(default_factory=lambda: list(PORTAIS_PADRAO))
    # "api" usa o endpoint JSON; "navegador" percorre o DOM com o Playwright.
    backend: str = "navegador"
    api: ConfigApi = field(default_factory=ConfigApi)
    seletores: ConfigSeletores = field(default_factory=ConfigSeletores)

    # Boa vizinhança: intervalo mínimo entre requisições e limite de
    # concorrência. Não aumente sem necessidade — é um servidor público.
    intervalo_seg: float = 1.5
    concorrencia: int = 2
    timeout_seg: float = 45.0
    tentativas: int = 4
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36 (pesquisa-academica; contato via repositorio)"
    )
    respeitar_robots: bool = True
    diretorio_saida: str = "dados"

    # Executável do navegador a usar no lugar do que o Playwright baixa (por
    # exemplo, um Chrome já instalado na máquina). Também pode vir da variável
    # de ambiente TCERJ_CHROMIUM.
    caminho_navegador: str | None = None

    def executavel_navegador(self) -> str | None:
        return self.caminho_navegador or os.environ.get("TCERJ_CHROMIUM") or None

    @classmethod
    def carregar(cls, caminho: str | Path | None) -> "Config":
        if caminho is None:
            return cls()
        arquivo = Path(caminho)
        if not arquivo.exists():
            raise FileNotFoundError(f"Configuração não encontrada: {arquivo}")
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        return cls.de_dict(dados)

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "Config":
        dados = dict(dados)
        api = ConfigApi(**dados.pop("api", {}) or {})
        seletores = ConfigSeletores(**dados.pop("seletores", {}) or {})
        validos = {c for c in cls.__dataclass_fields__ if c not in {"api", "seletores"}}
        desconhecidos = set(dados) - validos
        if desconhecidos:
            raise ValueError(
                f"Chaves desconhecidas na configuração: {', '.join(sorted(desconhecidos))}"
            )
        return cls(api=api, seletores=seletores, **dados)

    def salvar(self, caminho: str | Path) -> None:
        Path(caminho).write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def url_absoluta(self, caminho: str) -> str:
        if caminho.startswith(("http://", "https://")):
            return caminho
        return f"{self.base_url.rstrip('/')}/{caminho.lstrip('/')}"
