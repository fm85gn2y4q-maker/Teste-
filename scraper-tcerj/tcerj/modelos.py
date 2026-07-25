"""Modelos de domínio da jurisprudência do TCE-RJ."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class TipoDocumento(str, Enum):
    """Espécies documentais publicadas pelo TCE-RJ."""

    ACORDAO = "acordao"
    SUMULA = "sumula"
    ENUNCIADO = "enunciado"
    DELIBERACAO = "deliberacao"
    RESOLUCAO = "resolucao"
    DECISAO = "decisao"
    PARECER_PREVIO = "parecer_previo"
    RESPOSTA_CONSULTA = "resposta_consulta"
    VOTO = "voto"
    INDEFINIDO = "indefinido"

    @classmethod
    def de_texto(cls, valor: str | None) -> "TipoDocumento":
        """Classifica uma espécie documental a partir de rótulo livre.

        Aceita as variações de grafia que aparecem no portal ("Acórdão",
        "ACORDAOS", "Resposta a Consulta", "Parecer Prévio" etc.).
        """
        if not valor:
            return cls.INDEFINIDO

        normalizado = normalizar(valor)

        # A ordem importa: rótulos mais específicos são testados primeiro,
        # porque "parecer prévio" também casaria com um teste ingênuo de
        # "parecer" e "resposta a consulta" contém "consulta".
        regras: list[tuple[TipoDocumento, tuple[str, ...]]] = [
            (cls.PARECER_PREVIO, ("parecer previo", "pareceres previos")),
            (cls.RESPOSTA_CONSULTA, ("resposta a consulta", "resposta consulta", "consulta")),
            (cls.ACORDAO, ("acordao", "acordaos")),
            (cls.SUMULA, ("sumula", "sumulas")),
            (cls.ENUNCIADO, ("enunciado", "enunciados")),
            (cls.DELIBERACAO, ("deliberacao", "deliberacoes")),
            (cls.RESOLUCAO, ("resolucao", "resolucoes")),
            (cls.PARECER_PREVIO, ("parecer",)),
            (cls.VOTO, ("voto", "votos")),
            (cls.DECISAO, ("decisao", "decisoes")),
        ]
        for tipo, termos in regras:
            if any(termo in normalizado for termo in termos):
                return tipo
        return cls.INDEFINIDO


@dataclass(slots=True)
class Documento:
    """Um item de jurisprudência normalizado.

    `id` é derivado determinísticamente (tipo + número + ano, com queda para o
    hash da URL ou do texto) para que reexecuções do coletor não dupliquem
    registros já gravados.
    """

    tipo: TipoDocumento = TipoDocumento.INDEFINIDO
    numero: str | None = None
    ano: int | None = None
    processo: str | None = None
    relator: str | None = None
    orgao_julgador: str | None = None
    data_sessao: date | None = None
    data_publicacao: date | None = None
    ementa: str | None = None
    inteiro_teor: str | None = None
    assuntos: list[str] = field(default_factory=list)
    url: str | None = None
    url_pdf: str | None = None
    fonte: str | None = None
    coletado_em: str | None = None
    bruto: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        if self.numero and self.tipo is not TipoDocumento.INDEFINIDO:
            partes = [self.tipo.value, so_digitos_e_letras(self.numero)]
            if self.ano:
                partes.append(str(self.ano))
            return "-".join(partes)

        semente = self.url or self.inteiro_teor or self.ementa or ""
        if not semente:
            raise ValueError(
                "Documento sem número, URL ou texto: impossível gerar identificador estável"
            )
        return f"{self.tipo.value}-h{hashlib.sha1(semente.encode('utf-8')).hexdigest()[:16]}"

    @property
    def citacao(self) -> str:
        """Referência curta no formato usado em peças processuais."""
        rotulo = ROTULOS.get(self.tipo, "Documento")
        numero = self.numero or "s/n"
        base = f"TCE-RJ, {rotulo} {numero}"
        if self.ano:
            base += f"/{self.ano}"
        if self.processo:
            base += f", Processo {self.processo}"
        if self.relator:
            base += f", Rel. {self.relator}"
        if self.data_sessao:
            base += f", j. {self.data_sessao.strftime('%d/%m/%Y')}"
        return base

    def para_dict(self) -> dict[str, Any]:
        dados = asdict(self)
        dados["tipo"] = self.tipo.value
        dados["id"] = self.id
        for campo in ("data_sessao", "data_publicacao"):
            valor = dados.get(campo)
            dados[campo] = valor.isoformat() if isinstance(valor, date) else None
        return dados

    def mesclar(self, outro: "Documento") -> "Documento":
        """Completa campos vazios com os valores de `outro`, sem sobrescrever.

        Usado quando o mesmo documento aparece na listagem (metadados rasos) e
        depois na página de detalhe (inteiro teor).
        """
        for campo in self.__dataclass_fields__:
            atual = getattr(self, campo)
            novo = getattr(outro, campo)
            if novo in (None, "", [], {}):
                continue
            if campo == "tipo":
                if self.tipo is TipoDocumento.INDEFINIDO:
                    self.tipo = novo
            elif atual in (None, "", [], {}):
                setattr(self, campo, novo)
        return self


ROTULOS: dict[TipoDocumento, str] = {
    TipoDocumento.ACORDAO: "Acórdão",
    TipoDocumento.SUMULA: "Súmula",
    TipoDocumento.ENUNCIADO: "Enunciado",
    TipoDocumento.DELIBERACAO: "Deliberação",
    TipoDocumento.RESOLUCAO: "Resolução",
    TipoDocumento.DECISAO: "Decisão",
    TipoDocumento.PARECER_PREVIO: "Parecer Prévio",
    TipoDocumento.RESPOSTA_CONSULTA: "Resposta a Consulta",
    TipoDocumento.VOTO: "Voto",
    TipoDocumento.INDEFINIDO: "Documento",
}


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos e com espaços colapsados."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def so_digitos_e_letras(texto: str) -> str:
    return re.sub(r"[^0-9a-zA-Z]", "", texto)
