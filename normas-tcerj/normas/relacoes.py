"""Relações entre atos, extraídas da prosa da ementa.

Os campos estruturados da API registram a revogação e dão 82 relações. A
ementa acrescenta duas coisas que eles não têm:

1. **Alterações.** Alteração é o que mais engana num acervo de normas: o ato
   segue vigente, mas com outra redação, e nada no PDF original avisa. A
   revogação ao menos derruba o ato inteiro.

2. **Revogação tácita**, declarada em caixa alta pelo próprio Serviço:
   "TACITAMENTE REVOGADA POR OUTRAS ALTERAÇÕES NA ESTRUTURA". São 18 atos que
   os campos dão como vigentes e que a ementa desmente. Sem isso, o acervo
   afirmaria vigência onde a fonte já registrou o contrário.

SOBRE O QUE NÃO SE EXTRAI

A primeira versão desta extração puxava todo número dentro da frase e filtrava
datas por lookahead. O tiro saiu pela culatra no formato mais comum do portal —
"Deliberação nº 294/18" —, em que o lookahead rejeitava o número do ato (294,
seguido de "/18") e aceitava o fragmento do ano. Produziu relação errada em
silêncio, que é pior do que relação nenhuma.

A extração agora só reconhece o número **imediatamente após** a espécie ou o
"nº", nos dois formatos que o portal usa. Listas ("145, 129, 89 e 87") são
seguidas enquanto forem números separados por vírgula ou "e". Tudo o mais fica
de fora, de propósito: aqui o objetivo é não errar, e não maximizar a colheita.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Iterator

_ESPECIE_RX = (r"Ato[s]?\s+Normativo[s]?|Delibera(?:ção|ções)|Resolu(?:ção|ções)"
               r"|Portaria[s]?|Nota[s]?\s+T[ée]cnica[s]?")

# "Alterado pelos Atos Normativos 145, 129, 89" / "Revogada pela Deliberação nº 294/18"
_RELACAO = re.compile(
    rf"(?P<verbo>Alterad[oa]s?|Revogad[oa]s?)\s+p(?:el)?[oa]s?\s+"
    rf"(?P<especie>{_ESPECIE_RX})\s*"
    rf"(?P<numeros>(?:n?[ºo°.]?\s*\d{{1,4}}(?:\s*/\s*\d{{2,4}})?"
    rf"(?:\s*(?:,|e)\s*)?)+)",
    re.IGNORECASE,
)

# Um número de ato: opcionalmente precedido de "nº", opcionalmente seguido de
# "/ano". O ano nunca é confundido com número porque só se lê o que vem ANTES
# da barra.
_NUMERO = re.compile(r"n?[ºo°.]?\s*(\d{1,4})(?:\s*/\s*\d{2,4})?")

# Voz ativa: "Altera a Deliberação nº 286", "Altera o Regimento Interno".
#
# Sem isto o Regimento aparecia sem alteração alguma — porque quem declara a
# alteração é a ementa de QUEM ALTERA, não a do alterado. Era o caso mais
# importante do acervo escapando pela voz do verbo.
_ATIVA = re.compile(
    rf"\bAltera(?:m|r|ndo)?\s+(?:a|o|as|os|dispositivos?\s+d[eoa]s?\s*)?\s*"
    rf"(?P<alvo>Regimento\s+Interno|{_ESPECIE_RX})\s*"
    rf"(?P<numeros>(?:n?[ºo°.]?\s*\d{{1,4}}(?:\s*/\s*\d{{2,4}})?"
    rf"(?:\s*(?:,|e)\s*)?)*)",
    re.IGNORECASE,
)

# Revogação tácita: o Serviço a escreve em caixa alta, com ou sem indicar quem.
_TACITA = re.compile(r"TACITAMENTE\s+REVOGAD[OA]S?", re.IGNORECASE)

_ESPECIE = {
    "ato": "ato-normativo", "atos": "ato-normativo",
    "deliberação": "deliberacao", "deliberações": "deliberacao",
    "resolução": "resolucao", "resoluções": "resolucao",
    "portaria": "portaria", "portarias": "portaria",
    "nota": "nota-tecnica", "notas": "nota-tecnica",
}

_VERBO = {"alterad": "alterado_por", "revogad": "revogado_por"}


def extrair(ementa: str) -> Iterator[tuple[str, str, int]]:
    """(relação, espécie, número) para cada menção reconhecida na ementa."""
    if not ementa:
        return
    for m in _RELACAO.finditer(ementa):
        relacao = _VERBO.get(m.group("verbo")[:7].lower())
        especie = _ESPECIE.get(m.group("especie").split()[0].lower())
        if not relacao or not especie:
            continue
        for numero in _NUMERO.findall(m.group("numeros")):
            n = int(numero)
            if n:
                yield relacao, especie, n


def altera(ementa: str) -> Iterator[tuple[str, int | None]]:
    """(espécie-alvo, número) do que ESTE ato altera. Voz ativa.

    Número `None` significa "o Regimento Interno", sem número — quem resolve
    qual Regimento é o chamador, porque isso depende da data do ato: antes de
    fevereiro de 2023 a referência era ao regimento anterior.
    """
    if not ementa:
        return
    for m in _ATIVA.finditer(ementa):
        alvo = m.group("alvo").lower()
        if alvo.startswith("regimento"):
            yield "regimento", None
            continue
        especie = _ESPECIE.get(alvo.split()[0])
        if not especie:
            continue
        for numero in _NUMERO.findall(m.group("numeros") or ""):
            if int(numero):
                yield especie, int(numero)


def tacitamente_revogado(ementa: str) -> bool:
    return bool(ementa and _TACITA.search(ementa))


ESQUEMA = """
CREATE TABLE IF NOT EXISTS relacoes (
    ato_id     TEXT NOT NULL,   -- o ato que SOFRE a relação
    relacao    TEXT NOT NULL,   -- alterado_por | revogado_por
    outro_id   TEXT,            -- quem a provoca, quando identificável
    especie    TEXT NOT NULL,
    numero     INTEGER NOT NULL,
    origem     TEXT NOT NULL,   -- 'ementa' (prosa) ou 'campo' (metadado)
    PRIMARY KEY (ato_id, relacao, especie, numero, origem)
);
CREATE INDEX IF NOT EXISTS ix_rel_outro ON relacoes(outro_id);
CREATE INDEX IF NOT EXISTS ix_rel_ato   ON relacoes(ato_id, relacao);
"""


def minerar(conexao: sqlite3.Connection) -> dict[str, int]:
    conexao.executescript(ESQUEMA)
    try:
        conexao.execute("ALTER TABLE atos ADD COLUMN revogacao_tacita INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conexao.execute("DELETE FROM relacoes WHERE origem='ementa'")

    contagem: dict[str, int] = {"alterado_por": 0, "revogado_por": 0,
                                "tacitas": 0, "ambiguas": 0}
    for ato in conexao.execute(
        "SELECT id, ementa FROM atos WHERE ementa IS NOT NULL AND ementa <> ''"
    ).fetchall():
        if tacitamente_revogado(ato["ementa"]):
            conexao.execute("UPDATE atos SET revogacao_tacita=1 WHERE id=?",
                            (ato["id"],))
            contagem["tacitas"] += 1
        for relacao, especie, numero in extrair(ato["ementa"]):
            # A numeração recicla entre anos: sem o ano, a ementa não
            # desambigua. Nesse caso o vínculo fica sem `outro_id` — não se
            # escolhe um candidato ao acaso.
            candidatos = [r[0] for r in conexao.execute(
                "SELECT id FROM atos WHERE especie=? AND numero=?",
                (especie, numero))]
            if len(candidatos) > 1:
                contagem["ambiguas"] += 1
            conexao.execute(
                "INSERT OR REPLACE INTO relacoes"
                " (ato_id, relacao, outro_id, especie, numero, origem)"
                " VALUES (?,?,?,?,?,'ementa')",
                (ato["id"], relacao, candidatos[0] if len(candidatos) == 1 else None,
                 especie, numero))
            contagem[relacao] += 1

    # Voz ativa: quem ALTERA declara na própria ementa. A relação é gravada no
    # ato ALTERADO, que é onde o advogado vai procurá-la.
    ri = conexao.execute(
        "SELECT id, data FROM atos WHERE e_regimento=1").fetchone()
    for ato in conexao.execute(
        "SELECT id, data, ementa FROM atos WHERE ementa IS NOT NULL AND ementa <> ''"
    ).fetchall():
        for especie, numero in altera(ato["ementa"]):
            if especie == "regimento":
                # "Altera o Regimento Interno" antes de fevereiro de 2023
                # alcançava o regimento ANTERIOR, que não está identificado no
                # acervo. Vincular tudo à Deliberação 338 diria que 58 atos
                # alteram o texto atual — falso, e do tipo que se propaga.
                if not ri or not ato["data"] or ato["data"] <= ri["data"]:
                    continue
                alvo, alvo_especie, alvo_numero = ri["id"], "deliberacao", 0
            else:
                candidatos = [r[0] for r in conexao.execute(
                    "SELECT id FROM atos WHERE especie=? AND numero=?",
                    (especie, numero))]
                if len(candidatos) != 1:
                    contagem["ambiguas"] += 1
                    continue
                alvo, alvo_especie, alvo_numero = candidatos[0], especie, numero
            if alvo == ato["id"]:
                continue
            e, n_ = ato["id"].rsplit("-", 2)[0], int(ato["id"].rsplit("-", 2)[1])
            conexao.execute(
                "INSERT OR REPLACE INTO relacoes"
                " (ato_id, relacao, outro_id, especie, numero, origem)"
                " VALUES (?, 'alterado_por', ?, ?, ?, 'ementa')",
                (alvo, ato["id"], e, n_))
            contagem["alterado_por"] += 1

    conexao.execute(
        "INSERT OR REPLACE INTO relacoes"
        " (ato_id, relacao, outro_id, especie, numero, origem)"
        " SELECT revogado_id, 'revogado_por', revogador_id,"
        "        substr(revogador_id, 1, instr(revogador_id, '-') - 1), 0, 'campo'"
        " FROM revogacoes")
    conexao.commit()
    return contagem
