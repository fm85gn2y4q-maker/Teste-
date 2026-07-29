"""Orquestração da coleta: planejar → listar → baixar teor → gravar.

Duas propriedades importam mais que velocidade, porque a varredura histórica
do TJRJ leva semanas:

* **Retomável.** Cada fatia concluída vira uma linha em `coleta`. Reiniciar
  o processo pula o que já terminou. Uma coleta que precise recomeçar do
  zero a cada queda nunca chega ao fim.
* **Idempotente.** Rodar duas vezes a mesma fatia não duplica nem apaga
  nada: o upsert é por `id` de conteúdo e o teor só é rebaixado se o novo
  for melhor (ver `models.preferir`).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Iterable

from ..config import CFG, Config
from ..crawl.base import Coletor
from ..crawl.planner import Lacuna, planejar
from ..db import (
    conectar,
    dump_json,
    indexar_ementa,
    indexar_paginas,
    migrar,
    registrar_lacuna,
    transacao,
)
from ..models import Acordao, hash_texto
from ..parse.composicao import extrair as extrair_composicao
from ..parse.normalize import chave_julgador, chave_orgao, nome_canonico

log = logging.getLogger("tjrj.ingest")


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def coletar(
    coletor: Coletor,
    inicio: date,
    fim: date,
    *,
    cfg: Config = CFG,
    com_teor: bool = True,
    retomar: bool = True,
) -> dict[str, int]:
    """Varre o período inteiro para um coletor. Devolve um resumo."""
    con = conectar(cfg.banco)
    migrar(con)

    feitas = _fatias_concluidas(con, coletor.nome) if retomar else set()
    lacunas: list[Lacuna] = []
    resumo = {"fatias": 0, "puladas": 0, "encontrados": 0, "novos": 0, "com_teor": 0, "erros": 0}

    fatias = planejar(
        inicio,
        fim,
        coletor.contar,
        cfg.teto_resultados,
        valores_de_faceta=coletor.valores_de_faceta,
        lacunas=lacunas,
    )

    for fatia in fatias:
        if fatia.chave() in feitas:
            resumo["puladas"] += 1
            continue

        resumo["fatias"] += 1
        inicio_fatia = agora()
        try:
            achados = novos = com = 0
            for resultado in coletor.listar(fatia):
                achados += 1
                acordao = Acordao.de_resultado(resultado, coletor.nome)

                teor = None
                if com_teor:
                    try:
                        teor = coletor.obter_teor(resultado.referencia)
                    except Exception as e:
                        log.warning("teor falhou (%s): %s", resultado.referencia.id_externo, e)

                if teor is not None:
                    acordao.paginas = len(teor.paginas)
                    acordao.hash_teor = hash_texto(teor.texto)
                    com += 1

                if _gravar(con, acordao, teor):
                    novos += 1

            _marcar(con, coletor.nome, fatia, inicio_fatia, achados, novos, "ok")
            resumo["encontrados"] += achados
            resumo["novos"] += novos
            resumo["com_teor"] += com
            log.info("%s %s: %d encontrados, %d novos", coletor.nome, fatia, achados, novos)

        except Exception as e:
            resumo["erros"] += 1
            _marcar(con, coletor.nome, fatia, inicio_fatia, 0, 0, "erro", str(e)[:500])
            log.exception("fatia %s falhou", fatia)
            # Segue para a próxima: uma fatia quebrada não pode parar semanas
            # de varredura. O status 'erro' a traz de volta no próximo passe.

    for lac in lacunas:
        with transacao(con):
            registrar_lacuna(con, coletor.nome, lac, agora())
        log.warning("%s", lac)

    con.close()
    return resumo


def _gravar(con, acordao: Acordao, teor) -> bool:
    """Upsert do acórdão + teor + composição. True se era inédito."""
    with transacao(con):
        existente = con.execute(
            "SELECT id, paginas, hash_teor FROM acordao WHERE id = ?", (acordao.id,)
        ).fetchone()

        orgao_id = _orgao_id(con, acordao.orgao_julgador)
        campos = (
            acordao.numero_cnj, acordao.numero_origem, acordao.sistema, acordao.grau,
            acordao.orgao_julgador, orgao_id, acordao.classe, acordao.tipo_decisao,
            acordao.data_julgamento, acordao.data_publicacao, acordao.ementa,
            acordao.dispositivo, int(acordao.segredo_justica), acordao.url_fonte,
            acordao.hash_ementa, acordao.hash_teor, acordao.paginas, agora(),
        )

        if existente is None:
            con.execute(
                "INSERT INTO acordao (numero_cnj, numero_origem, sistema, grau, orgao_julgador,"
                " orgao_id, classe, tipo_decisao, data_julgamento, data_publicacao, ementa,"
                " dispositivo, segredo_justica, url_fonte, hash_ementa, hash_teor, paginas,"
                " atualizado_em, id, coletado_em)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (*campos, acordao.id, agora()),
            )
            inedito = True
        else:
            # Não rebaixe: um registro que já tem teor não perde o teor para
            # uma passagem que só trouxe a ementa.
            if existente["paginas"] and not acordao.paginas:
                acordao.paginas = existente["paginas"]
                acordao.hash_teor = existente["hash_teor"]
            con.execute(
                "UPDATE acordao SET numero_cnj=?, numero_origem=?, sistema=?, grau=?,"
                " orgao_julgador=?, orgao_id=?, classe=?, tipo_decisao=?, data_julgamento=?,"
                " data_publicacao=?, ementa=COALESCE(?, ementa), dispositivo=COALESCE(?, dispositivo),"
                " segredo_justica=?, url_fonte=?, hash_ementa=?, hash_teor=?, paginas=?,"
                " atualizado_em=? WHERE id=?",
                (*campos, acordao.id),
            )
            inedito = False

        for a in acordao.assuntos:
            con.execute(
                "INSERT INTO assunto (acordao_id, codigo, descricao) VALUES (?,?,?)",
                (acordao.id, str(a.get("codigo", "")), a.get("nome") or a.get("descricao")),
            )

        indexar_ementa(con, acordao.id)

        if teor is not None and teor.paginas:
            con.execute("DELETE FROM documento WHERE acordao_id = ?", (acordao.id,))
            con.executemany(
                "INSERT INTO documento (acordao_id, pagina, texto, origem) VALUES (?,?,?,?)",
                [(acordao.id, i + 1, p, teor.origem) for i, p in enumerate(teor.paginas)],
            )
            indexar_paginas(con, acordao.id)
            _gravar_composicao(con, acordao.id, teor.texto)

    return inedito


def _gravar_composicao(con, acordao_id: str, texto: str) -> None:
    con.execute("DELETE FROM participacao WHERE acordao_id = ?", (acordao_id,))
    for p in extrair_composicao(texto):
        jid = _julgador_id(con, p.nome, p.nome_norm)
        con.execute(
            "INSERT OR REPLACE INTO participacao"
            " (acordao_id, julgador_id, papel, vencido, ordem, confianca, fonte)"
            " VALUES (?,?,?,?,?,?,?)",
            (acordao_id, jid, p.papel, int(p.vencido), p.ordem, p.confianca, p.fonte),
        )


def _julgador_id(con, nome: str, norm: str) -> int:
    linha = con.execute("SELECT julgador_id FROM julgador_alias WHERE alias_norm = ?", (norm,)).fetchone()
    if linha:
        return linha["julgador_id"]
    linha = con.execute("SELECT id FROM julgador WHERE nome_norm = ?", (norm,)).fetchone()
    if linha:
        return linha["id"]
    cur = con.execute(
        "INSERT INTO julgador (nome, nome_norm, cargo) VALUES (?,?,?)",
        (nome_canonico(nome), norm, "desembargador"),
    )
    return cur.lastrowid


def _orgao_id(con, nome: str | None) -> int | None:
    if not nome:
        return None
    norm = chave_orgao(nome)
    linha = con.execute("SELECT id FROM orgao WHERE nome_norm = ?", (norm,)).fetchone()
    if linha:
        return linha["id"]
    cur = con.execute(
        "INSERT INTO orgao (nome, nome_norm, tipo, grau) VALUES (?,?,?,?)",
        (nome.strip(), norm, _tipo_orgao(norm), "2" if "camara" in norm else None),
    )
    return cur.lastrowid


def _tipo_orgao(norm: str) -> str:
    if "camara" in norm and "criminal" in norm:
        return "camara_criminal"
    if "camara" in norm:
        return "camara_civel"
    if "orgao especial" in norm:
        return "orgao_especial"
    if "grupo" in norm:
        return "grupo_camaras"
    if "turma recursal" in norm:
        return "turma_recursal"
    return "outro"


def _fatias_concluidas(con, fonte: str) -> set[str]:
    return {
        r["fatia"]
        for r in con.execute(
            "SELECT fatia FROM coleta WHERE fonte = ? AND status = 'ok'", (fonte,)
        )
    }


def _marcar(con, fonte, fatia, inicio, achados, novos, status, detalhe=None) -> None:
    with transacao(con):
        con.execute(
            "INSERT INTO coleta (fonte, fatia, inicio, fim, encontrados, novos, status, detalhe)"
            " VALUES (?,?,?,?,?,?,?,?)"
            " ON CONFLICT(fonte, fatia) DO UPDATE SET fim=excluded.fim,"
            " encontrados=excluded.encontrados, novos=excluded.novos, status=excluded.status,"
            " detalhe=excluded.detalhe",
            (fonte, fatia.chave(), inicio, agora(), achados, novos, status, detalhe),
        )


def reprocessar(cfg: Config = CFG, ids: Iterable[str] | None = None) -> int:
    """Reextrai composição a partir do texto já gravado.

    Existe porque o parser de composição vai melhorar depois que você vir os
    acórdãos reais — e melhorar o parser não pode implicar recoletar nada.
    """
    con = conectar(cfg.banco)
    migrar(con)
    alvo = list(ids) if ids else [r["id"] for r in con.execute("SELECT id FROM acordao WHERE paginas > 0")]
    for acordao_id in alvo:
        texto = "\n\n".join(
            r["texto"]
            for r in con.execute(
                "SELECT texto FROM documento WHERE acordao_id = ? ORDER BY pagina", (acordao_id,)
            )
        )
        with transacao(con):
            _gravar_composicao(con, acordao_id, texto)
    con.close()
    return len(alvo)
