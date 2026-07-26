"""Servidor MCP do Ementário.

Expõe o acervo de jurisprudência do TCE-RJ como ferramentas de pesquisa. Fala
os dois transportes porque os clientes divergem: o Claude conversa por stdio
com um processo local, enquanto o ChatGPT só aceita servidor remoto por HTTP.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .acervo import ROTULOS, Acervo

# Hosts sempre aceitos: é por onde o servidor é usado na própria máquina.
_LOCAIS = ["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*"]


def seguranca_de_transporte(dominios: list[str] | None) -> TransportSecuritySettings:
    """Monta a política de Host/Origin aceitos.

    O SDK bloqueia por padrão qualquer Host que não seja local — é proteção
    contra DNS rebinding, e sem ela um site malicioso poderia falar com o
    servidor pelo navegador da vítima. Servir através de um túnel ou de um
    endereço público exige declarar esse domínio aqui; não há curinga, a
    comparação é exata.
    """
    hosts = list(_LOCAIS)
    origens = [f"http://{h}" for h in _LOCAIS if "*" not in h]

    for dominio in dominios or []:
        limpo = dominio.strip().removeprefix("https://").removeprefix("http://")
        limpo = limpo.rstrip("/")
        if not limpo:
            continue
        hosts += [limpo, f"{limpo}:*"]
        origens.append(f"https://{limpo}")

    if dominios:
        # O conector do ChatGPT chama de servidor, sem Origin, mas o painel de
        # testes chama do navegador.
        origens += ["https://chatgpt.com", "https://chat.openai.com"]

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origens,
    )

INSTRUCOES = """
Acervo de jurisprudência do Tribunal de Contas do Estado do Rio de Janeiro
(TCE-RJ): ementas de acórdãos, súmulas, respostas a consulta e questões de
ordem, coletadas do portal público do Tribunal.

Como responder ao advogado:
- Entregue análise e precedentes, não o funcionamento da ferramenta. Não cite
  nomes de tools, identificadores internos nem estrutura de URL.
- Chame `cobertura_do_acervo` quando precisar saber o alcance da base, e
  declare os limites que afetem a resposta.

COMO APRESENTAR CADA JULGADO — os quatro itens são obrigatórios, nesta ordem:

1. **Citação.** Exatamente o campo `citacao`: espécie, número/ano, processo,
   relator e data de julgamento. É a referência que vai para a peça.

2. **Do que tratou.** Uma ou duas frases dizendo qual era a controvérsia,
   a partir de `descritores` (a indexação oficial) e de `tese`. Não repita a
   lista de descritores crua — traduza em oração. Se `descritores` vier vazio,
   extraia da própria ementa.

3. **O que ficou decidido e como se aplica ao caso.** Reproduza a tese com
   fidelidade e diga, explicitamente, em que ela ajuda ou atrapalha a questão
   perguntada. Se o precedente for contrário ao que o advogado busca, diga isso
   com todas as letras — precedente contrário conhecido a tempo vale mais do
   que precedente favorável que não se sustenta.

4. **Link de conferência.** Sempre. `url_inteiro_teor` é o PDF do acórdão com o
   voto integral; `url_processo` abre a consulta processual. Apresente como
   "[Inteiro teor](url)" e "[Processo](url)", sem comentar o formato do
   endereço. Quando não houver `url_inteiro_teor` (súmulas, por exemplo),
   ofereça o que houver e diga qual é.

Nunca cite um julgado sem os quatro. Uma citação sem explicação obriga o
advogado a abrir tudo para saber se serve; uma explicação sem link o obriga a
confiar sem conferir.

A ementa é o resumo oficial, não o acórdão. Quando a tese for decisiva para a
peça, diga para conferir o inteiro teor pelo link antes de citar.

Limites que não podem ser omitidos quando importarem:
- A base de acórdãos é a *Jurisprudência Selecionada* — curadoria do Serviço de
  Jurisprudência, não todos os acórdãos do Tribunal. A ausência de uma tese
  aqui NÃO prova que o Tribunal não a firmou.
- Não há inteiro teor: só a ementa.
- Deliberações e Resoluções não estão no acervo.
- Súmula do TCE-RJ vincula a Administração estadual e municipal fluminense no
  âmbito do controle externo; ementa de acórdão é precedente persuasivo.
