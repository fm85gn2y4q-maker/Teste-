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

DUAS BUSCAS, PROPOSITALMENTE SEPARADAS:
- `pesquisar_jurisprudencia` procura nas **ementas** — o resumo oficial, com a
  tese já destilada pelo Tribunal.
- `pesquisar_inteiro_teor` procura dentro dos **votos e acórdãos**, e devolve
  a página. É onde está a fundamentação.

Diga sempre de onde veio a proposição. "Consta da ementa" e "consta do voto,
à p. 27" têm pesos diferentes numa peça, e o advogado precisa saber qual dos
dois você leu. Não encontrando na ementa, procure no inteiro teor antes de
concluir que o Tribunal não se pronunciou.

UMA PERGUNTA, VÁRIAS FORMULAÇÕES

A busca é literal. Uma única tradução da pergunta em consulta pode falhar por
motivo puramente lexical: termos genéricos como "projeto", "contrato" ou
"aditivo" espalham a relevância por documentos densos mas juridicamente
laterais, enquanto o precedente pertinente usa outro vocabulário. Medido neste
acervo: "erro de projeto básico justifica aditivo?" não achou nada de útil;
"deficiência do projeto básico" achou o precedente na primeira tentativa.

1. **Preserve a consulta inicial.** As variantes acrescentam, não substituem.
   A pergunta do advogado é o alvo; as variantes são caminhos até ele.

2. **Reformule quando o resultado for fraco ou lateral.** Sinais: os primeiros
   resultados tratam de assunto diverso; os termos aparecem dispersos sem
   formar a relação jurídica perguntada; a busca caiu em correspondência
   parcial casando só palavras genéricas; a leitura do melhor resultado mostra
   que ele não responde. Outro sinal forte: a busca por ementa trouxe
   precedente pertinente que o inteiro teor não recuperou — as duas servem de
   controle cruzado uma da outra.

3. **Variante é o mesmo problema com outro vocabulário, nunca a resposta
   presumida.** Para "erro de projeto básico justifica aditivo?", valem
   "deficiência projeto básico", "projeto básico incompleto aditivo", "falha
   de planejamento termo aditivo". Não vale formular a variante já embutindo
   a conclusão que se quer encontrar — isso é procurar confirmação, não
   pesquisar.

4. **Antes de dizer que não há precedente, tente ao menos uma variante.**
   Dispensável apenas quando a consulta original já for literal e específica
   (uma expressão exata entre aspas, por exemplo).

Registre, para cada precedente que apresentar, por qual formulação ele
apareceu — o campo `expressao_executada` traz a expressão de fato usada. Serve
para o advogado saber como a pesquisa foi feita, e para refazê-la depois.

PROVENIÊNCIA: A REGRA QUE NÃO PODE SER QUEBRADA

O PDF do acórdão não é um texto homogêneo. Ele reúne, em sequência:

    o acórdão (decisão colegiada certificada)
    o relatório
    as alegações de defesa do jurisdicionado
    a instrução do corpo técnico
    o parecer do Ministério Público de Contas
    decisões anteriores transcritas (notificações, cautelares)
    precedentes transcritos, adotados ou não
    a fundamentação do relator
    o dispositivo do voto

Para a busca, tudo isso são caracteres iguais. Juridicamente, não são. Um
trecho tirado das razões de defesa diz o que a **parte alegou ao Tribunal** —
o oposto do que o Tribunal decidiu. Apresentá-lo como entendimento do TCE-RJ
inverte o sentido do precedente.

**Nunca afirme que um trecho representa o entendimento do TCE-RJ sem antes ler
seu contexto e identificar de que parte do documento ele vem.** A rotina:

1. `pesquisar_inteiro_teor` localiza a passagem.
2. `ler_paginas` com `vizinhas=1` mostra o contexto imediato.
3. Identifique a natureza do trecho pelos marcos do próprio documento:
   "ACORDAM" e "ACÓRDÃO Nº" abrem a decisão colegiada; "É o Relatório"
   encerra o relato e inicia a análise; "VOTO" abre a fundamentação;
   "o jurisdicionado alega", "razões de defesa", "sustenta o responsável"
   introduzem alegação de parte; "o Corpo Instrutivo", "a Coordenadoria
   propôs" introduzem instrução técnica; "o Ministério Público de Contas
   opinou" introduz o parecer.
4. Continuando ambíguo, **expanda a leitura** — em especial quando o trecho
   for alegação ou instrução: o que importa é o que o relator fez com aquilo,
   e isso pode estar várias páginas adiante.
5. Só então formule a tese.

O limite de `adiante` é **operacional, não interpretativo**. Se ao fim da
janela o trecho ainda estiver dentro das razões de defesa, da instrução ou de
transcrição — ou se o posicionamento do relator não tiver aparecido —,
continue lendo em nova chamada. "Acabou a janela" não é conclusão jurídica, e
declarar o ponto indeterminado por esgotamento de leitura é erro pior do que
demorar mais uma consulta.

