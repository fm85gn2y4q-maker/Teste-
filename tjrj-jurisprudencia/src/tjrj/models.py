"""Identidade e deduplicação dos acórdãos.

O mesmo acórdão aparece mais de uma vez: em duas fatias que se tocam, na
republicação por erro material, no eJURIS e de novo no eproc quando o
processo migra, e nos embargos de declaração que republicam o texto inteiro.
Sem uma identidade estável, o acervo incha e as agregações por relator ou por
câmara passam a contar o mesmo julgamento várias vezes.

A identidade é derivada do conteúdo — não de um id do tribunal, que muda de
sistema para sistema:

    id = sha1(numero_cnj | data_julgamento | orgao_normalizado | tipo)

E o `hash_teor` (do texto normalizado) resolve o caso que o id não pega: dois
registros com metadados ligeiramente diferentes e exatamente o mesmo teor.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date

from .parse.normalize import chave_orgao, numero_cnj as parse_cnj

_RE_ESPACO = re.compile(r"\s+")


def id_acordao(
    numero: str | None,
    data_julgamento: date | str | None,
    orgao: str | None,
    tipo: str | None = "acordao",
    *,
    fallback: str | None = None,
) -> str:
    """Identidade estável do julgamento."""
    num = parse_cnj(numero or "") or (numero or "").strip() or (fallback or "")
    data = data_julgamento.isoformat() if isinstance(data_julgamento, date) else (data_julgamento or "")
    base = "|".join([num, str(data)[:10], chave_orgao(orgao or ""), (tipo or "acordao")])
    if not num and not fallback:
        # Sem número e sem âncora, o hash colidiria entre julgamentos
        # distintos do mesmo dia e órgão. Melhor falhar do que fundir.
        raise ValueError("id_acordao exige número do processo ou um fallback único")
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def hash_texto(texto: str | None) -> str:
    """Hash do texto normalizado — imune a espaçamento e caixa."""
    t = _RE_ESPACO.sub(" ", (texto or "").strip().lower())
    return hashlib.sha1(t.encode("utf-8")).hexdigest()


@dataclass
class Acordao:
    id: str
    sistema: str
    numero_cnj: str | None = None
    numero_origem: str | None = None
    grau: str | None = None
    orgao_julgador: str | None = None
    classe: str | None = None
    tipo_decisao: str = "acordao"
    data_julgamento: str | None = None
    data_publicacao: str | None = None
    ementa: str | None = None
    dispositivo: str | None = None
    segredo_justica: bool = False
    url_fonte: str | None = None
    hash_ementa: str | None = None
    hash_teor: str | None = None
    paginas: int = 0
    assuntos: list[dict] = field(default_factory=list)

    @classmethod
    def de_resultado(cls, r, sistema: str) -> "Acordao":
        """Constrói a partir de um `ResultadoBusca` de qualquer coletor."""
        num = r.numero_cnj or (parse_cnj(r.numero_origem or "") if r.numero_origem else None)
        ident = id_acordao(
            num,
            r.data_julgamento,
            r.orgao_julgador,
            r.tipo_decisao or "acordao",
            fallback=r.referencia.id_externo,
        )
        return cls(
            id=ident,
            sistema=sistema,
            numero_cnj=num,
            numero_origem=r.numero_origem,
            orgao_julgador=r.orgao_julgador,
            classe=r.classe,
            tipo_decisao=r.tipo_decisao or "acordao",
            data_julgamento=r.data_julgamento.isoformat() if r.data_julgamento else None,
            data_publicacao=r.data_publicacao.isoformat() if r.data_publicacao else None,
            ementa=r.ementa,
            url_fonte=r.url_fonte,
            hash_ementa=hash_texto(r.ementa),
        )


def preferir(a: Acordao, b: Acordao) -> Acordao:
    """Decide qual das duas versões do mesmo acórdão fica.

    Critério, em ordem: quem tem inteiro teor; quem tem mais páginas; quem
    tem ementa maior; e, empatado tudo, o eproc — que é a base viva.
    """
    for chave in (lambda x: bool(x.hash_teor), lambda x: x.paginas, lambda x: len(x.ementa or "")):
        if chave(a) != chave(b):
            return a if chave(a) > chave(b) else b
    if a.sistema != b.sistema:
        return a if a.sistema == "eproc" else b
    return a
