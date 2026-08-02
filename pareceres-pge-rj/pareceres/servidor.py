"""Servidor MCP dos pareceres da PGE-RJ.

Expõe o acervo consultivo da Procuradoria-Geral do Estado do Rio de Janeiro
sobre contratações, acordos e parcerias. Fala stdio (Claude local) e HTTP
(hospedagem e ChatGPT), como o servidor do Ementário.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .acervo import Acervo

_LOCAIS = ["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*"]


def seguranca_de_transporte(dominios: list[str] | None) -> TransportSecuritySettings:
    """Host/Origin aceitos. Sem declarar o domínio público, só passa requisição
    local — é a proteção do SDK contra DNS rebinding, e não há curinga."""
    hosts = list(_LOCAIS)
    origens = [f"http://{h}" for h in _LOCAIS if "*" not in h]
    for dominio in dominios or []:
        limpo = dominio.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        if not limpo:
            continue
        hosts += [limpo, f"{limpo}:*"]
        origens.append(f"https://{limpo}")
    if dominios:
        origens += ["https://chatgpt.com", "https://chat.openai.com"]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origens,
    )


INSTRUCOES = """
Acervo consultivo da Procuradoria-Geral do Estado do Rio de Janeiro sobre
contratações, acordos e parcerias — licitação, contratação direta, contrato
administrativo, convênio, terceiro setor (OS, OSCIP, MROSC), concessão,
permissão e uso de bem público. 14.420 documentos, 8.559 com inteiro teor,
177.156 páginas, de 1961 a 2026.

Como responder ao advogado: entregue a tese e o precedente, não o funcionamento
da ferramenta. Não cite nomes de tools, identificadores internos nem estrutura
de URL. Apresente links como "[Inteiro teor](url)" e ponto. Chame
`cobertura_do_acervo` quando precisar do alcance da base, e declare os limites
que afetarem a resposta.

REGRA 1 — A BUSCA É LITERAL; O VOCABULÁRIO JURÍDICO NÃO É

Uma só formulação falha por motivo puramente lexical. Medido neste acervo:
"reequilíbrio econômico-financeiro" acha 248 documentos; "equilíbrio
econômico-financeiro", 649; "reajustamento de preços", 397; "teoria da
imprevisão", 108. Somadas, 1.716 — quem busca só a primeira forma perde 85%.

Antes de concluir que o acervo não trata de um tema, chame `expandir_consulta`
e refaça a busca com as variantes. Preserve a consulta inicial: as variantes
acrescentam, não substituem. Registre por qual formulação cada precedente
apareceu — `expressao_executada` traz a expressão de fato usada.

REGRA 2 — DE QUEM É O TRECHO QUE VOCÊ ENCONTROU

Um parecer reúne, no mesmo texto: o relatório do que o órgão consultou, a
transcrição de doutrina e jurisprudência, os pareceres anteriores citados, a
tese que o parecerista vai REFUTAR, e só então a opinião da PGE. Para a busca
são caracteres iguais. Doutrina transcrita apresentada como entendimento da
Procuradoria inverte o parecer.

Cada página devolvida traz `secao` (relatório, fundamentação, conclusão ou não
identificada), `transcricao_percent` (0 a 100) e, quando for o caso,
`aviso_proveniencia`. 18% das páginas do acervo têm transcrição igual ou
superior a 50, e 11.658 dessas estão dentro da fundamentação — é ali que a
confusão acontece.

Nunca atribua um trecho à PGE-RJ sem verificar esses campos. Ao citar, diga de
onde veio: "consta da conclusão, à p. 14" e "consta de doutrina transcrita à
p. 9" têm pesos diferentes numa peça.

REGRA 3 — VIGÊNCIA: 87% DO ACERVO É ANTERIOR À LEI 14.133/2021

Um precedente envelhece; uma norma morre. Dos 14.420 documentos, 12.535 são
anteriores a 2021. Entre os que têm inteiro teor, 4.335 respondem sob a Lei
8.666/93 — revogada desde 30/12/2023 — e apenas 101 aplicam exclusivamente a
Lei 14.133/2021.

Cada documento traz `regime` e, quando cabível, `alerta_vigencia`. Nunca
responda pergunta de Lei 14.133 com parecer de regime 8.666 sem declarar isso.
A tese pode sobreviver ao novo regime, mas quem afirma que sobrevive é o
advogado, depois de conferir. No regime "transicao", o parecer cita os dois:
verifique a qual deles a conclusão se refere.

