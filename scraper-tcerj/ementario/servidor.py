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

E duas ferramentas que não devolvem julgado, e sim o que se precisa saber para
não errar o peso do que se achou: `sumulas_sobre` (há enunciado vinculante?) e
`panorama_do_tema` (quantos acórdãos existem, de que anos, quanto ficou por
ler).

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

DIVERGÊNCIA, PACIFICAÇÃO E O QUE NÃO SE PODE AFIRMAR

Antes de dizer qualquer coisa sobre **orientação do Tribunal** — e não sobre um
precedente isolado —, faça as duas verificações. Elas são baratas e a resposta
sem elas é insegura.

1. **`sumulas_sobre`.** Havendo súmula sobre o ponto, ela precede tudo: vincula
   a Administração fluminense no controle externo, enquanto ementa de acórdão
   apenas persuade. Acórdão anterior em sentido diverso está **superado**, não
   em divergência — a diferença muda a peça inteira. Não casando súmula por
   palavra, a ferramenta devolve todas: leia e conclua você, porque "nenhuma
   casou" não é "não existe".

2. **`panorama_do_tema`.** Diz quantos acórdãos tratam da matéria, como se
   distribuem no tempo e quantos estão na curadoria. É o denominador da sua
   afirmação.

Sobre divergência, três regras, e a terceira é a que não pode ser quebrada:

- **Nunca apresente um precedente sozinho como sendo o entendimento do
  Tribunal.** Resultado único é a principal fábrica de falsa pacificação.
  Reformule a busca e dimensione o tema antes.

- **Sempre declare a base do que afirma.** O campo `exame` traz quantos você
  examinou e quantos casam a expressão. Ao contar precedentes, diga "dos N que
  examinei" — nunca "o Tribunal majoritariamente entende". Um tema com
  trezentos acórdãos devolve doze na busca; descrever os doze como se fossem o
  Tribunal é falso, e soa verdadeiro por vir com número.

- **É VEDADO afirmar que não há divergência, ou que a matéria é pacífica, por
  não ter encontrado julgado em contrário.** No TCE-RJ a divergência quase
  nunca se declara: medido no acervo, menos de 1% dos acórdãos registram voto
  vencido ou voto divergente. O Tribunal decide diferente em anos diferentes,
  em processos diferentes, sem dizer que mudou. Logo, ausência de dissenso
  visível não é prova de nada, e `sinais_de_dissenso` vazio significa apenas
  que ninguém registrou dissenso interno — não que o entendimento seja um só.

  O que se pode dizer: "entre os N acórdãos que examinei, todos apontam nesse
  sentido, o mais recente de <ano>". O que não se pode: "o entendimento do
  TCE-RJ é pacífico".

Quando o `panorama_do_tema` mostrar julgados distribuídos ao longo dos anos,
prefira examinar os mais recentes e ao menos um antigo: entendimento que muda
sem aviso só aparece na comparação. Havendo desfechos diferentes sobre a mesma
matéria, **aponte a divergência explicitamente**, diga qual julgado é mais
recente e quantos você viu de cada lado — sempre como amostra.

DUAS ORIGENS, DOIS PESOS

Todo resultado traz `na_jurisprudencia_selecionada`.

- **Verdadeiro**: o Serviço de Jurisprudência escolheu divulgar o julgado como
  orientação. Há ementa oficial, com a tese destilada pelo Tribunal.
- **Falso**: o acórdão veio da Pesquisa Textual. É decisão real e citável, mas
  de caso concreto, sem ementa e sem o aval da curadoria. A tese tem de ser
  extraída do voto, com o cuidado de proveniência acima.

Diga ao advogado a que origem pertence cada julgado que apresentar. Entre dois
precedentes em sentido oposto, o que o Tribunal selecionou para divulgação pesa
mais — é o que ele assume como orientação.

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

