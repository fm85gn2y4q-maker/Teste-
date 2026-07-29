"""Servidor MCP do acervo TJRJ.

O desenho das ferramentas segue a mesma lógica dos seus outros acervos
(Ementário TCE-RJ, Legis Mesquita), por um motivo prático: um advogado que
já sabe consultar um deles não precisa reaprender nada, e o modelo do outro
lado escolhe melhor entre ferramentas cujo contrato ele reconhece.

A separação que mais importa é entre **ementa** e **inteiro teor**. A ementa
é a tese já destilada pelo tribunal; o voto é onde está a fundamentação. Uma
proposição que veio da ementa e uma que veio da página 27 do voto têm pesos
diferentes numa peça, e a resposta precisa dizer de qual das duas se trata —
por isso são duas ferramentas, e por isso a busca em teor devolve a página.

`cobertura_do_acervo` não é enfeite: é o que permite ao modelo distinguir
"o TJRJ não decidiu isso" de "esse período não está na base".
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..config import CFG
from ..db import conectar

LIMITE_PADRAO = 20
LIMITE_MAXIMO = 100
TRECHO = 400


def _con() -> sqlite3.Connection:
    return conectar(CFG.banco)


def _fts(consulta: str) -> str:
    """Traduz a consulta do usuário para a sintaxe do FTS5.

    Aspas viram frase exata; o resto vira AND implícito. Escapamos aspas
    soltas porque uma consulta malformada faz o FTS5 lançar erro em vez de
    devolver zero resultados — e o modelo do outro lado interpreta o erro
    como "a base não tem isso".
    """
    consulta = (consulta or "").strip()
    if not consulta:
        return '""'
    if consulta.count('"') % 2:
        consulta = consulta.replace('"', " ")
    termos = []
    for parte in consulta.replace("(", " ").replace(")", " ").split():
        if parte.upper() in ("AND", "OR", "NOT", "NEAR"):
            termos.append(parte.upper())
        elif parte.startswith('"') or parte.endswith('"'):
            termos.append(parte)
        else:
            termos.append(f'"{parte}"')
    return " ".join(termos)


def _citacao(r: sqlite3.Row) -> str:
    partes = [p for p in ("TJRJ", r["orgao_julgador"], r["classe"], r["numero_cnj"]) if p]
    if r["data_julgamento"]:
        d = r["data_julgamento"]
        partes.append(f"j. {d[8:10]}/{d[5:7]}/{d[:4]}")
    return ", ".join(partes)


def _relator(con, acordao_id: str) -> str | None:
    linha = con.execute(
        "SELECT j.nome FROM participacao p JOIN julgador j ON j.id = p.julgador_id"
        " WHERE p.acordao_id = ? AND p.papel IN ('relator_designado','relator')"
        " ORDER BY CASE p.papel WHEN 'relator_designado' THEN 0 ELSE 1 END LIMIT 1",
        (acordao_id,),
    ).fetchone()
    return linha["nome"] if linha else None


# --- ferramentas -----------------------------------------------------------


def pesquisar_jurisprudencia(
    consulta: str,
    limite: int = LIMITE_PADRAO,
    orgao_julgador: str | None = None,
    relator: str | None = None,
    data_de: str | None = None,
    data_ate: str | None = None,
) -> dict[str, Any]:
    """Pesquisa nas EMENTAS — o resumo oficial, com a tese já destilada."""
    limite = max(1, min(limite, LIMITE_MAXIMO))
    con = _con()
    sql = [
        "SELECT a.id, a.numero_cnj, a.orgao_julgador, a.classe, a.data_julgamento,",
        " a.ementa, a.paginas, a.url_fonte, bm25(ementa_fts) AS score",
        " FROM ementa_fts JOIN ementa_map m ON m.rowid = ementa_fts.rowid",
        " JOIN acordao a ON a.id = m.acordao_id",
        " WHERE ementa_fts MATCH ?",
    ]
    args: list[Any] = [_fts(consulta)]
    if orgao_julgador:
        sql.append(" AND a.orgao_julgador LIKE ?")
        args.append(f"%{orgao_julgador}%")
    if data_de:
        sql.append(" AND a.data_julgamento >= ?")
        args.append(data_de)
    if data_ate:
        sql.append(" AND a.data_julgamento <= ?")
        args.append(data_ate)
    if relator:
        sql.append(
            " AND EXISTS (SELECT 1 FROM participacao p JOIN julgador j ON j.id = p.julgador_id"
            " WHERE p.acordao_id = a.id AND p.papel LIKE 'relator%' AND j.nome_norm LIKE ?)"
        )
        from ..parse.normalize import chave_julgador

        args.append(f"%{chave_julgador(relator)}%")
    sql.append(" ORDER BY score LIMIT ?")
    args.append(limite)

    linhas = con.execute("".join(sql), args).fetchall()
    resultados = [
        {
            "id": r["id"],
            "citacao": _citacao(r),
            "numero_cnj": r["numero_cnj"],
            "orgao_julgador": r["orgao_julgador"],
            "data_julgamento": r["data_julgamento"],
            "relator": _relator(con, r["id"]),
            "ementa": r["ementa"],
            "tem_inteiro_teor": bool(r["paginas"]),
            "url": r["url_fonte"],
            "origem_da_proposicao": "ementa",
        }
        for r in linhas
    ]
    con.close()
    return {"total": len(resultados), "resultados": resultados}


def pesquisar_inteiro_teor(
    consulta: str, limite: int = LIMITE_PADRAO, orgao_julgador: str | None = None
) -> dict[str, Any]:
    """Pesquisa dentro dos VOTOS e devolve a página onde o trecho está."""
    limite = max(1, min(limite, LIMITE_MAXIMO))
    con = _con()
    sql = (
        "SELECT m.acordao_id, m.pagina, a.numero_cnj, a.orgao_julgador, a.classe,"
        " a.data_julgamento, a.url_fonte,"
        " snippet(teor_fts, 0, '«', '»', ' … ', 24) AS trecho, bm25(teor_fts) AS score"
        " FROM teor_fts JOIN teor_map m ON m.rowid = teor_fts.rowid"
        " JOIN acordao a ON a.id = m.acordao_id"
        " WHERE teor_fts MATCH ?"
    )
    args: list[Any] = [_fts(consulta)]
    if orgao_julgador:
        sql += " AND a.orgao_julgador LIKE ?"
        args.append(f"%{orgao_julgador}%")
    sql += " ORDER BY score LIMIT ?"
    args.append(limite)

    linhas = con.execute(sql, args).fetchall()
    resultados = [
        {
            "id": r["acordao_id"],
            "pagina": r["pagina"],
            "citacao": _citacao(r),
            "relator": _relator(con, r["acordao_id"]),
            "trecho": r["trecho"],
            "url": r["url_fonte"],
            "origem_da_proposicao": f"voto, p. {r['pagina']}",
        }
        for r in linhas
    ]
    con.close()
    return {"total": len(resultados), "resultados": resultados}


def obter_documento(id: str) -> dict[str, Any]:
    """Ficha completa do julgamento, com a composição do órgão julgador."""
    con = _con()
    r = con.execute("SELECT * FROM acordao WHERE id = ?", (id,)).fetchone()
    if r is None:
        con.close()
        return {"erro": "documento não encontrado", "id": id}

    composicao = [
        {
            "nome": p["nome"],
            "papel": p["papel"],
            "vencido": bool(p["vencido"]),
            "confianca": p["confianca"],
        }
        for p in con.execute(
            "SELECT j.nome, p.papel, p.vencido, p.confianca FROM participacao p"
            " JOIN julgador j ON j.id = p.julgador_id WHERE p.acordao_id = ?"
            " ORDER BY CASE p.papel WHEN 'relator_designado' THEN 0 WHEN 'relator' THEN 1"
            " WHEN 'revisor' THEN 2 WHEN 'presidente' THEN 3 ELSE 4 END, j.nome",
            (id,),
        )
    ]
    partes = [
        {"nome": p["nome"], "polo": p["polo"]}
        for p in con.execute(
            "SELECT nome, polo FROM parte WHERE acordao_id = ? AND sigilo = 0", (id,)
        )
    ]
    con.close()
    return {
        "id": r["id"],
        "citacao": _citacao(r),
        "numero_cnj": r["numero_cnj"],
        "sistema": r["sistema"],
        "orgao_julgador": r["orgao_julgador"],
        "classe": r["classe"],
        "tipo_decisao": r["tipo_decisao"],
        "data_julgamento": r["data_julgamento"],
        "data_publicacao": r["data_publicacao"],
        "ementa": r["ementa"],
        "composicao_do_julgamento": composicao,
        "partes": partes,
        "paginas_de_inteiro_teor": r["paginas"],
        "url": r["url_fonte"],
    }


def ler_paginas(id: str, pagina_inicial: int = 1, quantidade: int = 5) -> dict[str, Any]:
    """Lê o inteiro teor, página a página."""
    quantidade = max(1, min(quantidade, 20))
    con = _con()
    linhas = con.execute(
        "SELECT pagina, texto, origem FROM documento WHERE acordao_id = ?"
        " AND pagina >= ? ORDER BY pagina LIMIT ?",
        (id, pagina_inicial, quantidade),
    ).fetchall()
    total = con.execute(
        "SELECT paginas FROM acordao WHERE id = ?", (id,)
    ).fetchone()
    con.close()
    return {
        "id": id,
        "total_de_paginas": total["paginas"] if total else 0,
        "paginas": [
            {"pagina": r["pagina"], "texto": r["texto"], "origem_do_texto": r["origem"]}
            for r in linhas
        ],
    }


def entendimento_do_relator(nome: str, consulta: str | None = None, limite: int = 20) -> dict:
    """Como um desembargador específico vem decidindo determinado tema."""
    from ..parse.normalize import chave_julgador

    con = _con()
    sql = [
        "SELECT a.id, a.numero_cnj, a.orgao_julgador, a.classe, a.data_julgamento, a.ementa,",
        " p.papel, p.vencido FROM participacao p JOIN julgador j ON j.id = p.julgador_id",
        " JOIN acordao a ON a.id = p.acordao_id WHERE j.nome_norm LIKE ?",
    ]
    args: list[Any] = [f"%{chave_julgador(nome)}%"]
    if consulta:
        sql.append(
            " AND a.id IN (SELECT m.acordao_id FROM ementa_fts"
            " JOIN ementa_map m ON m.rowid = ementa_fts.rowid WHERE ementa_fts MATCH ?)"
        )
        args.append(_fts(consulta))
    sql.append(" ORDER BY a.data_julgamento DESC LIMIT ?")
    args.append(max(1, min(limite, LIMITE_MAXIMO)))

    linhas = con.execute("".join(sql), args).fetchall()
    con.close()
    return {
        "julgador": nome,
        "total": len(linhas),
        "julgados": [
            {
                "id": r["id"],
                "citacao": _citacao(r),
                "papel": r["papel"],
                "vencido": bool(r["vencido"]),
                "ementa": (r["ementa"] or "")[:TRECHO],
            }
            for r in linhas
        ],
    }


def cobertura_do_acervo() -> dict[str, Any]:
    """O que está e o que NÃO está na base. Leia antes de afirmar ausência."""
    con = _con()

    def um(sql: str, *a):
        r = con.execute(sql, a).fetchone()
        return r[0] if r else None

    por_sistema = [
        {
            "sistema": r["sistema"],
            "documentos": r["n"],
            "de": r["min_d"],
            "ate": r["max_d"],
            "com_inteiro_teor": r["com_teor"],
        }
        for r in con.execute(
            "SELECT sistema, COUNT(*) n, MIN(data_julgamento) min_d, MAX(data_julgamento) max_d,"
            " SUM(CASE WHEN paginas > 0 THEN 1 ELSE 0 END) com_teor FROM acordao GROUP BY sistema"
        )
    ]
    lacunas = [
        {"fonte": r["fonte"], "fatia": r["fatia"], "motivo": r["motivo"],
         "total_declarado": r["total_declarado"]}
        for r in con.execute(
            "SELECT fonte, fatia, motivo, total_declarado FROM lacuna"
            " ORDER BY total_declarado DESC LIMIT 50"
        )
    ]
    falhas = um("SELECT COUNT(*) FROM coleta WHERE status = 'erro'")
    sem_texto = um("SELECT COUNT(*) FROM documento WHERE origem = 'pdf_sem_texto'")
    con.close()

    return {
        "tribunal": "Tribunal de Justiça do Estado do Rio de Janeiro",
        "por_sistema": por_sistema,
        "limites_conhecidos": [
            "O acervo cobre acórdãos e decisões monocráticas publicados; não abrange "
            "decisões de primeiro grau não publicadas nem processos em segredo de justiça.",
            "Decisões do sistema eproc existem a partir de 05/02/2026; o anterior está no eJURIS, "
            "cuja inserção retroativa pelo próprio tribunal ainda é gradual.",
            "Ausência de resultado nesta base não é prova de inexistência do precedente.",
        ],
        "lacunas_registradas": lacunas,
        "fatias_com_erro": falhas,
        "documentos_sem_camada_de_texto": sem_texto,
    }


# --- compatibilidade com conectores (search/fetch) --------------------------


def search(query: str) -> dict[str, Any]:
    """Busca genérica: ementa primeiro, inteiro teor quando a ementa falha."""
    r = pesquisar_jurisprudencia(query, limite=10)
    if not r["resultados"]:
        r = pesquisar_inteiro_teor(query, limite=10)
    return r


def fetch(id: str) -> dict[str, Any]:
    return obter_documento(id)


FERRAMENTAS = (
    pesquisar_jurisprudencia,
    pesquisar_inteiro_teor,
    obter_documento,
    ler_paginas,
    entendimento_do_relator,
    cobertura_do_acervo,
    search,
    fetch,
)


def construir():
    """Monta o servidor FastMCP com as ferramentas acima."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "jurisprudencia-tjrj",
        instructions=(
            "Acervo de jurisprudência do Tribunal de Justiça do Estado do Rio de Janeiro: "
            "acórdãos e decisões monocráticas com ementa, inteiro teor paginado, órgão "
            "julgador, relator e demais julgadores.\n\n"
            "DUAS BUSCAS, PROPOSITALMENTE SEPARADAS: `pesquisar_jurisprudencia` procura nas "
            "ementas; `pesquisar_inteiro_teor` procura dentro dos votos e devolve a página. "
            "Diga sempre de onde veio a proposição — 'consta da ementa' e 'consta do voto, à "
            "p. 27' têm pesos diferentes numa peça.\n\n"
            "A busca é literal: se o resultado vier fraco ou lateral, reformule com o "
            "vocabulário que o tribunal usa, sem abandonar a pergunta original. Não conclua "
            "que o TJRJ não se pronunciou antes de tentar a busca em inteiro teor.\n\n"
            "Antes de afirmar ausência de precedente, consulte `cobertura_do_acervo` e declare "
            "os limites que afetem a resposta. Não cite nomes de ferramentas nem estrutura de "
            "URL: entregue análise e precedentes."
        ),
    )
    for f in FERRAMENTAS:
        mcp.tool()(f)
    return mcp


def main() -> None:
    construir().run()


if __name__ == "__main__":
    main()
