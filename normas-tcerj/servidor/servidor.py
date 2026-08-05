"""Servidor MCP do acervo normativo do TCE-RJ."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .acervo import ROTULOS, Acervo

_LOCAIS = ["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*"]

INSTRUCOES = """
Acervo normativo do Tribunal de Contas do Estado do Rio de Janeiro: as
Deliberações, Resoluções, Atos Normativos, Portarias, Notas Técnicas e Súmulas
publicados no Portal de Normas e Publicações do próprio Tribunal, de 1975 em
diante — inclusive o Regimento Interno.

Como responder ao advogado: entregue a norma e a análise, não o funcionamento
da ferramenta. Não cite nomes de tools nem estrutura de URL. Apresente links
como "[Inteiro teor](url)". Chame `cobertura_do_acervo` na primeira consulta e
declare os limites que afetarem a resposta.

A REGRA QUE NÃO PODE SER QUEBRADA: ISTO AINDA VALE?

Num acervo de jurisprudência o risco é a proveniência do trecho. Aqui é a
**vigência**, e ela não está no texto: o PDF de um ato revogado é igual, em
tudo, ao de um ato em vigor. Medido nesta base: **um quarto dos atos está
revogado**.

Por isso todo resultado traz `situacao`, e ela tem três estados:

    vigente                Sem revogação registrada na fonte.
    revogado               A fonte registra quem revogou e quando.
    revogado_tacitamente   A ementa do Tribunal declara a revogação em
                           prosa, embora o campo estruturado diga vigente.
                           São 16 atos. Não os trate como em vigor.

**Nunca escreva "o ato está em vigor".** Escreva o que a fonte declara e em que
data foi coletada: "sem revogação registrada até a coleta de <data>". A
diferença é entre uma pesquisa e uma garantia — e garantia esta base não dá.

NÃO HÁ TEXTO CONSOLIDADO. NENHUM.

Todo PDF do portal é a **redação original** da data de publicação. Alteração
posterior é ato autônomo, e nada no documento alterado avisa que ele mudou.

Isso vale inclusive para o **Regimento Interno**: o arquivo que o portal chama
de Regimento é a Deliberação nº 338/2023, texto de fevereiro de 2023. As
alterações posteriores são deliberações separadas, listadas em
`cobertura_do_acervo`.

Consequência prática, e é obrigatória: **antes de reproduzir qualquer
dispositivo, verifique `situacao.alteracoes_declaradas`.** Havendo alteração,
diga-o na resposta e leia o ato alterador. Citar "o art. 5º dispõe que…" quando
há alteração declarada é reproduzir redação possivelmente superada.

FORÇA DE CADA ESPÉCIE

    Súmula          Enunciado consolidado. Vincula a Administração
                    fluminense no âmbito do controle externo.
    Deliberação     Ato normativo do Plenário. É a espécie do Regimento
                    Interno e das normas de maior alcance.
    Resolução       Organização interna e procedimento.
    Ato Normativo   Ato da Presidência, de alcance interno.
    Portaria        Ato administrativo pontual.
    Nota Técnica    Orientação técnica, sem força normativa própria.

Não trate Portaria ou Nota Técnica como se obrigassem o jurisdicionado.

COMO APRESENTAR CADA ATO — os quatro itens, sempre:

1. **Citação**, no formato do campo `citacao`: espécie, número/ano e data.
2. **Situação**, explicitamente — vigente, revogado ou tacitamente revogado —,
   com a data da coleta. Havendo alteração declarada, diga quantas e quais.
3. **O que o ato dispõe**, com o número da página quando vier do inteiro teor.
4. **Link de conferência**, sempre.

Um dispositivo citado sem situação declarada vale menos do que parece — e pode
valer o contrário.

LIMITES QUE NÃO PODEM SER OMITIDOS

- A **Lei Orgânica do TCE-RJ** (Lei Complementar estadual nº 63/1990) NÃO está
  aqui: é lei da ALERJ, não ato do Tribunal.
- O acervo tem os atos que o portal publica. Ausência aqui não prova que o
  Tribunal nunca normatizou a matéria.
- O Ato Normativo nº 1/1980 traz, no portal, o texto do de 1982 — erro da
  fonte. O texto verdadeiro do ato de 1980 não está disponível.