5. **Origem.** Se o julgado integra a Jurisprudência Selecionada ou veio da
   Pesquisa Textual — o campo `na_jurisprudencia_selecionada`. Uma linha basta:
   "julgado selecionado pelo Tribunal" ou "acórdão de caso concreto, fora da
   curadoria". Muda o peso do precedente e o advogado tem de saber antes de
   apoiar a peça nele.

Nunca cite um julgado sem os cinco. Uma citação sem explicação obriga o
advogado a abrir tudo para saber se serve; uma explicação sem link o obriga a
confiar sem conferir; e um precedente sem origem declarada aparenta um peso que
pode não ter.

A ementa é o resumo oficial, não o acórdão. Quando a tese for decisiva para a
peça, diga para conferir o inteiro teor pelo link antes de citar.

Limites que não podem ser omitidos quando importarem:
- O acervo não é o conjunto dos acórdãos do TCE-RJ. Reúne a curadoria da
  *Jurisprudência Selecionada* e o que a Pesquisa Textual do Tribunal alcançou
  em temas de licitações e contratos. A ausência de uma tese aqui NÃO prova que
  o Tribunal não a firmou.
- Deliberações e Resoluções não estão no acervo.
- Súmula do TCE-RJ vincula a Administração estadual e municipal fluminense no
  âmbito do controle externo; ementa de acórdão é precedente persuasivo.
- Chame `cobertura_do_acervo` para os números do momento — o acervo cresce, e
  volumes citados de memória envelhecem.
