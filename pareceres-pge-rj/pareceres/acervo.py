"""Acesso ao acervo de pareceres da PGE-RJ.

O banco é somente leitura: quem coleta e indexa é outro programa. Aqui só se
consulta, e cada resultado carrega o que o advogado precisa para citar — página,
seção do parecer, grau de transcrição, regime de vigência e link de conferência.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

FICHA = "https://documentacao.pge.rj.gov.br/bnportal/pt-BR/detalhes/%s"

# Fórmulas que caracterizam conclusão de fato, por oposição a mero despacho de
# aprovação de parecer alheio.
CONCLUSAO_PROPRIA = ("exposto", "conclusao", "opino", "termos")

ROTULO_SECAO = {
    "relatorio": "relatório (recontagem do que o órgão consultou)",
    "fundamentacao": "fundamentação",
    "conclusao": "conclusão",
    "indefinida": "seção não identificada",
}


def _sem_acento(texto: str) -> str:
    forma = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in forma if unicodedata.category(c) != "Mn")


def montar_consulta_fts(texto: str, operador: str = "AND") -> str:
    """Traduz o que o usuário escreveu numa expressão FTS5 válida.

    Preserva expressões entre aspas (busca literal) e liga o resto pelo
    operador. Sem isto, um apóstrofo ou um hífen viram erro de sintaxe e a
    consulta falha inteira em vez de simplesmente achar menos.
    """
    if not texto or not texto.strip():
        return ""
    termos: list[str] = []
    for pedaco in re.findall(r'"[^"]+"|\S+', texto.strip()):
        if pedaco.startswith('"') and pedaco.endswith('"') and len(pedaco) > 2:
            interno = pedaco[1:-1].replace('"', " ").strip()
            if interno:
                termos.append(f'"{interno}"')
            continue
        limpo = re.sub(r"[^0-9A-Za-zÀ-ÿ*]+", " ", pedaco).strip()
        if not limpo:
            continue
        # operadores do FTS5 escritos pelo usuário passam adiante
        if limpo.upper() in {"AND", "OR", "NOT", "NEAR"}:
            termos.append(limpo.upper())
            continue
        termos.append(f'"{limpo}"' if " " in limpo else limpo)
    if not termos:
        return ""
    saida: list[str] = []
    for i, t in enumerate(termos):
        if i and t not in {"AND", "OR", "NOT"} and termos[i - 1] not in {"AND", "OR", "NOT"}:
            saida.append(operador)
        saida.append(t)
    return " ".join(saida)


@dataclass
class Trecho:
    """Uma página que casou com a busca."""

    codigo: int
    pagina: int
    texto: str
    secao: str
    transcricao: int

    def para_dict(self) -> dict[str, Any]:
        aviso = None
        if self.transcricao >= 50:
            aviso = ("Página majoritariamente composta de transcrição de terceiro "
                     "(doutrina, jurisprudência ou parecer citado). NÃO atribua este "
                     "trecho à PGE-RJ sem ler o contexto ao redor.")
        elif self.secao == "relatorio":
            aviso = ("Trecho no relatório: é a recontagem do que o órgão consulente "
                     "afirmou, não o entendimento da Procuradoria.")
        return {
            "pagina": self.pagina,
            "trecho": self.texto,
            "secao": ROTULO_SECAO.get(self.secao, self.secao or "?"),
            "transcricao_percent": self.transcricao,
            "aviso_proveniencia": aviso,
        }


@dataclass
class Parecer:
    codigo: int
    tipo: str | None
    titulo: str | None
    data: str | None
    ano: int | None
    ementa: str | None
    assuntos: str | None
    procuradores: str | None
    setores: str | None
    orgao: str | None
    processo: str | None
    eixos: str | None
    conclusao: str | None
    conclusao_tipo: str | None
    fecho: str | None
    regime: str | None
    alerta_vigencia: str | None
    paginas: int
    tem_texto: int
    url_pdf: str | None
    trechos: list[Trecho] = field(default_factory=list)

    def para_dict(self, com_conclusao: bool = True) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.codigo,
            "especie": self.tipo,
            "citacao": self.titulo,
            "data": self.data,
            "ano": self.ano,
            "procurador": self.procuradores or None,
            "setor": self.setores or None,
            "orgao_consulente": self.orgao or None,
            "processo": self.processo or None,
            "ementa": self.ementa or None,
            "assuntos": self.assuntos or None,
            "eixos": self.eixos or None,
            "regime": self.regime,
            "paginas": self.paginas,
            "inteiro_teor_disponivel": bool(self.paginas),
            "url_inteiro_teor": self.url_pdf or None,
            "url_ficha": FICHA % self.codigo,
        }
        if self.alerta_vigencia:
            d["alerta_vigencia"] = self.alerta_vigencia
        if not self.paginas:
            d["aviso"] = ("Só ficha e ementa: o portal não publica o inteiro teor "
                          "deste documento. Não é possível conferir a fundamentação.")
        elif not self.tem_texto:
            d["aviso"] = ("Digitalização sem camada de texto: o inteiro teor existe em "
                          "imagem, mas não é pesquisável nem transcrevível.")
        if com_conclusao:
            if self.conclusao:
                propria = self.conclusao_tipo in CONCLUSAO_PROPRIA
                d["conclusao"] = self.conclusao
                d["conclusao_e_do_parecer"] = propria
                if not propria:
                    d["conclusao_observacao"] = (
                        "Não é conclusão própria: é despacho de aprovação ou de "
                        "encaminhamento, que chancela parecer alheio.")
            elif self.fecho:
                d["fecho_bruto"] = self.fecho
                d["conclusao_observacao"] = (
                    "Nenhuma fórmula de conclusão foi identificada; acima está o "
                    "fecho literal do documento, sem interpretação.")
        if self.trechos:
            d["paginas_encontradas"] = [t.para_dict() for t in self.trechos]
        return d


class Acervo:
    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)
        if not self.caminho.exists():
            raise FileNotFoundError(f"banco não encontrado: {self.caminho}")
        uri = f"file:{self.caminho.as_posix()}?mode=ro"
        self.con = sqlite3.connect(uri, uri=True, check_same_thread=False)
        self.con.row_factory = sqlite3.Row

    def fechar(self) -> None:
        self.con.close()

    # ------------------------------------------------------------------ ficha
    def _parecer(self, linha: sqlite3.Row) -> Parecer:
        return Parecer(
            codigo=linha["codigo"], tipo=linha["tipo"], titulo=linha["titulo"],
            data=linha["data"], ano=linha["ano"], ementa=linha["ementa"],
            assuntos=linha["assuntos"], procuradores=linha["procuradores"],
            setores=linha["setores"], orgao=linha["orgao"], processo=linha["processo"],
            eixos=linha["eixos"], conclusao=linha["conclusao"],
            conclusao_tipo=linha["conclusao_tipo"], fecho=linha["fecho"],
            regime=linha["regime"], alerta_vigencia=linha["alerta_vigencia"],
            paginas=linha["paginas"] or 0, tem_texto=linha["tem_texto"] or 0,
            url_pdf=linha["url_pdf"],
        )

    def obter(self, codigo: int) -> Parecer | None:
        linha = self.con.execute(
            "SELECT * FROM documentos WHERE codigo = ?", (codigo,)).fetchone()
        return self._parecer(linha) if linha else None

    def _por_codigos(self, codigos: Iterable[int]) -> dict[int, Parecer]:
        codigos = list(codigos)
        if not codigos:
            return {}
        marcas = ",".join("?" * len(codigos))
        linhas = self.con.execute(
            f"SELECT * FROM documentos WHERE codigo IN ({marcas})", codigos)
        return {l["codigo"]: self._parecer(l) for l in linhas}

    # ------------------------------------------------- busca em ficha/ementa
    def pesquisar(self, consulta: str, limite: int = 10, ano_min: int | None = None,
                  ano_max: int | None = None, regime: str | None = None,
                  operador: str = "AND", so_com_conclusao: bool = False,
                  ) -> tuple[list[Parecer], str, int]:
        expressao = montar_consulta_fts(consulta, operador)
        if not expressao:
            return [], "", 0
        alvo = f"{{titulo ementa assuntos}} : ({expressao})"
        filtros, params = [], [alvo]
        if so_com_conclusao:
            # 5.861 documentos só têm ficha: sem inteiro teor não há conclusão
            filtros.append("d.paginas > 0 AND COALESCE(d.conclusao,'') <> ''")
        if ano_min:
            filtros.append("d.ano >= ?")
            params.append(ano_min)
        if ano_max:
            filtros.append("d.ano <= ?")
            params.append(ano_max)
        if regime:
            filtros.append("d.regime LIKE ?")
            params.append(f"%{regime}%")
        onde = (" AND " + " AND ".join(filtros)) if filtros else ""
        total = self.con.execute(
            f"""SELECT COUNT(*) FROM busca b JOIN documentos d ON d.codigo = b.codigo
                WHERE busca MATCH ?{onde}""", params).fetchone()[0]
        linhas = self.con.execute(
            f"""SELECT d.* FROM busca b JOIN documentos d ON d.codigo = b.codigo
                WHERE busca MATCH ?{onde}
                ORDER BY bm25(busca, 0.0, 6.0, 8.0, 4.0), d.ano DESC
                LIMIT ?""", params + [limite])
        return [self._parecer(l) for l in linhas], expressao, total

    # ------------------------------------------------- busca por página
    def pesquisar_paginas(self, consulta: str, limite: int = 8,
                          paginas_por_doc: int = 3, ano_min: int | None = None,
                          ano_max: int | None = None, so_fundamentacao: bool = False,
                          operador: str = "AND") -> tuple[list[Parecer], str, int]:
        expressao = montar_consulta_fts(consulta, operador)
        if not expressao:
            return [], "", 0
        filtros, params = [], [expressao]
        if ano_min:
            filtros.append("d.ano >= ?")
            params.append(ano_min)
        if ano_max:
            filtros.append("d.ano <= ?")
            params.append(ano_max)
        if so_fundamentacao:
            filtros.append("COALESCE(p.secao,'') IN ('fundamentacao','conclusao')")
        onde = (" AND " + " AND ".join(filtros)) if filtros else ""
        total = self.con.execute(
            f"""SELECT COUNT(DISTINCT f.codigo) FROM paginas_fts f
                JOIN documentos d ON d.codigo = f.codigo
                LEFT JOIN paginas p ON p.codigo = f.codigo AND p.pagina = f.pagina
                WHERE paginas_fts MATCH ?{onde}""", params).fetchone()[0]
        linhas = self.con.execute(
            f"""SELECT f.codigo, f.pagina,
                       snippet(paginas_fts, 2, '«', '»', ' … ', 26) AS trecho,
                       COALESCE(p.secao,'indefinida') AS secao,
                       COALESCE(p.transcricao,0) AS transcricao,
                       bm25(paginas_fts) AS score
                FROM paginas_fts f
                JOIN documentos d ON d.codigo = f.codigo
                LEFT JOIN paginas p ON p.codigo = f.codigo AND p.pagina = f.pagina
                WHERE paginas_fts MATCH ?{onde}
                ORDER BY score LIMIT ?""", params + [limite * paginas_por_doc * 3])
        por_doc: dict[int, list[Trecho]] = {}
        ordem: list[int] = []
        for l in linhas:
            lista = por_doc.setdefault(l["codigo"], [])
            if l["codigo"] not in ordem:
                ordem.append(l["codigo"])
            if len(lista) < paginas_por_doc:
                lista.append(Trecho(l["codigo"], l["pagina"], " ".join(l["trecho"].split()),
                                    l["secao"], l["transcricao"]))
            if len(ordem) >= limite and all(len(por_doc[c]) >= paginas_por_doc for c in ordem):
                break
        fichas = self._por_codigos(ordem[:limite])
        saida = []
        for cod in ordem[:limite]:
            p = fichas.get(cod)
            if p:
                p.trechos = por_doc[cod]
                saida.append(p)
        return saida, expressao, total

    def paginas_do_documento(self, codigo: int, inicio: int, quantidade: int = 3,
                             ) -> list[dict[str, Any]]:
        fim = inicio + max(1, min(quantidade, 10)) - 1
        linhas = self.con.execute(
            """SELECT f.pagina, f.texto, COALESCE(p.secao,'indefinida') AS secao,
                      COALESCE(p.transcricao,0) AS transcricao
               FROM paginas_fts f
               LEFT JOIN paginas p ON p.codigo = f.codigo AND p.pagina = f.pagina
               WHERE f.codigo = ? AND f.pagina BETWEEN ? AND ?
               ORDER BY f.pagina""", (codigo, inicio, fim))
        saida = []
        for l in linhas:
            t = Trecho(codigo, l["pagina"], (l["texto"] or "").strip(), l["secao"], l["transcricao"])
            d = t.para_dict()
            d["texto"] = d.pop("trecho")
            saida.append(d)
        return saida

    # ------------------------------------------------------------- tesauro
    def sinonimos(self, termo: str) -> list[dict[str, Any]]:
        # A comparação tem de ignorar acento dos DOIS lados: as variantes estão
        # gravadas acentuadas ("organização social") e o termo chega sem acento.
        # Comparar só o lado da consulta fazia o tesauro não achar nada.
        chave = _sem_acento(termo).lower()
        conceitos = []
        for conceito, variante in self.con.execute(
                "SELECT conceito, variante FROM sinonimos"):
            if chave in _sem_acento(conceito).lower() or chave in _sem_acento(variante).lower():
                if conceito not in conceitos:
                    conceitos.append(conceito)
        saida = []
        for c in conceitos:
            variantes = [dict(variante=r["variante"], documentos=r["documentos"],
                              paginas=r["paginas"])
                         for r in self.con.execute(
                             """SELECT variante, documentos, paginas FROM sinonimos
                                WHERE conceito = ? ORDER BY documentos DESC""", (c,))]
            saida.append({"conceito": c, "variantes": variantes,
                          "soma_documentos": sum(v["documentos"] for v in variantes)})
        return saida

    # ------------------------------------------------------------- citações
    def quem_citou(self, referencia: str, limite: int = 25) -> dict[str, Any]:
        chave = f"%{referencia.strip()}%"
        refs = self.con.execute(
            """SELECT referencia, especie, COUNT(DISTINCT codigo) AS docs,
                      SUM(ocorrencias) AS cit
               FROM citacoes WHERE referencia LIKE ?
               GROUP BY referencia, especie ORDER BY docs DESC LIMIT 8""", (chave,)).fetchall()
        if not refs:
            return {"referencia": referencia, "encontrado": False, "documentos": []}
        principal = refs[0]
        quals = [dict(qualificador=r["qualificador"] or "(sem)", documentos=r["docs"])
                 for r in self.con.execute(
                     """SELECT qualificador, COUNT(DISTINCT codigo) AS docs FROM citacoes
                        WHERE referencia = ? GROUP BY 1 ORDER BY 2 DESC""",
                     (principal["referencia"],))]
        linhas = self.con.execute(
            """SELECT d.* FROM citacoes c JOIN documentos d ON d.codigo = c.codigo
               WHERE c.referencia = ?
               -- do mais RECENTE para o mais antigo: esta é a ferramenta de
               -- conferir o que aconteceu com a norma, e o que aconteceu por
               -- último é o que decide. Ordenar por frequência escondia o
               -- parecer de 2023 que declarou a inconstitucionalidade.
               ORDER BY d.ano DESC, c.ocorrencias DESC LIMIT ?""",
            (principal["referencia"], limite))
        return {
            "referencia": principal["referencia"],
            "encontrado": True,
            "especie": principal["especie"],
            "documentos_que_citam": principal["docs"],
            "ocorrencias": principal["cit"],
            "qualificadores": quals,
            "outras_referencias_parecidas": [
                dict(referencia=r["referencia"], documentos=r["docs"]) for r in refs[1:]],
            "documentos": [self._parecer(l).para_dict(com_conclusao=False) for l in linhas],
        }

    # ------------------------------------------------------------ listagem
    def listar(self, ano: int | None = None, procurador: str | None = None,
               orgao: str | None = None, eixo: str | None = None,
               regime: str | None = None, limite: int = 30) -> list[Parecer]:
        filtros, params = [], []
        for campo, valor in (("ano", ano), ("procuradores", procurador),
                             ("orgao", orgao), ("eixos", eixo), ("regime", regime)):
            if valor is None:
                continue
            if campo == "ano":
                filtros.append("ano = ?")
                params.append(valor)
            else:
                filtros.append(f"{campo} LIKE ?")
                params.append(f"%{valor}%")
        onde = ("WHERE " + " AND ".join(filtros)) if filtros else ""
        linhas = self.con.execute(
            f"SELECT * FROM documentos {onde} ORDER BY ano DESC, codigo DESC LIMIT ?",
            params + [limite])
        return [self._parecer(l) for l in linhas]

    # ------------------------------------------------------------ cobertura
    def cobertura(self) -> dict[str, Any]:
        base = {r["chave"]: r["valor"] for r in
                self.con.execute("SELECT chave, valor FROM cobertura")}
        regimes = {r[0]: r[1] for r in self.con.execute(
            "SELECT regime, COUNT(*) FROM documentos WHERE paginas > 0 GROUP BY 1")}
        eixos: dict[str, int] = {}
        for (e,) in self.con.execute("SELECT eixos FROM documentos WHERE eixos <> ''"):
            for parte in e.split("; "):
                eixos[parte] = eixos.get(parte, 0) + 1
        base["regimes_entre_os_com_inteiro_teor"] = regimes
        base["eixos_tematicos"] = dict(sorted(eixos.items(), key=lambda x: -x[1]))
        return base