""".strip()


def _caminho_padrao() -> Path:
    if os.environ.get("EMENTARIO_BANCO"):
        return Path(os.environ["EMENTARIO_BANCO"])
    return Path(__file__).resolve().parent.parent / "dados" / "tcerj.sqlite"


def construir(
    banco: str | Path | None = None,
    dominios: list[str] | None = None,
    url_publica: str | None = None,
    segredo_oauth: str | None = None,
    **ajustes: Any,
) -> FastMCP:
    acervo = Acervo(banco or _caminho_padrao())

    # O ChatGPT recusa servidor MCP sem OAuth; o Claude conecta sem. O fluxo
    # só é montado quando há URL pública, porque os metadados precisam apontar
    # para endereços que o cliente alcance.
    if url_publica:
        from .autenticacao import montar

        provedor, definicoes = montar(url_publica, segredo_oauth)
        ajustes |= {"auth_server_provider": provedor, "auth": definicoes}

    mcp = FastMCP(
        "ementario",
        instructions=INSTRUCOES,
        transport_security=seguranca_de_transporte(dominios),
        **ajustes,
    )

    @mcp.tool()
    def pesquisar_jurisprudencia(
        consulta: str,
        especie: str | None = None,
        ano_min: int | None = None,
        ano_max: int | None = None,
        relator: str | None = None,
        limite: int = 10,
    ) -> dict[str, Any]:
        """Pesquisa a jurisprudência do TCE-RJ por palavras da ementa.

        Busca sem sensibilidade a acento ("licitacao" acha "licitação") e
        combina os termos com E. Para expressão exata, use aspas dentro da
        própria consulta: 'dispensa "notória especialização"'.

        Args:
            consulta: palavras ou expressão a procurar na ementa.
            especie: filtra a espécie — acordao, sumula, resposta_consulta.
            ano_min: ano mais antigo aceito.
            ano_max: ano mais recente aceito.
            relator: nome, ou parte do nome, do conselheiro relator.
            limite: quantos resultados devolver (máximo 50).
        """
        achados, parcial = acervo.pesquisar(
            consulta,
            especie=especie,
            ano_min=ano_min,
            ano_max=ano_max,
            relator=relator,
            limite=limite,
        )
        if not achados:
            observacao = (
                "Nenhum resultado. Isso não significa ausência de entendimento do "
                "Tribunal: a base é a Jurisprudência Selecionada, uma curadoria."
            )
        elif parcial:
            observacao = (
                "Nenhuma ementa reunia todos os termos; estes atendem a parte "
                "deles, ordenados por relevância. Confira a aderência ao caso "
                "antes de citar."
            )
        else:
            observacao = None

        return {
            "consulta": consulta,
            "quantidade": len(achados),
            "correspondencia_parcial": parcial,
            "resultados": [r.para_dict() for r in achados],
            "observacao": observacao,
        }

    @mcp.tool()
    def obter_documento(id: str) -> dict[str, Any]:
        """Devolve a ementa completa de um documento já localizado.

        Args:
            id: identificador vindo de uma pesquisa anterior.
        """
        achado = acervo.obter(id)
        if achado is None:
            return {"erro": f"Documento não encontrado: {id}"}
        return achado.para_dict()

    @mcp.tool()
    def listar_documentos(
        especie: str | None = None,
        ano: int | None = None,
        relator: str | None = None,
        limite: int = 20,
    ) -> dict[str, Any]:
        """Lista documentos por espécie, ano ou relator, sem termo de busca.

        Serve para varrer o acervo — por exemplo, todas as súmulas, ou o que um
        conselheiro relatou num ano.

        Args:
            especie: acordao, sumula, resposta_consulta, indefinido.
            ano: ano exato.
            relator: nome, ou parte do nome, do conselheiro relator.
            limite: quantos devolver (máximo 50).
        """
        achados = acervo.listar(especie=especie, ano=ano, relator=relator, limite=limite)
        return {"quantidade": len(achados), "resultados": [r.para_dict() for r in achados]}

    @mcp.tool()
    def cobertura_do_acervo() -> dict[str, Any]:
        """Descreve o que existe na base: volumes, período, relatores e limites.

        Consulte antes de afirmar que algo não consta, ou para saber quais
        filtros fazem sentido.
        """
        return acervo.cobertura()

    # -- Compatibilidade com os conectores do ChatGPT ---------------------
    # A pesquisa profunda do ChatGPT espera exatamente `search` e `fetch`, com
    # este formato de retorno. São fachadas finas sobre as ferramentas acima.

    @mcp.tool()
    def search(query: str) -> dict[str, Any]:
        """Search TCE-RJ case law by keyword. Returns matching documents.

        Args:
            query: words to look for in the case-law abstract.
        """
        achados, _ = acervo.pesquisar(query, limite=15)
        return {
            "results": [
                {"id": r.id, "title": r.citacao, "text": r.trecho or r.ementa[:400],
                 "url": r.url}
                for r in achados
            ]
        }

    @mcp.tool()
    def fetch(id: str) -> dict[str, Any]:
        """Fetch the full record of a TCE-RJ document by its id.

        Args:
            id: identifier returned by `search`.
        """
        achado = acervo.obter(id)
        if achado is None:
            return {"id": id, "title": "não encontrado", "text": "", "url": "",
                    "metadata": {}}
        return {
            "id": achado.id,
            "title": achado.citacao,
            "text": achado.ementa,
            "url": achado.url,
            "metadata": {
                "especie": ROTULOS.get(achado.tipo, achado.tipo),
                "relator": achado.relator or "",
                "processo": achado.processo or "",
                "data_sessao": achado.data_sessao or "",
                "assuntos": ", ".join(achado.assuntos),
                "url_inteiro_teor": achado.url_documento or "",
                "url_processo": achado.url_processo or "",
                "fonte": "TCE-RJ — Portal de Jurisprudência",
            },
        }

    return mcp