""".strip()


def seguranca(dominios: list[str] | None) -> TransportSecuritySettings:
    hosts = list(_LOCAIS)
    origens = [f"http://{h}" for h in _LOCAIS if "*" not in h]
    for d in dominios or []:
        limpo = d.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        if limpo:
            hosts += [limpo, f"{limpo}:*"]
            origens.append(f"https://{limpo}")
    if dominios:
        origens += ["https://chatgpt.com", "https://chat.openai.com"]
    return TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                     allowed_hosts=hosts, allowed_origins=origens)


def _caminho() -> Path:
    if os.environ.get("NORMAS_BANCO"):
        return Path(os.environ["NORMAS_BANCO"])
    return Path(__file__).resolve().parent.parent / "dados" / "normas-tcerj.sqlite"


def construir(banco: str | Path | None = None, dominios: list[str] | None = None,
              **ajustes: Any) -> FastMCP:
    acervo = Acervo(banco or _caminho())
    mcp = FastMCP("normas-tcerj", instructions=INSTRUCOES,
                  transport_security=seguranca(dominios), **ajustes)

    def _nota(achados: list[dict[str, Any]]) -> str | None:
        rev = [a for a in achados
               if a["situacao"] and a["situacao"]["estado"] != "vigente"]
        alt = [a for a in achados
               if a["situacao"] and a["situacao"]["alteracoes_declaradas"]]
        partes = []
        if rev:
            partes.append(f"{len(rev)} dos {len(achados)} resultados estão "
                          f"REVOGADOS — veja `situacao` antes de citar.")
        if alt:
            partes.append(f"{len(alt)} têm alteração declarada: o texto do PDF é "
                          f"a redação original.")
        return " ".join(partes) or None

    @mcp.tool()
    def pesquisar_atos(consulta: str, especie: str | None = None,
                       apenas_vigentes: bool | None = None,
                       limite: int = 15) -> dict[str, Any]:
        """Procura atos normativos do TCE-RJ pela ementa.

        Use para descobrir QUAIS atos tratam de um assunto. Para o texto do
        dispositivo, use `pesquisar_dispositivos`.

        Args:
            consulta: palavras ou expressão entre aspas.
            especie: deliberacao, resolucao, ato-normativo, portaria,
                nota-tecnica, sumula.
            apenas_vigentes: True traz só os sem revogação registrada; False,
                só os revogados; omitido, todos. Prefira omitir e ler a
                situação de cada um — um ato revogado pode ser exatamente o
                que se procura, quando os fatos são da época dele.
            limite: quantos devolver (máximo 50).
        """
        achados, parcial, expressao = acervo.pesquisar(
            consulta, especie=especie, vigentes=apenas_vigentes, limite=limite)
        return {
            "consulta": consulta, "expressao_executada": expressao,
            "quantidade": len(achados), "correspondencia_parcial": parcial,
            "resultados": achados,
            "coletado_em": acervo.coletado_em,
            "observacao": _nota(achados) or (
                "Nenhum resultado. Isso não prova que o Tribunal não normatizou "
                "a matéria: tente outra formulação antes de concluir."
                if not achados else None),
        }

    @mcp.tool()
    def pesquisar_dispositivos(consulta: str, especie: str | None = None,
                               apenas_vigentes: bool | None = None,
                               limite: int = 12) -> dict[str, Any]:
        """Procura dentro do TEXTO dos atos, e devolve a página.

        É onde estão os artigos. Cada resultado traz a página, para conferência
        no documento oficial, e a situação do ato — sem a qual o dispositivo
        não pode ser citado.

        Args:
            consulta: palavras ou expressão entre aspas.
            especie: filtra a espécie.
            apenas_vigentes: ver `pesquisar_atos`.
            limite: quantos trechos devolver (máximo 30).
        """
        achados, parcial, expressao = acervo.pesquisar_texto(
            consulta, especie=especie, vigentes=apenas_vigentes, limite=limite)
        return {
            "consulta": consulta, "expressao_executada": expressao,
            "quantidade": len(achados), "correspondencia_parcial": parcial,
            "resultados": achados,
            "coletado_em": acervo.coletado_em,
            "lembrete": ("O trecho é a redação ORIGINAL do ato. Havendo "
                         "alteração em `situacao.alteracoes_declaradas`, ela "
                         "não está aplicada aqui."),
            "observacao": _nota(achados),
        }

    @mcp.tool()
    def situacao_do_ato(id: str) -> dict[str, Any]:
        """Vigência de um ato: revogado, alterado, ou sem registro.

        Etapa obrigatória antes de citar qualquer dispositivo.

        Args:
            id: identificador vindo de uma pesquisa (ex.: deliberacao-338-2023).
        """
        ato = acervo.obter(id)
        if not ato:
            return {"erro": f"Ato não encontrado: {id}"}
        return {
            "citacao": ato["citacao"],
            "ementa": ato["ementa"],
            "situacao": ato["situacao"],
            "revogou": acervo.revogados_por(id),
            "url_documento": ato["url_documento"],
            "coletado_em": acervo.coletado_em,
            "como_afirmar": (
                "Diga qual é a situação declarada na fonte E a data da coleta. "
                "Não escreva 'está em vigor': escreva 'sem revogação registrada "
                f"até a coleta de {acervo.coletado_em}'."),
        }

    @mcp.tool()
    def historico_do_ato(id: str) -> dict[str, Any]:
        """A cadeia de um ato: o que ele revogou e o que o alterou.

        Serve para reconstituir o regime aplicável na data dos fatos — que
        raramente é o de hoje.

        Args:
            id: identificador do ato.
        """
        ato = acervo.obter(id)
        if not ato:
            return {"erro": f"Ato não encontrado: {id}"}
        s = ato["situacao"] or {}
        return {
            "citacao": ato["citacao"],
            "publicado_em": ato["data"],
            "revogou": acervo.revogados_por(id),
            "alterado_por": s.get("alteracoes_declaradas", []),
            "revogado_por": s.get("revogado_por"),
            "revogado_em": s.get("revogado_em"),
            "estado": s.get("estado"),
            "aviso": ("A cadeia é a que a fonte declara. Alterações que o "
                      "Tribunal não registrou na ementa não aparecem aqui, e "
                      "esta base não as detecta."),
        }

    @mcp.tool()
    def ler_paginas(id: str, pagina: int, vizinhas: int = 1) -> dict[str, Any]:
        """Lê páginas contíguas do ato, para ver o dispositivo no contexto.

        Args:
            id: identificador do ato.
            pagina: página central.
            vizinhas: quantas antes e depois (até 8).
        """
        v = max(0, min(vizinhas, 8))
        paginas = acervo.paginas(id, pagina - v, pagina + v)
        if not paginas:
            return {"erro": f"Sem texto para {id} na página {pagina}."}
        ato = acervo.obter(id)
        return {
            "citacao": ato["citacao"] if ato else id,
            "situacao": ato["situacao"] if ato else None,
            "url_documento": ato["url_documento"] if ato else None,
            "paginas": paginas,
            "lembrete": "Redação original. Confira as alterações declaradas.",
        }

    @mcp.tool()
    def obter_ato(id: str) -> dict[str, Any]:
        """Ficha completa de um ato já localizado.

        Args:
            id: identificador vindo de uma pesquisa.
        """
        ato = acervo.obter(id)
        return ato or {"erro": f"Ato não encontrado: {id}"}

    @mcp.tool()
    def listar_atos(especie: str | None = None, ano: int | None = None,
                    apenas_vigentes: bool | None = None,
                    limite: int = 30) -> dict[str, Any]:
        """Lista atos por espécie, ano ou vigência, sem termo de busca.

        Args:
            especie: deliberacao, resolucao, ato-normativo, portaria,
                nota-tecnica, sumula.
            ano: ano exato de publicação.
            apenas_vigentes: True, False ou omitido.
            limite: quantos devolver (máximo 100).
        """
        achados = acervo.listar(especie=especie, ano=ano,
                                vigentes=apenas_vigentes, limite=limite)
        return {"quantidade": len(achados), "resultados": achados,
                "observacao": _nota(achados)}

    @mcp.tool()
    def cobertura_do_acervo() -> dict[str, Any]:
        """O que existe na base: espécies, período, revogados e limites.

        Consulte na primeira pesquisa da sessão, e antes de afirmar que algo
        não consta.
        """
        return acervo.cobertura()

    # -- fachada para os conectores do ChatGPT ----------------------------

    @mcp.tool()
    def search(query: str) -> dict[str, Any]:
        """Search TCE-RJ normative acts by keyword.

        Args:
            query: words to look for.
        """
        achados, _, _ = acervo.pesquisar(query, limite=15)
        return {"results": [
            {"id": a["id"], "title": a["citacao"],
             "text": f"[{a['situacao']['estado'].upper()}] {a['ementa'] or ''}"[:400],
             "url": a["url_documento"] or a["url_portal"]}
            for a in achados]}

    @mcp.tool()
    def fetch(id: str) -> dict[str, Any]:
        """Fetch a TCE-RJ normative act by its id.

        Args:
            id: identifier returned by `search`.
        """
        a = acervo.obter(id)
        if not a:
            return {"id": id, "title": "não encontrado", "text": "", "url": "",
                    "metadata": {}}
        paginas = acervo.paginas(id, 1, 9999)
        return {
            "id": a["id"], "title": a["citacao"],
            "text": "\n\n".join(p["texto"] for p in paginas) or (a["ementa"] or ""),
            "url": a["url_documento"] or a["url_portal"],
            "metadata": {
                "especie": a["especie"],
                "situacao": a["situacao"]["estado"],
                "aviso": a["situacao"]["aviso"],
                "data": a["data"] or "",
                "coletado_em": acervo.coletado_em,
                "fonte": "TCE-RJ — Portal de Normas e Publicações",
            },
        }

    return mcp