Verifique também o **estágio processual**. Um voto pode conter formulação
jurídica robusta e, ao final, apenas notificar para defesa: a tese existe, o
julgamento de mérito não. Nesse caso, diga que a questão foi posta, não que
foi decidida.

Ao apresentar, informe de onde vem o trecho: "consta do dispositivo do voto",
"consta do acórdão", "é alegação da defesa, acolhida à p. X". Um precedente
citado sem essa qualificação vale menos do que parece — e pode valer o
contrário.

Um único acórdão é um precedente, não a jurisprudência consolidada do
Tribunal. Diga "nesse precedente", salvo quando houver súmula ou resposta a
consulta, que têm força própria.

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
        achados, parcial, expressao = acervo.pesquisar(
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
            "expressao_executada": expressao,
            "quantidade": len(achados),
            "correspondencia_parcial": parcial,
            "resultados": [r.para_dict() for r in achados],
            "observacao": observacao,
        }

    @mcp.tool()
    def pesquisar_inteiro_teor(
        consulta: str,
        especie: str | None = None,
        ano_min: int | None = None,
        ano_max: int | None = None,
        relator: str | None = None,
        limite: int = 10,
    ) -> dict[str, Any]:
        """Procura dentro dos votos e acórdãos, não nas ementas.

        A ementa é o resumo oficial; o voto é onde a tese é construída. Use
        esta ferramenta quando a pergunta for sobre fundamentação, sobre um
        argumento específico, ou quando a busca por ementa não achar nada.
        Cada resultado traz a página, para conferência no documento oficial.

        Args:
            consulta: palavras ou expressão a procurar no texto dos votos.
            especie: filtra a espécie — hoje só acórdãos têm inteiro teor.
            ano_min: ano mais antigo aceito.
            ano_max: ano mais recente aceito.
            relator: nome, ou parte do nome, do conselheiro relator.
            limite: quantos trechos devolver (máximo 30).
        """
        achados, parcial, expressao = acervo.pesquisar_paginas(
            consulta, especie=especie, ano_min=ano_min, ano_max=ano_max,
            relator=relator, limite=limite,
        )
        if not achados:
            observacao = (
                "Nada encontrado com esta formulação. Antes de concluir que o "
                "Tribunal não se pronunciou, tente ao menos uma variante lexical "
                "equivalente — a busca é literal, e o voto pode nomear o mesmo "
                "problema com outras palavras."
            )
        elif parcial:
            observacao = (
                "Nenhuma página reunia todos os termos; estas atendem a parte "
                "deles, ordenadas por relevância. Verifique `termos_encontrados` "
                "para saber o que de fato casou."
            )
        else:
            observacao = None

        return {
            "consulta": consulta,
            # Registre esta expressão ao anotar por qual formulação cada
            # precedente apareceu: a mesma pergunta, dita de outro modo,
            # encontra documentos diferentes.
            "expressao_executada": expressao,
            "quantidade": len(achados),
            "correspondencia_parcial": parcial,
            "resultados": [t.para_dict() for t in achados],
            "observacao": observacao,
        }

    @mcp.tool()
    def ler_paginas(
        id: str, pagina: int, vizinhas: int = 1, adiante: int | None = None
    ) -> dict[str, Any]:
        """Lê páginas contíguas do inteiro teor, para saber de onde vem o trecho.

        Etapa obrigatória antes de tratar uma passagem como entendimento do
        Tribunal: o documento reúne relatório, defesa, instrução, precedentes
        transcritos e o voto, e a busca não distingue nenhum deles.

        Sendo o trecho alegação de parte ou instrução técnica, o que importa
        está adiante — use `adiante` para avançar até a análise do relator.

        Args:
            id: identificador do documento ou de uma de suas ementas.
            pagina: página central.
            vizinhas: páginas antes e depois (até 5).
            adiante: quando informado, lê desta página até `pagina + adiante`
                (até 15), para alcançar o que o relator decidiu sobre o ponto.
        """
        antes = max(0, min(vizinhas, 5))
        depois = max(0, min(adiante, 15)) if adiante is not None else antes
        paginas = acervo.paginas_do_documento(id, pagina - antes, pagina + depois)
        if not paginas:
            return {"erro": f"Sem inteiro teor para {id} na página {pagina}."}
        documento = acervo.obter(id)
        return {
            "citacao": documento.citacao if documento else id,
            "url_inteiro_teor": documento.url_documento if documento else None,
            "paginas": paginas,
            "lembrete": (
                "Identifique a natureza de cada trecho antes de citar: acórdão, "
                "relatório, alegação de parte, instrução técnica, parecer do MPC, "
                "precedente transcrito, fundamentação ou dispositivo."
            ),
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
