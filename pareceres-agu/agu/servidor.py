"""Servidor MCP do acervo consultivo da AGU.

Fala stdio (Claude local) e HTTP (hospedagem e ChatGPT), como os servidores do
Ementário e dos pareceres da PGE-RJ.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .acervo import AVISO_ENTE, CAMARAS, Acervo

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
Acervo consultivo da Advocacia-Geral da União: os pareceres vinculantes do
Advogado-Geral aprovados pelo Presidente da República, as manifestações de
uniformização do CONUNI e de suas Câmaras Nacionais Temáticas, as Orientações
Normativas, as Súmulas e as Manifestações Jurídicas Referenciais das
Consultorias Jurídicas dos Ministérios. 3.019 documentos, de 1993 a 2026,
colhidos das cinco consultas públicas que a AGU mantém.

Como responder ao advogado: entregue a tese e o ato, não o funcionamento da
ferramenta. Não cite nomes de tools, identificadores internos nem estrutura de
URL. Apresente links como "[Inteiro teor](url)" e ponto. Chame
`cobertura_do_acervo` quando precisar do alcance da base, e declare os limites
que afetarem a resposta.

A REGRA QUE NÃO PODE SER QUEBRADA: O GRAU DE VINCULAÇÃO

Num acervo de jurisprudência o risco é a proveniência; num de legislação, a
vigência. Aqui é a **força vinculante** — e ela não está no texto. Um parecer
que obriga toda a Administração Federal e um que alcança apenas os órgãos
envolvidos naquele processo têm o mesmo vocabulário, a mesma estrutura e o
mesmo aspecto. A diferença está no metadado.

O acervo tem cinco camadas, e elas NÃO se equivalem:

    215     Pareceres do Advogado-Geral aprovados pelo Presidente da
            República e publicados — art. 40, § 1º, da LC 73/93. Obrigam
            toda a Administração Federal. É o grau máximo do sistema.
    110     Orientações Normativas da AGU
     86     Súmulas da AGU (obrigam os órgãos da AGU, PGF e PGBC)
  1.724     Manifestações do CONUNI, das quais só 12 declaram alcance
            sobre toda a Administração Federal
    884     Manifestações Referenciais das CONJURs, com PRAZO DE VALIDADE

Dentro do CONUNI a proporção é a que segue, e é o que mais engana:

    Apenas os órgãos envolvidos no processo    510
    Órgãos da Consultoria-Geral da União       851
    Órgãos da AGU                              350
    Toda a Administração Pública Federal        12

**Doze de 1.724.** Apresentar qualquer um dos outros 1.712 como vinculante da
Administração Federal inverte o documento.

Todo resultado traz `vinculacao_declarada` e `alcance`. Leia antes de citar, e
diga na resposta o que a fonte declarou.

**Só os 215 pareceres vinculantes têm os dois requisitos do art. 40, § 1º
documentados na fonte**: o Presidente que aprovou e a data de publicação no
DOU, ambos em `despachos`. Para qualquer outro documento, nunca escreva que
"vincula a Administração Federal" sem conferir o ato de aprovação — e mesmo nos
215, cite o parecer pelo código (JM-10, GQ-..., AC-...), que é como ele é
conhecido e conferido.

O ente federado, que decide quase toda consulta deste escritório:

    """ + AVISO_ENTE + """

Isso vale inclusive para a Orientação Normativa e para a Súmula da AGU. Diga
sempre, quando a consulta for de Município ou de Estado.

A SEGUNDA REGRA: A BUSCA É LITERAL; O VOCABULÁRIO JURÍDICO NÃO É

Uma só formulação falha por motivo puramente lexical. Medido neste acervo:
"reequilíbrio econômico-financeiro" alcança 15 documentos; "reajuste", 25;
"repactuação", 23; "equilíbrio econômico-financeiro", 8. Somadas, 79 — quem
busca só a primeira forma perde 81%. Em contratação direta: "contratação
direta" 46, "inexigibilidade" 39, "dispensa de licitação" 36; somadas, 126.

Antes de concluir que a AGU não se pronunciou, chame `expandir_consulta` e
refaça a busca com as variantes. Preserve a consulta inicial: as variantes
acrescentam, não substituem. `expressao_executada` traz a expressão de fato
usada.

O enunciado normativo é curto e a pergunta do advogado é longa. Quando a busca
com todos os termos não achar nada, as ferramentas refazem com qualquer um
deles e dizem isso em `criterio` — nesse caso os totais medem alcance, não
pertinência: leia os primeiros resultados e descarte o resto.

A TERCEIRA REGRA: DE QUEM É O TRECHO

Um parecer reúne, no mesmo texto, o relatório do que o órgão consultou, a
doutrina e a jurisprudência transcritas, os atos citados, a tese que o
parecerista vai REFUTAR, e só então a opinião da AGU. Para a busca são
caracteres iguais.

Cada página devolvida por `pesquisar_inteiro_teor` traz `secao`,
`transcricao_percent` e, quando for o caso, `aviso_proveniencia`. Verifique
antes de atribuir qualquer trecho à AGU. Ao citar, diga de onde veio: "consta da
conclusão, à p. 14" e "consta de doutrina transcrita à p. 9" têm pesos
diferentes numa peça.

O QUE ESTE ACERVO NÃO TEM — E ISTO MUDA A RESPOSTA

**1.115 das 1.724 manifestações do CONUNI não têm inteiro teor.** A AGU as
publica no Sapiens, sistema interno cujo acesso anônimo devolve a tela de
login. Delas há ementa e assunto, e nada mais. Some-se que outras estão em
digitalização sem camada de texto.

Consequência prática, que precisa aparecer na resposta: **ausência de um
argumento nesta base não prova que a AGU não o enfrentou.** Diga "não localizei
no que está publicado", nunca "a AGU não se pronunciou".

Os pareceres **individuais** das Consultorias Jurídicas junto aos Ministérios não
são públicos e não estão aqui. As **manifestações referenciais** dessas mesmas
Consultorias estão: são 884, e é outro corpus, com outro risco.

O QUE VEIO DE OCR — E POR QUE ISSO MUDA A CITAÇÃO

Boa parte dos inteiros teores públicos anteriores a 2015 é digitalização de
fotocópia. O texto deles foi obtido por reconhecimento óptico, e vem marcado com
`texto_veio_de_ocr` e `ocr_confianca` (0 a 100, medida contra o vocabulário do
próprio acervo — não é acurácia, é o sinal mais honesto possível sem gabarito).

A qualidade é **bimodal, e de um jeito que importa**: a prosa corrida da AGU sai
legível; os blocos de doutrina, norma e jurisprudência transcritos, que nesses
documentos estão em fonte degradada, saem ilegíveis. Ou seja, o que o OCR
estraga é justamente a palavra de terceiro.

Por isso: use o texto reconhecido para **localizar** e para **entender a tese**.
**Nunca reproduza citação literal a partir de página de OCR sem conferir no
PDF** — e diga ao advogado que conferiu, ou que não conferiu.

O SEGUNDO RISCO, QUE VALE SÓ PARA UM CORPUS: O PRAZO

As 884 Manifestações Jurídicas Referenciais das Consultorias Jurídicas dos
Ministérios têm **prazo de validade**, e isso não existe no resto do acervo. Um
referencial dispensa a análise jurídica individualizada dos processos da classe
que descreve; **vencido, não dispensa nada**, e invocá-lo para dispensar parecer
é vício no processo administrativo.

Medido na coleta: das 823 com prazo declarado, **463 já estavam vencidas** — mais
da metade. E o texto de uma vencida é idêntico ao de uma válida.

Use `manifestacoes_referenciais`, que separa em vigor, vencidas e sem prazo
declarado, e calcula o vencimento contra a data de HOJE. Nunca apresente
referencial vencido como fundamento de dispensa: ele serve como argumento e como
histórico do entendimento, não como dispensa.

Sem prazo declarado não é prazo indeterminado. Nesses casos, mande conferir no
próprio parecer.

DUAS ARMADILHAS DE ATRIBUIÇÃO E DE CONTAGEM

**`CONUNI` não é autor.** Na fonte, essa sigla é o rótulo do que não foi
atribuído a nenhuma Câmara Temática: 1.471 documentos de 2007 a 2026, dos quais
**1.416 são do DECOR**, o Departamento de Coordenação e Orientação de Órgãos
Jurídicos. Não escreva "1.471 manifestações da CONUNI". E não chame a CONUNI de
extinta: a extinta é a **CNU**, Câmara Nacional de Uniformização, cujas sete ONs
estão marcadas à parte.

**As citações mapeadas não são internas.** Das 9.706, apenas 1.013 são
manifestações da própria AGU; 7.916 são normas, 377 acórdãos, 271 súmulas e 129
Orientações Normativas.

VIGÊNCIA

Ao contrário do acervo da PGE-RJ, aqui a fonte declara a situação do ato: ONs
canceladas, revogadas e com nova redação vêm marcadas, e o CONUNI nomeia a
manifestação revogadora. Quando houver `ressalvas_de_vigencia`, o documento NÃO
pode ser apresentado como fundamento sem ler o ato indicado — por mais que o
texto pareça responder à pergunta.

Ausência de ressalva significa que a fonte nada declarou na data da coleta, e
não que o ato esteja íntegro: revogação tácita, norma superveniente e decisão
judicial ficam fora. `situacao_do_ato` devolve o que a fonte publicou, nunca uma
garantia de vigência.

REGIME DE LICITAÇÃO

Boa parte do acervo é anterior à Lei 14.133/2021. Cada documento traz `regime` e,
quando cabível, `alerta_regime`. Nunca responda pergunta de Lei 14.133 com
manifestação de regime 8.666 sem declarar isso. A tese pode sobreviver ao novo
regime — quem afirma que sobrevive é o advogado, depois de conferir.

**`regime` ausente não é regime neutro.** Muitas ONs enunciam a regra sem citar
lei nenhuma, e aí nem a etiqueta da AGU nem a leitura do texto conseguem
situá-la. A ON 50/2014, sobre acréscimos e supressões contratuais, é o exemplo:
a AGU etiquetou as vizinhas 44, 45, 48 e 49 e deixou a 50 sem etiqueta — e
justamente nesse tema o regime é a pergunta inteira (art. 65 da 8.666 contra
art. 125 da 14.133). Quando `regime` vier nulo num tema em que a lei mudou,
**diga que o acervo não sabe**, em vez de omitir.
""".strip()


