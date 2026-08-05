"""Leitura do acervo normativo do TCE-RJ.

Num acervo de jurisprudência a pergunta perigosa é *de quem é este trecho*.
Aqui é outra: **isto ainda vale?** Um quarto dos atos está revogado, e o texto
do PDF revogado é idêntico em aparência ao do vigente.

Por isso toda leitura passa por `situacao`, e nenhum resultado sai sem ela.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROTULOS = {
    "deliberacao": "Deliberação",
    "resolucao": "Resolução",
    "ato-normativo": "Ato Normativo",
    "portaria": "Portaria",
    "nota-tecnica": "Nota Técnica",
    "sumula": "Súmula",
}

PORTAL = "https://www.tcerj.tc.br/cadastro-publicacoes/lista-{lista}"
LISTA = {
    "deliberacao": "deliberacao", "resolucao": "resolucao",
    "ato-normativo": "ato-normativo", "portaria": "portaria",
    "nota-tecnica": "nota-tecnica", "sumula": "sumula",
}
ARQUIVO = "https://www.tcerj.tc.br/cadastro-publicacoes-webapi/api/file/{id}"

_OPERADORES = {"and", "or", "not", "near"}
_VAZIAS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos", "e",
    "em", "entre", "essa", "esse", "esta", "este", "eh", "existe", "foi", "ha",
    "na", "nas", "no", "nos", "num", "numa", "o", "os", "ou", "para", "pela",
    "pelo", "por", "pode", "posso", "qual", "quais", "quando", "que", "quem",
    "se", "sem", "ser", "sao", "seu", "sob", "sobre", "sua", "tem", "ter",
    "um", "uma", "uns", "umas", "qualquer", "preciso", "quero", "gostaria",
}


def _sem_acento(t: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", t)
                   if not unicodedata.combining(c)).lower()


def montar_consulta(texto: str, operador: str = "AND") -> str:
    partes: list[str] = []
    for frase in re.findall(r'"([^"]+)"', texto):
        limpa = frase.replace('"', " ").strip()
        if limpa:
            partes.append(f'"{limpa}"')
    resto = re.sub(r'"[^"]*"', " ", texto)
    livres = re.findall(r"[\wÀ-ɏ]+", resto)
    uteis = [t for t in livres
             if _sem_acento(t) not in _VAZIAS and _sem_acento(t) not in _OPERADORES]
    partes.extend(f'"{t}"' for t in (uteis or livres))
    return f" {operador} ".join(partes)


@dataclass(slots=True)
class Situacao:
    """A vigência declarada pela fonte, com a proveniência de cada afirmação."""

    estado: str                    # vigente | revogado | revogado_tacitamente
    revogado_em: str | None
    revogado_por: str | None
    origem: str                    # campo | ementa
    alteracoes: list[dict[str, Any]]
    aviso: str

    def para_dict(self) -> dict[str, Any]:
        return {
            "estado": self.estado,
            "revogado_em": self.revogado_em,
            "revogado_por": self.revogado_por,
            "origem_da_informacao": self.origem,
            "alteracoes_declaradas": self.alteracoes,
            "aviso": self.aviso,
        }


class Acervo:
    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)
        if not self.caminho.exists():
            raise FileNotFoundError(
                f"Acervo não encontrado em {self.caminho}. Rode a coleta antes "
                f"(python -m normas coletar && python -m normas textos)."
            )
        self.conexao = sqlite3.connect(
            f"file:{self.caminho.as_posix()}?mode=ro", uri=True,
            check_same_thread=False)
        self.conexao.row_factory = sqlite3.Row
        self.coletado_em = (self.conexao.execute(
            "SELECT MAX(coletado_em) FROM atos").fetchone()[0] or "")[:10]

    def fechar(self) -> None:
        self.conexao.close()

    # -- situação ---------------------------------------------------------

    def situacao(self, ato_id: str) -> Situacao | None:
        a = self.conexao.execute(
            "SELECT * FROM atos WHERE id=?", (ato_id,)).fetchone()
        if not a:
            return None
        alteracoes = [
            {"por": ROTULOS.get(r["especie"], r["especie"]) + f" nº {r['numero']}",
             "id": r["outro_id"], "declarado_em": "ementa do próprio ato"}
            for r in self.conexao.execute(
                "SELECT especie, numero, outro_id FROM relacoes "
                "WHERE ato_id=? AND relacao='alterado_por' ORDER BY numero", (ato_id,))
        ]
        tacita = bool(a["revogacao_tacita"]) if "revogacao_tacita" in a.keys() else False
        revogado = a["revogado_por_numero"] or a["revogado_em"]

        if revogado:
            estado, origem = "revogado", "campo"
            por = (f"{ROTULOS.get(a['especie'], a['especie'])} nº "
                   f"{a['revogado_por_numero']}" if a["revogado_por_numero"] else None)
            aviso = ("Ato REVOGADO. Não o cite como norma em vigor. Serve para "
                     "reconstituir o regime da época dos fatos, e só.")
        elif tacita:
            estado, origem, por = "revogado_tacitamente", "ementa", None
            aviso = ("A ementa do próprio Tribunal declara este ato TACITAMENTE "
                     "REVOGADO, embora o campo estruturado não o registre. Não o "
                     "trate como vigente; confirme na fonte antes de qualquer uso.")
        else:
            estado, origem, por = "vigente", "campo", None
            aviso = ("Sem revogação registrada na fonte até a data da coleta. "
                     "Isso NÃO é certidão de vigência: ausência de registro não "
                     "prova que o ato não foi revogado ou alterado depois.")

        if alteracoes and estado == "vigente":
            aviso += (f" ATENÇÃO: a fonte declara {len(alteracoes)} alteração(ões) "
                      f"deste ato. O texto do PDF é o ORIGINAL — não há versão "
                      f"consolidada. Leia os atos alteradores antes de citar "
                      f"qualquer dispositivo.")
        return Situacao(estado, a["revogado_em"], por, origem, alteracoes, aviso)

    def revogados_por(self, ato_id: str) -> list[dict[str, Any]]:
        """O que este ato derrubou — a pergunta inversa."""
        return [
            {"id": r["id"], "citacao": _citacao(r), "ementa": (r["ementa"] or "")[:200]}
            for r in self.conexao.execute(
                "SELECT a.* FROM revogacoes v JOIN atos a ON a.id = v.revogado_id "
                "WHERE v.revogador_id=? ORDER BY a.ano, a.numero", (ato_id,))
        ]

    # -- consulta ---------------------------------------------------------

    def pesquisar(self, consulta: str, *, especie: str | None = None,
                  vigentes: bool | None = None, limite: int = 15
                  ) -> tuple[list[dict[str, Any]], bool, str]:
        for operador in ("AND", "OR"):
            expressao = montar_consulta(consulta, operador)
            if not expressao:
                return [], False, ""
            sql = ["SELECT a.*, snippet(atos_fts, 1, '', '', ' … ', 26) trecho",
                   "FROM atos_fts f JOIN atos a ON a.rowid = f.rowid",
                   "WHERE atos_fts MATCH ?"]
            par: list[Any] = [expressao]
            if especie:
                sql.append("AND a.especie=?")
                par.append(especie)
            if vigentes is True:
                sql.append("AND a.revogado_por_numero IS NULL AND a.revogado_em IS NULL")
            elif vigentes is False:
                sql.append("AND (a.revogado_por_numero IS NOT NULL"
                           " OR a.revogado_em IS NOT NULL)")
            sql.append("ORDER BY rank LIMIT ?")
            par.append(max(1, min(limite, 50)))
            achados = [self._montar(l, l["trecho"])
                       for l in self.conexao.execute(" ".join(sql), par)]
            if achados:
                return achados, operador == "OR", expressao
        return [], False, expressao

    def pesquisar_texto(self, consulta: str, *, especie: str | None = None,
                        vigentes: bool | None = None, limite: int = 12
                        ) -> tuple[list[dict[str, Any]], bool, str]:
        for operador in ("AND", "OR"):
            expressao = montar_consulta(consulta, operador)
            if not expressao:
                return [], False, ""
            sql = ["SELECT a.*, p.pagina,",
                   "  snippet(paginas_fts, 2, '\x02', '\x03', ' … ', 34) trecho",
                   "FROM paginas_fts f JOIN paginas p ON p.rowid = f.rowid",
                   "JOIN atos a ON a.id = p.ato_id",
                   "WHERE paginas_fts MATCH ?"]
            par: list[Any] = [expressao]
            if especie:
                sql.append("AND a.especie=?")
                par.append(especie)
            if vigentes is True:
                sql.append("AND a.revogado_por_numero IS NULL AND a.revogado_em IS NULL")
            elif vigentes is False:
                sql.append("AND (a.revogado_por_numero IS NOT NULL"
                           " OR a.revogado_em IS NOT NULL)")
            sql.append("ORDER BY rank LIMIT ?")
            par.append(max(1, min(limite, 30)))
            achados = []
            for l in self.conexao.execute(" ".join(sql), par):
                bruto = l["trecho"] or ""
                termos = sorted({t.lower() for t in re.findall("\x02(.*?)\x03", bruto)})
                d = self._montar(l, "")
                d |= {
                    "pagina": l["pagina"],
                    "trecho": re.sub(r"\s+", " ", bruto.replace("\x02", "")
                                     .replace("\x03", "")).strip(),
                    "termos_encontrados": termos,
                }
                achados.append(d)
            if achados:
                return achados, operador == "OR", expressao
        return [], False, expressao

    def obter(self, ato_id: str) -> dict[str, Any] | None:
        l = self.conexao.execute("SELECT * FROM atos WHERE id=?", (ato_id,)).fetchone()
        return self._montar(l, "") if l else None

    def listar(self, *, especie: str | None = None, ano: int | None = None,
               vigentes: bool | None = None, limite: int = 30) -> list[dict[str, Any]]:
        sql = ["SELECT * FROM atos WHERE 1=1"]
        par: list[Any] = []
        if especie:
            sql.append("AND especie=?")
            par.append(especie)
        if ano is not None:
            sql.append("AND ano=?")
            par.append(ano)
        if vigentes is True:
            sql.append("AND revogado_por_numero IS NULL AND revogado_em IS NULL")
        elif vigentes is False:
            sql.append("AND (revogado_por_numero IS NOT NULL OR revogado_em IS NOT NULL)")
        sql.append("ORDER BY ano DESC, numero DESC LIMIT ?")
        par.append(max(1, min(limite, 100)))
        return [self._montar(l, "") for l in self.conexao.execute(" ".join(sql), par)]

    def paginas(self, ato_id: str, inicio: int, fim: int) -> list[dict[str, Any]]:
        return [{"pagina": l["pagina"], "texto": l["texto"]}
                for l in self.conexao.execute(
                    "SELECT pagina, texto FROM paginas WHERE ato_id=? "
                    "AND pagina BETWEEN ? AND ? ORDER BY pagina",
                    (ato_id, inicio, fim))]

    # -- cobertura --------------------------------------------------------

    def cobertura(self) -> dict[str, Any]:
        especies = [
            {"especie": ROTULOS.get(l["especie"], l["especie"]),
             "chave": l["especie"], "atos": l["n"], "revogados": l["rev"],
             "com_texto": l["txt"], "periodo": f"{l['de']}–{l['ate']}"}
            for l in self.conexao.execute(
                "SELECT especie, COUNT(*) n, MIN(ano) de, MAX(ano) ate,"
                " SUM(CASE WHEN revogado_por_numero IS NOT NULL"
                "     OR revogado_em IS NOT NULL THEN 1 ELSE 0 END) rev,"
                " SUM(CASE WHEN paginas_total>0 THEN 1 ELSE 0 END) txt"
                " FROM atos GROUP BY especie ORDER BY n DESC")
        ]
        p, c = self.conexao.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(texto)),0) FROM paginas").fetchone()
        tacitas = self.conexao.execute(
            "SELECT COUNT(*) FROM atos WHERE revogacao_tacita=1").fetchone()[0]
        ri = self.conexao.execute(
            "SELECT id, numero, ano, data FROM atos WHERE e_regimento=1").fetchone()
        posteriores = self.conexao.execute(
            "SELECT numero, ano, ementa FROM atos WHERE especie='deliberacao'"
            " AND lower(ementa) LIKE '%regimento interno%' AND data > ?"
            " ORDER BY data", (ri["data"],)).fetchall() if ri else []
        return {
            "por_especie": especies,
            "atos": sum(e["atos"] for e in especies),
            "revogados": sum(e["revogados"] for e in especies),
            "paginas": p,
            "caracteres": c,
            "revogacoes_tacitas": tacitas,
            "coletado_em": self.coletado_em,
            "regimento_interno": {
                "ato": f"Deliberação nº {ri['numero']}/{ri['ano']}" if ri else None,
                "aprovado_em": ri["data"] if ri else None,
                "alterado_por": [f"Deliberação nº {a['numero']}/{a['ano']}"
                                 for a in posteriores],
                "aviso": ("O PDF do Regimento é o texto ORIGINAL aprovado pela "
                          "Deliberação acima. NÃO existe versão consolidada no "
                          "portal: as alterações posteriores são atos separados, "
                          "listados aqui. Citar um artigo sem conferi-los arrisca "
                          "reproduzir redação superada."),
            },
            "limites": [
                "A Lei Orgânica do TCE-RJ (Lei Complementar estadual nº 63/1990) "
                "NÃO está neste acervo: é lei da ALERJ, não ato do Tribunal.",
                "Nenhum ato tem texto consolidado. Todo PDF é a redação original "
                "da data de publicação; alterações são atos autônomos.",
                "A situação de vigência é a declarada pela fonte na data da "
                "coleta. Ausência de revogação registrada não é certidão de "
                "vigência.",
                "O Ato Normativo nº 1/1980 tem, no portal, o texto do Ato "
                "Normativo nº 1/1982 — erro da fonte. O texto verdadeiro do ato "
                "de 1980 não está disponível.",
            ],
        }

    # -- montagem ---------------------------------------------------------

    def _montar(self, l: sqlite3.Row, trecho: str) -> dict[str, Any]:
        s = self.situacao(l["id"])
        return {
            "id": l["id"],
            "especie": ROTULOS.get(l["especie"], l["especie"]),
            "citacao": _citacao(l),
            "numero": l["numero"],
            "ano": l["ano"],
            "data": l["data"],
            "ementa": l["ementa"],
            "trecho": re.sub(r"\s+", " ", trecho or "").strip() or None,
            "situacao": s.para_dict() if s else None,
            "url_documento": (ARQUIVO.format(id=l["arquivo_id"])
                              if l["arquivo_id"] else None),
            "url_portal": PORTAL.format(lista=LISTA.get(l["especie"], "deliberacao")),
            "paginas_total": l["paginas_total"],
        }


def _citacao(l: sqlite3.Row) -> str:
    base = f"TCE-RJ, {ROTULOS.get(l['especie'], l['especie'])} nº {l['numero']}"
    if l["ano"]:
        base += f"/{l['ano']}"
    if l["data"]:
        d, m, a = l["data"].split("-")[::-1]
        base += f", de {d}/{m}/{a}"
    return base
