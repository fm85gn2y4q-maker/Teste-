"""Configuração central. Tudo que muda de máquina para máquina vive aqui."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RAIZ = Path(os.environ.get("TJRJ_HOME", Path(__file__).resolve().parents[2]))


def _p(env: str, padrao: Path) -> Path:
    return Path(os.environ.get(env, padrao)).expanduser()


# Mutável de propósito: a configuração é ajustada em tempo de execução pela
# CLI e apontada para um banco temporário nos testes.
@dataclass
class Config:
    # --- armazenamento -------------------------------------------------
    dados: Path = field(default_factory=lambda: _p("TJRJ_DADOS", RAIZ / "dados"))
    banco: Path = field(default_factory=lambda: _p("TJRJ_BANCO", RAIZ / "dados" / "acervo.db"))
    # Cache do HTML/PDF cru. É o ativo mais valioso do projeto: permite
    # reprocessar o parsing inteiro sem tocar de novo no tribunal.
    cache: Path = field(default_factory=lambda: _p("TJRJ_CACHE", RAIZ / "dados" / "cru"))

    # --- ritmo de coleta -----------------------------------------------
    # Coleta educada: uma conexão, intervalo fixo entre requisições.
    # Não aumente sem necessidade — o custo de ser bloqueado é semanas.
    req_por_segundo: float = float(os.environ.get("TJRJ_RPS", "0.5"))
    concorrencia: int = int(os.environ.get("TJRJ_CONCORRENCIA", "1"))
    timeout_s: float = float(os.environ.get("TJRJ_TIMEOUT", "60"))
    tentativas: int = int(os.environ.get("TJRJ_TENTATIVAS", "5"))
    user_agent: str = os.environ.get(
        "TJRJ_UA",
        # Identifique-se. Um coletor anônimo é indistinguível de um ataque.
        "pesquisa-juridica-tjrj/0.1 (coleta academica; contato: {email})".format(
            email=os.environ.get("TJRJ_CONTATO", "defina TJRJ_CONTATO")
        ),
    )

    # --- fontes ---------------------------------------------------------
    ejuris_base: str = os.environ.get("TJRJ_EJURIS", "https://www3.tjrj.jus.br/ejuris/")
    eproc_base: str = os.environ.get("TJRJ_EPROC", "https://eproc1g-cp.tjrj.jus.br/eproc/")
    eproc_2g_base: str = os.environ.get("TJRJ_EPROC2G", "https://eproc2g-cp.tjrj.jus.br/eproc/")
    djerj_base: str = os.environ.get("TJRJ_DJERJ", "https://www3.tjrj.jus.br/consultadje/")
    datajud_url: str = os.environ.get(
        "TJRJ_DATAJUD", "https://api-publica.datajud.cnj.jus.br/api_publica_tjrj/_search"
    )
    # Chave pública divulgada pelo CNJ. O CNJ a rotaciona sem aviso: se vier
    # 401, confira em https://datajud-wiki.cnj.jus.br/api-publica/acesso/
    datajud_chave: str = os.environ.get("TJRJ_DATAJUD_KEY", "")

    # --- janela histórica ------------------------------------------------
    inicio_historico: date = date.fromisoformat(os.environ.get("TJRJ_INICIO", "1998-01-01"))
    # Corte declarado pelo TJRJ: o eproc só guarda decisões incorporadas a
    # partir de 05/02/2026; antes disso, tudo é eJURIS.
    corte_eproc: date = date.fromisoformat(os.environ.get("TJRJ_CORTE_EPROC", "2026-02-05"))

    # --- limites do buscador ---------------------------------------------
    # Todo buscador judicial corta o resultado em N. O coletor precisa saber
    # esse N para fatiar as janelas até caber. Ajuste na calibração.
    teto_resultados: int = int(os.environ.get("TJRJ_TETO", "1000"))
    pagina_tamanho: int = int(os.environ.get("TJRJ_PAGINA", "50"))

    def preparar(self) -> "Config":
        self.dados.mkdir(parents=True, exist_ok=True)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.banco.parent.mkdir(parents=True, exist_ok=True)
        return self


CFG = Config().preparar()