def _caminho_padrao() -> Path:
    do_ambiente = os.environ.get("AGU_BANCO")
    if do_ambiente:
        return Path(do_ambiente)
    local = Path(__file__).resolve().parent.parent / "dados" / "agu_consultivo.db"
    if local.exists():
        return local
    return Path(os.path.expanduser(
        "~/Documents/AGU_Acervo_Consultivo/agu_consultivo.db"))


def construir(banco: str | None = None, dominios: list[str] | None = None,
              **ajustes: Any) -> FastMCP:
    acervo = Acervo(banco or _caminho_padrao())

    mcp = FastMCP(
        "Consultivo AGU",
        instructions=INSTRUCOES,
        transport_security=seguranca_de_transporte(dominios),
        **ajustes,
    )

    @mcp.tool()
    def pesquisar_manifestacoes(consulta: str, limite: int = 10,
                                ano_minimo: int | None = None,
                                ano_maximo: int | None = None,
                                camara: str | None = None,
                                vinculacao: str | None = None) -> dict[str, Any]:
        """Procura na ementa, no assunto e no enunciado — o resumo oficial, com a
        tese já destilada. Use primeiro; é a via mais precisa.

        `camara` filtra pela Câmara Nacional: CNLCA (licitações e contratos),
        CNCIC (convênios), CNMLC (modelos), CNPAT (patrimônio), CNASP (servidor),
        CNPAD (disciplinar), CNDE (eleitoral), CNIR, CNPDI, CNS, CNU, CONUNI.

        `vinculacao` filtra pelo alcance declarado: "administracao_federal",
        "agu", "cgu", "processo".
        """
        achados, expressao, total = acervo.pesquisar(
            consulta, limite=limite, ano_min=ano_minimo, ano_max=ano_maximo,
            orgao=camara, vinculacao=vinculacao)
        criterio = "todos os termos"
        if not achados:
            achados, expressao, total = acervo.pesquisar(
                consulta, limite=limite, ano_min=ano_minimo, ano_max=ano_maximo,
                orgao=camara, vinculacao=vinculacao, operador="OR")
            criterio = "qualquer termo (a busca com todos não devolveu nada)"
        return {
            "expressao_executada": expressao,
            "criterio": criterio,
            "total_encontrado": total,
            "exibindo": len(achados),
            "resultados": [d.para_dict() for d in achados],
            "aviso_ente": AVISO_ENTE,
            "nota": ("Nem com todos os termos nem com qualquer um deles houve "
                     "resultado. Chame expandir_consulta e refaça com as variantes. "
                     "Lembre que 1.115 manifestações não têm inteiro teor público: "
                     "ausência aqui não prova que a AGU não se pronunciou.")
            if not achados else None,
        }

    @mcp.tool()
    def o_que_vincula(consulta: str, limite: int = 10) -> dict[str, Any]:
        """Procura só no que tem força normativa, em ordem de autoridade: os
        pareceres vinculantes do Advogado-Geral aprovados pelo Presidente da
        República, as Orientações Normativas, as Súmulas e as manifestações de
        alcance declarado sobre toda a Administração Federal.

        É a primeira pergunta a fazer sobre qualquer tema: existe enunciado
        vinculante? Havendo, o parecer isolado vira reforço, não fundamento.
        """
        def buscar(**filtro):
            achados, expressao, total = acervo.pesquisar(consulta, limite=limite, **filtro)
            return achados, expressao, total

        vinc, expressao, total_vinc = buscar(fonte="vinculante")
        ons, _, total_on = buscar(fonte="on")
        sums, _, total_sum = buscar(fonte="sumula")
        federal, _, total_fed = buscar(vinculacao="administracao_federal")
        criterio = "todos os termos"
        # O enunciado normativo é curto e a pergunta do advogado é longa: exigir
        # todos os termos numa ON de uma linha não acha nada. "prorrogação de
        # contrato de serviço contínuo" não casava a ON 1/2009, que diz
        # exatamente isso com outras palavras. Sem este segundo passe a
        # ferramenta falha justamente no caso que ela existe para responder.
        if not (vinc or ons or sums or federal):
            criterio = "qualquer termo (a busca com todos não devolveu nada)"
            vinc, expressao, total_vinc = buscar(fonte="vinculante", operador="OR")
            ons, _, total_on = buscar(fonte="on", operador="OR")
            sums, _, total_sum = buscar(fonte="sumula", operador="OR")
            federal, _, total_fed = buscar(
                vinculacao="administracao_federal", operador="OR")
        federal = [d for d in federal if d.fonte == "conuni"]
        return {
            "expressao_executada": expressao,
            "criterio": criterio,
            # Em primeiro lugar o que obriga toda a Administração Federal:
            # havendo parecer vinculante sobre o tema, o resto é reforço.
            "pareceres_vinculantes": [d.para_dict() for d in vinc],
            "orientacoes_normativas": [d.para_dict() for d in ons],
            "sumulas": [d.para_dict() for d in sums],
            "manifestacoes_de_alcance_federal": [d.para_dict() for d in federal],
            # No segundo passe a busca é por QUALQUER termo, e "de" ou "contrato"
            # alcançam quase tudo. O total deixa de medir pertinência, e dizer
            # "86 súmulas sobre o tema" seria falso: são as 86 que existem.
            ("totais" if criterio == "todos os termos" else
             "alcancados_pela_busca_ampliada"): {
                "pareceres_vinculantes": total_vinc,
                "orientacoes_normativas": total_on, "sumulas": total_sum,
                "manifestacoes_de_alcance_federal": total_fed},
            "leitura_dos_totais": None if criterio == "todos os termos" else (
                "A busca com todos os termos não devolveu nada e foi refeita com "
                "qualquer um deles. Os números acima são o alcance da busca "
                "ampliada, não a quantidade de atos pertinentes — leia os "
                "primeiros resultados, que são os mais próximos, e descarte o resto."),
            "aviso_ente": AVISO_ENTE,
            "nota": ("Nada com força normativa sobre este tema no acervo. Isso não "
                     "significa que a AGU não tenha se pronunciado — significa que "
                     "não há enunciado uniformizador publicado. Procure em "
                     "pesquisar_manifestacoes.")
            if not (vinc or ons or sums or federal) else
            ("Havendo parecer vinculante sobre o tema, ele é o fundamento e o "
             "resto é reforço. Verifique as ressalvas de vigência antes de "
             "citar: a fonte marca ON cancelada, revogada e com nova redação."),
        }

    @mcp.tool()
    def manifestacoes_referenciais(consulta: str, limite: int = 10,
                                   orgao: str | None = None,
                                   so_em_vigor: bool = False) -> dict[str, Any]:
        """Manifestações Jurídicas Referenciais das Consultorias Jurídicas dos
        Ministérios, SEPARADAS pelo prazo de validade.

        Um parecer referencial dispensa a análise jurídica individualizada dos
        processos da classe que descreve — mas só dentro do prazo. Vencido, não
        dispensa nada, e invocá-lo para dispensar parecer é vício no processo.

        O vencimento é calculado contra a data de hoje, não contra a data em que
        o acervo foi construído.
        """
        return acervo.referenciais(consulta, limite=limite, orgao=orgao,
                                   so_validos=so_em_vigor)

    @mcp.tool()
    def pesquisar_inteiro_teor(consulta: str, limite: int = 8,
                               paginas_por_documento: int = 3,
                               ano_minimo: int | None = None,
                               ano_maximo: int | None = None,
                               excluir_relatorio: bool = False) -> dict[str, Any]:
        """Procura dentro do texto das manifestações e devolve A PÁGINA, com a
        seção e o grau de transcrição. É onde está a fundamentação — e onde mora
        o risco de atribuir à AGU palavra de terceiro.

        Alcança apenas os documentos com inteiro teor público. Os demais só são
        pesquisáveis por ementa.
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
            "resultados": [d.para_dict() for d in achados],
            "lembrete": ("Verifique secao e transcricao_percent antes de atribuir "
                         "qualquer trecho à AGU. E lembre que esta busca só alcança "
                         "os documentos com inteiro teor público."),
        }

    @mcp.tool()
    def ler_paginas(id: int, pagina_inicial: int, quantidade: int = 3) -> dict[str, Any]:
        """Lê páginas contíguas de uma manifestação, para ver o contexto ao redor
        de um trecho encontrado. Máximo de 10 por chamada."""
        d = acervo.obter(id)
        if not d:
            return {"erro": f"documento {id} não encontrado"}
        return {
            "id": id,
            "citacao": d.citacao,
            "total_de_paginas": d.paginas,
            "vinculacao_declarada": d.vinculacao or d.grupo,
            "regime": d.regime,
            "alerta_regime": d.alerta_vigencia or None,
            "paginas": acervo.paginas_do_documento(id, pagina_inicial, quantidade),
            "url_inteiro_teor": d.url_inteiro_teor or None,
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
                     "sinônimos próprios do vocabulário administrativo federal.")
            if not conceitos else
            ("Refaça a busca com as variantes de maior contagem. Elas se somam: "
             "os conjuntos raramente coincidem."),
        }

    @mcp.tool()
    def obter_documento(id: int) -> dict[str, Any]:
        """Ficha completa de uma manifestação, ON ou súmula: ementa, alcance
        declarado, ressalvas de vigência, cadeia de despachos e links."""
        d = acervo.obter(id)
        if not d:
            return {"erro": f"documento {id} não encontrado"}
        ficha = d.para_dict()
        ficha["aviso_ente"] = AVISO_ENTE
        return ficha

    @mcp.tool()
    def quem_citou(referencia: str, limite: int = 25) -> dict[str, Any]:
        """Quem, no acervo, cita uma norma, súmula, Orientação Normativa ou
        acórdão. Do mais recente para o mais antigo — o que aconteceu por último
        é o que decide."""
        return acervo.quem_citou(referencia, limite=limite)

    @mcp.tool()
    def situacao_do_ato(ato: str) -> dict[str, Any]:
        """O que a fonte DECLARA sobre o estado de uma ON, súmula ou manifestação:
        cancelamento, revogação, nova redação, reanálise.

        Não responde "está em vigor" — devolve o que a AGU publicou, na data da
        coleta. Chame antes de apresentar qualquer ato como fundamento.
        """
        return acervo.situacao_do_ato(ato)

    @mcp.tool()
    def listar_documentos(fonte: str | None = None, ano: int | None = None,
                          camara: str | None = None, vinculacao: str | None = None,
                          so_com_inteiro_teor: bool = False,
                          so_com_ressalva_de_vigencia: bool = False,
                          limite: int = 30) -> dict[str, Any]:
        """Varredura por ano, câmara, fonte ou grau de vinculação.

        `fonte`: "conuni", "on" ou "sumula".
        `so_com_ressalva_de_vigencia=True` lista o que a fonte marcou como
        cancelado, revogado ou de redação alterada — o que não se pode citar sem
        ler o ato novo.
        """
        achados = acervo.listar(
            fonte=fonte, ano=ano, orgao=camara, vinculacao=vinculacao,
            so_com_inteiro_teor=so_com_inteiro_teor,
            so_com_ressalva=so_com_ressalva_de_vigencia, limite=limite)
        return {
            "exibindo": len(achados),
            "camaras_disponiveis": CAMARAS,
            "resultados": [d.para_dict(com_texto=False) for d in achados],
            "aviso_ente": AVISO_ENTE,
        }

    @mcp.tool()
    def cobertura_do_acervo() -> dict[str, Any]:
        """Volumes, período, distribuição por grau de vinculação e os limites
        declarados. Chame antes de afirmar que algo não existe no acervo."""
        return acervo.cobertura()

    return mcp