O PASSO OBRIGATÓRIO — E O QUE O `alerta_vigencia` NÃO SABE

**Antes de apresentar QUALQUER norma como fundamento, chame `situacao_da_norma`
sobre ela.** Sempre. Inclusive lei estadual, inclusive lei recente, inclusive
quando o parecer que você encontrou parecer convincente. Ela devolve o que as
ementas do acervo registram de revogação, declaração de inconstitucionalidade,
suspensão de eficácia e alteração — e devolve nessa ordem: do mais recente para
o mais antigo.

Ela **não** diz "está em vigor", e ausência de apontamento não é atestado de
norma íntegra: significa apenas que nenhum parecer deste recorte temático tocou
no assunto. Havendo apontamento, leia o parecer indicado antes de usar a norma.

Para ver todos os pareceres que aplicaram a norma — e não só os que apontaram
mudança de estado —, use `quem_citou`, que também vem do mais recente ao mais
antigo.

O campo `alerta_vigencia` cobre **uma única coisa**: a revogação da lei geral
de licitação. Ele NÃO sabe de declaração de inconstitucionalidade, de suspensão
de eficácia, de alteração legislativa posterior, nem de nada que envolva lei
estadual ou municipal. Silêncio dele não é atestado de vigência.

O caso que obriga esta regra: a Lei Estadual nº 6.450/2013, que disciplinava o
reembolso de honorários de defesa de agente público, **foi declarada
inconstitucional pelo Órgão Especial do TJRJ**, com efeitos erga omnes e ex
tunc, sem modulação. O acervo diz isso com todas as letras no Parecer MGV nº
19/2023 — que aparece em PRIMEIRO lugar quando se chama `quem_citou("Lei
6.450")`. Uma resposta que parou num parecer de 2020 apresentou como direito
vigente uma lei que não existe mais, e pelo motivo errado: não é conflito de
interesses que impede o reembolso, é falta de fundamento legal.

Some-se a isso: o acervo vai até 2026. Parar no documento mais antigo que
responde à pergunta é erro de pesquisa. Quando a resposta depender do estado
da norma ou do entendimento, **confira se há manifestação posterior** antes de
concluir.

AUTORIDADE — O QUE ESTE ACERVO É E O QUE NÃO É

Parecer da PGE-RJ vincula a Administração ESTADUAL fluminense nos termos da
legislação própria. Para um município é precedente PERSUASIVO, não norma. Diga
isso sempre que a consulta for de interesse municipal.

Não é o acervo integral da PGE-RJ, que tem 49.139 documentos: é o recorte
temático de contratações, acordos e parcerias. Ausência aqui não prova que a
Procuradoria não se pronunciou.

5.861 documentos têm apenas ficha e ementa, sem inteiro teor; outros 291 são
digitalização sem camada de texto, invisíveis à busca textual. Declare quando
isso afetar a resposta.

CONCLUSÃO: NEM TODA CONCLUSÃO É CONCLUSÃO