""".strip()


def _exame(achados: list[Any], universo: int) -> dict[str, Any]:
    """Declara o que foi de fato examinado, e o que sobrou.

    Uma página de resultados parece um levantamento e não é. Sem o denominador,
    "todos os precedentes vão neste sentido" descreve a janela da busca e soa
    como descrição do Tribunal — é o modo mais comum de fabricar pacificação
    onde há divergência não lida.
    """
    anos = sorted({a for a in (_ano(r) for r in achados) if a})
    return {
        "examinados": len(achados),
        "acordaos_que_casam_a_expressao": universo,
        "e_amostra": universo > len(achados),
        "periodo_examinado": f"{anos[0]}–{anos[-1]}" if anos else None,
        "mais_recente_examinado": max(anos) if anos else None,
        "regra": (
            "Este é o recorte que a busca devolveu, não o conjunto do que o "
            "Tribunal decidiu. Ao contar precedentes, diga sempre 'dos N que "
            "examinei'. É vedado afirmar que não há divergência, ou que a "
            "matéria é pacífica, com base em não ter encontrado o contrário."
        ),
    }


def _bloco_sumulas(acervo: Acervo, consulta: str) -> dict[str, Any]:
    """Súmula pertinente vai junto do resultado, sem precisar ser pedida.

    Súmula do TCE-RJ vincula a Administração fluminense no controle externo;
    ementa de acórdão apenas persuade. Deixar a verificação a cargo de uma
    segunda chamada é deixá-la acontecer só quando alguém lembrar — e é
    exatamente quando não lembra que a peça sai citando precedente persuasivo
    contra enunciado vinculante.

    Aqui vai só o que casou. Não casando nada, o bloco aponta para
    `sumulas_sobre`, que devolve as vinte e oito para leitura direta: ausência
    de casamento léxico não é ausência de súmula.
    """
    achadas, _, _ = acervo.pesquisar(consulta, especie="sumula", limite=5)
    if not achadas:
        return {
            "encontradas": 0,
            "atencao": (
                "Nenhuma súmula casou estes termos. Isso NÃO autoriza dizer que "
                "não há súmula sobre a matéria — a busca é literal e o enunciado "
                "pode usar outro vocabulário. Chame `sumulas_sobre` para receber "
                "as súmulas do Tribunal e conferir uma a uma."
            ),
        }
    return {
        "encontradas": len(achadas),
        "sumulas": [s.para_dict() for s in achadas],
        "peso": (
            "Súmula do TCE-RJ vincula a Administração estadual e municipal "
            "fluminense no âmbito do controle externo. Havendo súmula sobre o "
            "ponto, ela precede os acórdãos na resposta — e um acórdão anterior "
            "em sentido diverso está superado, não em divergência."
        ),
    }


def _ano(resultado: Any) -> int | None:
    alvo = getattr(resultado, "documento", resultado)
    return getattr(alvo, "ano", None)


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
        elif len(achados) == 1:
            observacao = (
                "Um único precedente. Não o apresente como o entendimento do "
                "Tribunal: reformule a busca e consulte `panorama_do_tema` antes "
                "de dizer qualquer coisa sobre orientação consolidada."
            )
        else:
            observacao = None

        return {
            "consulta": consulta,
            "expressao_executada": expressao,
            "quantidade": len(achados),
            "correspondencia_parcial": parcial,
            "resultados": [r.para_dict() for r in achados],
            "exame": _exame(achados, acervo.universo(expressao, em_ementas=True)),
            "sumulas_sobre_a_materia": _bloco_sumulas(acervo, consulta),
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
        elif len({t.documento.id for t in achados}) == 1:
            observacao = (
                "Todos os trechos vieram de um único acórdão. Um acórdão é um "
                "precedente, não a orientação do Tribunal: consulte "
                "`panorama_do_tema` antes de generalizar."
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
            "exame": _exame(achados, acervo.universo(expressao)),
            "sumulas_sobre_a_materia": _bloco_sumulas(acervo, consulta),
            "observacao": observacao,
        }

    @mcp.tool()
    def panorama_do_tema(
        consulta: str, ano_min: int | None = None, ano_max: int | None = None
    ) -> dict[str, Any]:
        """Dimensiona um tema no acervo: quantos acórdãos, de que anos, com que sinais.

        Não devolve julgado nenhum — devolve o tamanho do que existe. Use
        sempre que for afirmar alguma coisa sobre *orientação do Tribunal*, e
        não sobre um precedente isolado: quantos acórdãos tratam do tema, como
        se distribuem no tempo, quantos o Serviço de Jurisprudência selecionou
        e quais carregam rastro de dissenso no julgamento.

        Serve para saber **quanto ficou por ler** antes de dizer que a matéria
        é pacífica. Números de distribuição não identificam divergência de
        teses; isso só a leitura dos votos faz.

        Args:
            consulta: o tema, nas mesmas palavras que se usaria na busca.
            ano_min: recorta a partir deste ano de julgamento.
            ano_max: recorta até este ano de julgamento.
        """
        return acervo.panorama(consulta, ano_min=ano_min, ano_max=ano_max)

    @mcp.tool()
    def sumulas_sobre(consulta: str) -> dict[str, Any]:
        """Verifica se há súmula do TCE-RJ sobre a matéria.

        Etapa obrigatória antes de responder sobre orientação do Tribunal.
        Súmula vincula a Administração fluminense no controle externo; ementa
        de acórdão é apenas persuasiva. Havendo súmula sobre o ponto, ela vem
        antes de qualquer acórdão na resposta.

        Não casando nenhuma pelas palavras da consulta, devolve **todas** as
        súmulas do Tribunal — são poucas e cabem numa leitura. É assim que se
        afirma ausência com base em ter conferido, e não em silêncio do índice.

        Args:
            consulta: a matéria sobre a qual se quer saber se há enunciado.
        """
        achadas, todas = acervo.sumulas_sobre(consulta)
        return {
            "consulta": consulta,
            "quantidade": len(achadas),
            "veio_o_conjunto_completo": todas,
            "sumulas": [s.para_dict() for s in achadas],
            "como_ler": (
                "Nenhuma súmula casou os termos da consulta; estas são TODAS as "
                "do Tribunal. Leia-as e conclua você: se nenhuma tratar da "
                "matéria, aí sim pode dizer que não há súmula sobre o ponto."
                if todas else
                "Estas casaram os termos da consulta. Confira a pertinência — "
                "casamento de palavra não é identidade de matéria. Se nenhuma "
                "servir, chame de novo com outro vocabulário antes de concluir."
            ),
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
