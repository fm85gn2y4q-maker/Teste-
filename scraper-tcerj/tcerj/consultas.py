"""Inteiro teor das Respostas a Consulta.

A coleta original guardou só a ementa das 572 respostas, e o acervo declarava,
como limite, que "só acórdãos têm inteiro teor". Era verdade por omissão: o
payload da listagem já trazia `arquivoId`, e o PDF sempre esteve a uma
requisição de distância, pelo mesmo endpoint que o acervo normativo usa.

Isso importa mais do que o volume sugere. **Resposta a Consulta tem peso
próprio no TCE-RJ** — é o que o Tribunal responde quando um jurisdicionado
pergunta em tese, e vale como orientação, não como precedente de caso
concreto. Ter só a ementa dela é ter o assunto sem a fundamentação.

E há uma segunda coisa que o payload guardava e ninguém lia: **a resposta a
consulta pode ser REVOGADA**. São `revogada`, `revogadaParcialmente`,
`numeroRevogacao`, `dataRevogacao` e `justificativaRevogacao`. Nove das 572
estão nessa condição. Uma orientação revogada apresentada como vigente é o
mesmo erro do acervo normativo, numa base onde ninguém esperava encontrá-lo.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from .http import Cliente
from .inteiro_teor import impressao_digital, paginas_do_pdf

log = logging.getLogger(__name__)

URL_ARQUIVO = "https://www.tcerj.tc.br/cadastro-publicacoes-webapi/api/file/{id}"


def dados_de_revogacao(bruto: str | None) -> dict[str, Any]:
    """Extrai do payload guardado o que a listagem diz sobre vigência."""
    if not bruto:
        return {}
    try:
        b = json.loads(bruto)
    except (ValueError, TypeError):
        return {}
    revogada = bool(b.get("revogada"))
    parcial = bool(b.get("revogadaParcialmente"))
    if not (revogada or parcial):
        return {}
    data = b.get("dataRevogacao") or ""
    return {
        "estado": "revogada_parcialmente" if parcial and not revogada else "revogada",
        "por": b.get("numeroRevogacao") or None,
        "em": data[:10] if data and not data.startswith("0001") else None,
        "justificativa": (b.get("justificativaRevogacao") or "").strip() or None,
    }


async def coletar(
    config,
    armazenamento,
    max_documentos: int | None = None,
    ao_progresso: Callable[[int, int, int], None] | None = None,
) -> dict[str, int]:
    """Baixa e extrai o inteiro teor das respostas a consulta que faltam."""
    pendentes = [
        dict(l) for l in armazenamento.conexao.execute(
            "SELECT d.id, d.numero, d.ano, d.processo, d.bruto FROM documentos d "
            "WHERE d.tipo = 'resposta_consulta' AND NOT EXISTS ("
            "  SELECT 1 FROM paginas p WHERE p.documento_id = "
            "    'resposta_consulta-' || d.numero || '-' || d.ano) "
            "ORDER BY d.ano DESC, CAST(d.numero AS INTEGER) DESC"
        )
    ]
    if max_documentos:
        pendentes = pendentes[:max_documentos]

    log.info("Respostas a consulta na fila: %d", len(pendentes))
    contagem = {"novos": 0, "paginas": 0, "falhas": 0, "sem_arquivo": 0}

    async with Cliente(config) as cliente:
        for item in pendentes:
            oficial = f"resposta_consulta-{item['numero']}-{item['ano']}"
            bruto = json.loads(item["bruto"]) if item["bruto"] else {}
            arquivo = bruto.get("arquivoId")
            comum = dict(tipo="resposta_consulta", numero=str(item["numero"]),
                         ano=item["ano"], processo=item["processo"],
                         url=URL_ARQUIVO.format(id=arquivo) if arquivo else None)

            if not arquivo:
                armazenamento.registrar_oficial(
                    oficial, **comum, status="sem_arquivo",
                    detalhe="listagem não traz arquivoId")
                contagem["sem_arquivo"] += 1
                continue

            try:
                resposta = await cliente.obter(URL_ARQUIVO.format(id=arquivo))
                if not resposta.content.startswith(b"%PDF"):
                    raise ValueError(
                        f"resposta não é PDF ({resposta.content[:16]!r})")
                paginas = paginas_do_pdf(resposta.content)
            except Exception as erro:  # noqa: BLE001 — rede e PDF de terceiro
                armazenamento.registrar_oficial(
                    oficial, **comum, status="erro_temporario",
                    detalhe=str(erro)[:200])
                log.warning("Falha em %s: %s", oficial, str(erro)[:120])
                contagem["falhas"] += 1
                continue

            if not paginas:
                armazenamento.registrar_oficial(
                    oficial, **comum, status="sem_texto",
                    detalhe="PDF sem texto aproveitável")
                contagem["falhas"] += 1
                continue

            contagem["paginas"] += armazenamento.gravar_paginas(oficial, paginas)
            armazenamento.registrar_oficial(
                oficial, **comum, paginas_total=len(paginas),
                impressao=impressao_digital(paginas), status="ok")
            contagem["novos"] += 1

            if ao_progresso and contagem["novos"] % 25 == 0:
                ao_progresso(contagem["novos"], contagem["paginas"],
                             contagem["falhas"])

    return contagem