`conclusao_e_do_parecer` distingue a conclusão própria (5.899 documentos) do
despacho que apenas chancela parecer alheio (1.567). Onde nenhuma fórmula foi
identificada (1.093), vem `fecho_bruto` — o fim literal do documento, sem
interpretação. Não apresente fecho bruto como se fosse conclusão.
""".strip()


def _caminho_padrao() -> Path:
    do_ambiente = os.environ.get("PARECERES_BANCO")
    if do_ambiente:
        return Path(do_ambiente)
    local = Path(__file__).resolve().parent.parent / "dados" / "pge_rj_pareceres.db"
    if local.exists():
        return local
    return Path(os.path.expanduser(
        "~/Documents/PGE-RJ_Pareceres_Contratacoes/pge_rj_pareceres.db"))


def construir(banco: str | None = None, dominios: list[str] | None = None,
              **ajustes: Any) -> FastMCP:
    acervo = Acervo(banco or _caminho_padrao())

    mcp = FastMCP(
        "Pareceres PGE-RJ",
        instructions=INSTRUCOES,
        transport_security=seguranca_de_transporte(dominios),
        **ajustes,
    )

    @mcp.tool()
    def pesquisar_pareceres(consulta: str, limite: int = 10,
                            ano_minimo: int | None = None,
                            ano_maximo: int | None = None,
                            regime: str | None = None) -> dict[str, Any]:
        """Procura na ementa, nos assuntos indexados e no título — o resumo
        oficial, com a tese já destilada. Use primeiro; é a via mais precisa.

        `regime` filtra por norma de regência: "14.133", "8.666", "transicao",
        "13.019".
        """
        achados, expressao, total = acervo.pesquisar(
            consulta, limite=limite, ano_min=ano_minimo, ano_max=ano_maximo,
            regime=regime)
        # Consulta longa com todos os termos exigidos costuma devolver zero por
        # motivo lexical, não por ausência de precedente. Refaz com OU e avisa.
        operador = "todos os termos"
        if not achados:
            achados, expressao, total = acervo.pesquisar(
                consulta, limite=limite, ano_min=ano_minimo, ano_max=ano_maximo,
                regime=regime, operador="OR")
            operador = "qualquer termo (a busca com todos não devolveu nada)"
        return {
            "expressao_executada": expressao,
            "criterio": operador,
            "total_encontrado": total,
            "exibindo": len(achados),
            "resultados": [p.para_dict() for p in achados],
            "nota": ("Nem com todos os termos nem com qualquer um deles houve "
                     "resultado. Chame expandir_consulta e refaça com as variantes "
                     "antes de concluir que a PGE não se pronunciou.")
            if not achados else None,
        }

    @mcp.tool()
    def pesquisar_inteiro_teor(consulta: str, limite: int = 8,
                               paginas_por_documento: int = 3,
                               ano_minimo: int | None = None,
                               ano_maximo: int | None = None,
                               excluir_relatorio: bool = False) -> dict[str, Any]:
        """Procura dentro do texto dos pareceres e devolve A PÁGINA, com a seção
        e o grau de transcrição. É onde está a fundamentação — e onde mora o
        risco de atribuir à PGE palavra de terceiro.

        `excluir_relatorio=True` descarta as páginas de relatório, que só
        recontam o que o órgão consulente afirmou.
        """
        achados, expressao, total = acervo.pesquisar_paginas(
            consulta, limite=limite, paginas_por_doc=paginas_por_documento,
            ano_min=ano_minimo, ano_max=ano_maximo, so_fundamentacao=excluir_relatorio)
        criterio = "todos os termos na mesma página"
        if not achados:
            achados, expressao, total = acervo.pesquisar_paginas(
                consulta, limite=limite, paginas_por_doc=paginas_por_documento,
                ano_min=ano_minimo, ano_max=ano_maximo,
                so_fundamentacao=excluir_relatorio, operador="OR")
            criterio = "qualquer termo (com todos na mesma página não houve resultado)"
        return {
            "expressao_executada": expressao,
            "criterio": criterio,
            "documentos_com_ocorrencia": total,
            "exibindo": len(achados),
            "resultados": [p.para_dict() for p in achados],
            "lembrete": ("Verifique secao e transcricao_percent antes de atribuir "
                         "qualquer trecho à Procuradoria."),
        }

    @mcp.tool()
    def ler_paginas(id: int, pagina_inicial: int, quantidade: int = 3) -> dict[str, Any]:
        """Lê páginas contíguas de um parecer, para ver o contexto ao redor de
        um trecho encontrado. Máximo de 10 por chamada."""
        p = acervo.obter(id)
        if not p:
            return {"erro": f"documento {id} não encontrado"}
        paginas = acervo.paginas_do_documento(id, pagina_inicial, quantidade)
        return {
            "id": id,
            "citacao": p.titulo,
            "total_de_paginas": p.paginas,
            "regime": p.regime,
            "alerta_vigencia": p.alerta_vigencia or None,
            "paginas": paginas,
            "url_inteiro_teor": p.url_pdf or None,
        }

    @mcp.tool()
    def expandir_consulta(termo: str) -> dict[str, Any]:
        """Devolve as formas equivalentes de um conceito, com quantos documentos
        cada uma alcança neste acervo. Use antes de dizer que não há precedente.
        """
        conceitos = acervo.sinonimos(termo)
        return {
            "termo": termo,
            "conceitos": conceitos,
            "nota": ("Sem entrada no tesauro para este termo; refaça a busca com "
                     "sinônimos próprios do vocabulário administrativo.")
            if not conceitos else
            ("Refaça a busca com as variantes de maior contagem. Elas se somam: "
             "os conjuntos raramente coincidem."),
        }

    @mcp.tool()
    def obter_documento(id: int) -> dict[str, Any]:
        """Ficha completa de um parecer: ementa, assuntos, procurador, órgão
        consulente, processo, conclusão, regime e links de conferência."""
        p = acervo.obter(id)
        return p.para_dict() if p else {"erro": f"documento {id} não encontrado"}

    @mcp.tool()
    def conclusoes_sobre(consulta: str, limite: int = 15,
                         so_conclusao_propria: bool = True) -> dict[str, Any]:
        """Triagem rápida: devolve só as conclusões dos pareceres que casam com
        a busca, sem o corpo. Serve para varrer muitos pareceres de uma vez e
        decidir quais valem leitura integral."""
        # Só faz sentido varrer o que tem conclusão: sem inteiro teor não há.
        achados, expressao, total = acervo.pesquisar(
            consulta, limite=limite * 3, so_com_conclusao=True)
        if not achados:
            achados, expressao, total = acervo.pesquisar(
                consulta, limite=limite * 3, so_com_conclusao=True, operador="OR")
        saida = []
        for p in achados:
            d = p.para_dict()
            propria = d.get("conclusao_e_do_parecer")
            if so_conclusao_propria and not propria:
                continue
            saida.append({
                "id": p.codigo, "citacao": p.titulo, "ano": p.ano,
                "regime": p.regime, "alerta_vigencia": p.alerta_vigencia or None,
                "conclusao": d.get("conclusao") or d.get("fecho_bruto"),
                "conclusao_e_do_parecer": propria,
                "url_ficha": d["url_ficha"],
            })
            if len(saida) >= limite:
                break
        return {"expressao_executada": expressao, "total_encontrado": total,
                "conclusoes": saida}

    @mcp.tool()
    def quem_citou(referencia: str, limite: int = 25) -> dict[str, Any]:
        """CONFERE O QUE ACONTECEU COM UMA NORMA, e mapeia o precedente interno.

        Etapa obrigatória antes de apresentar qualquer norma como fundamento:
        devolve quem a cita, do mais recente para o mais antigo, e é assim que
        se descobre revogação, declaração de inconstitucionalidade, suspensão ou
        mudança de entendimento — nada disso está no campo `alerta_vigencia`.

        Serve também para súmula, acórdão e parecer interno da própria PGE.
        Ex.: "Lei 6.450", "Lei 14.133", "Sumula 247", "Parecer 25/2009".
        """
        return acervo.quem_citou(referencia, limite=limite)

    @mcp.tool()
    def situacao_da_norma(norma: str) -> dict[str, Any]:
        """O QUE ACONTECEU COM UMA NORMA, segundo os próprios pareceres.

        Etapa obrigatória antes de apresentar qualquer norma como fundamento.
        Devolve os apontamentos de revogação, declaração de
        inconstitucionalidade, suspensão de eficácia e alteração que as ementas
        do acervo registram, do mais recente para o mais antigo.

        NÃO devolve "está em vigor" — esta base não autoriza essa afirmação.
        Ausência de apontamento não é atestado de norma íntegra.

        Ex.: "Lei 6.450", "Lei 8.666", "Decreto 40.500".
        """
        return acervo.situacao_da_norma(norma)

    @mcp.tool()
    def listar_documentos(ano: int | None = None, procurador: str | None = None,
                          orgao: str | None = None, eixo: str | None = None,
                          regime: str | None = None, limite: int = 30) -> dict[str, Any]:
        """Varredura por ano, procurador, órgão consulente, eixo temático
        (Licitacao, Contrato administrativo, Terceiro setor, Convenio e
        cooperacao, Concessao PPP e uso de bem, Contratacao direta, Obras e
        engenharia, Estatais) ou regime de vigência."""
        achados = acervo.listar(ano=ano, procurador=procurador, orgao=orgao,
                                eixo=eixo, regime=regime, limite=limite)
        return {"exibindo": len(achados),
                "resultados": [p.para_dict(com_conclusao=False) for p in achados]}

    @mcp.tool()
    def cobertura_do_acervo() -> dict[str, Any]:
        """Volumes, período, recorte, autoridade e limites declarados. Chame
        antes de afirmar que algo não existe no acervo."""
        return acervo.cobertura()

    return mcp
