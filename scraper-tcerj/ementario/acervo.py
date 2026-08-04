"""Leitura do acervo coletado: consulta textual, filtros e cobertura.

Este módulo só lê. O banco é aberto em modo somente-leitura porque quem o
consome é um modelo de linguagem, e uma ferramenta de pesquisa não tem por que
poder alterar o acervo.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Espécies como estão gravadas, com o rótulo que o advogado reconhece.
ROTULOS = {
    "acordao": "Acórdão",
    "sumula": "Súmula",
    "enunciado": "Enunciado",
    "deliberacao": "Deliberação",
    "resolucao": "Resolução",
    "decisao": "Decisão",
    "parecer_previo": "Parecer Prévio",
    "resposta_consulta": "Resposta a Consulta",
    "voto": "Voto",
    "indefinido": "Questão de Ordem/outros",
}

# Endereços de conferência, levantados contra o portal em 25/07/2026.
#
# O PDF traz o acórdão com o voto integral — é o documento que se confere antes
# de citar. A listagem de jurisprudência não devolve esse link; ele se monta a
# partir do número e do ano, que já vêm na coleta.
URL_PDF_ACORDAO = (
    "https://www.tcerj.tc.br/documento-webapi-externo/api/documento/acordao/"
    "{numero}/{ano}?votoInteiro=true"
)
# A consulta processual aceita o número completo na query string. O formato é o
# do Tribunal, mas sem os pontos de milhar: 207656-8/2026.
URL_PROCESSO = (
    "https://www.tcerj.tc.br/consulta-processo/Processo/List?numeroProcesso={processo}"
)

# Páginas públicas de onde cada espécie foi extraída — a tela de consulta serve
# de referência quando não há documento próprio (caso das súmulas).
PORTAIS = {
    "acordao": "https://www.tcerj.tc.br/cadastro-publicacoes/public/jurisprudencia-selecionada",
    "sumula": "https://www.tcerj.tc.br/cadastro-publicacoes/public/sumulas",
    "resposta_consulta": "https://www.tcerj.tc.br/cadastro-publicacoes/public/consultas",
    "indefinido": "https://www.tcerj.tc.br/cadastro-publicacoes/public/questao-ordem",
}
PORTAL_PADRAO = "https://www.tcerj.tc.br/cadastro-publicacoes/public/portal-jurisprudencia"

# Rastros literais de dissenso dentro de um mesmo julgamento.
#
# Medido nos 1.471 acórdãos com inteiro teor: "voto vencido" aparece em 0,8%,
# "voto divergente" em 0,1%, "redator" em 0,5%. São raros porque no TCE-RJ a
# divergência quase nunca se manifesta como dissenso interno — ela aparece como
# o Tribunal decidindo diferente em anos diferentes, sem declarar que mudou.
# Por isso estes sinais servem para APONTAR divergência, nunca para negá-la.
#
# Ficou de fora "divergindo": casa em 8,1% dos acórdãos, mas quase sempre em
# "divergindo do parecer do Ministério Público" — divergência com o órgão
# instrutor, não entre precedentes.
SINAIS_DE_DISSENSO = [
    ("voto vencido", "houve voto vencido"),
    ("voto divergente", "houve voto divergente"),
    ("vencido o Conselheiro", "conselheiro vencido"),
    ("redator para o acórdão", "relator vencido; acórdão redigido por outro"),
    ("pedido de vista", "houve pedido de vista"),
    ("embargos", "a decisão foi embargada"),
]

# Palavras que o FTS5 interpreta como operador e que, vindas de uma frase em
# português, quase sempre são apenas parte da busca.
_OPERADORES = {"and", "or", "not", "near"}

# Quem consulta é um modelo de linguagem, que manda a pergunta inteira ("posso
# exigir visita técnica em licitação?"). Com todos os termos ligados por E,
# basta um "posso" para zerar o resultado. Estas palavras são descartadas —
# nenhuma delas distingue uma ementa de outra.
_VAZIAS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos", "e",
    "em", "entre", "essa", "esse", "esta", "este", "eh", "existe", "existem",
    "foi", "ha", "isso", "meu", "minha", "na", "nas", "no", "nos", "num", "numa",
    "o", "os", "ou", "para", "pela", "pelo", "por", "pode", "podem", "posso",
    "qual", "quais", "quando", "que", "quem", "se", "sem", "ser", "sao", "seu",
    "sob", "sobre", "sua", "tem", "ter", "um", "uma", "uns", "umas",
    # Verbos que estruturam a pergunta sem carregar conceito. Ficam de fora
    # desta lista, de propósito, os que PARECEM verbos de formulação mas são o
    # que se procura: "compensar", "exigível", "autoriza", "responde". Medido:
    # tirá-los devolve resultado de outro assunto — "exigível" sozinho traz
    # "Exigível a Longo Prazo", que é termo contábil.
    "aferir", "cabe", "considera", "deve", "devem", "entra", "faz", "fazer",
    "gostaria", "haver", "justifica", "ocorre", "poderia", "precisa", "preciso",
    "quero",
}


def _sem_acento(texto: str) -> str:
    import unicodedata

    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    ).lower()


def montar_consulta_fts(texto: str, operador: str = "AND") -> str:
    """Traduz uma busca em linguagem natural para a sintaxe do FTS5.

    Cada termo vai entre aspas para que pontuação e operadores acidentais não
    quebrem a consulta — `MATCH` rejeita a expressão inteira com erro de
    sintaxe, e o usuário só veria "a busca falhou". Trechos que o próprio
    usuário aspeou são preservados como expressão exata.
    """
    partes: list[str] = []

    for frase in re.findall(r'"([^"]+)"', texto):
        limpa = frase.replace('"', " ").strip()
        if limpa:
            partes.append(f'"{limpa}"')

    resto = re.sub(r'"[^"]*"', " ", texto)
    livres = [t for t in re.findall(r"[\wÀ-ɏ]+", resto)]
    uteis = [
        t for t in livres
        if _sem_acento(t) not in _VAZIAS and _sem_acento(t) not in _OPERADORES
    ]
    # Se sobrou nada, a busca era só palavras vazias: melhor tentar com elas do
    # que devolver consulta em branco.
    partes.extend(f'"{t}"' for t in (uteis or livres))

    return f" {operador} ".join(partes)


def _quase_toda_maiuscula(texto: str) -> bool:
    letras = [c for c in texto if c.isalpha()]
    if not letras:
        return False
    return sum(1 for c in letras if c.isupper()) / len(letras) > 0.85


def separar_ementa(ementa: str | None) -> tuple[list[str], str]:
    """Divide a ementa em descritores e tese.

    O padrão do TCE-RJ na Jurisprudência Selecionada é uma primeira linha de
    descritores em caixa alta ("LICITAÇÃO. VISITA TÉCNICA. HABILITAÇÃO.")
    seguida da tese em prosa. Separar os dois permite dizer *do que tratou* o
    julgado antes de afirmar *o que ele decidiu* — e evita que a linha de
    indexação seja lida como se fosse o entendimento firmado.

    Nas respostas a consulta a ementa inteira vem em caixa alta; ali não há o
    que separar, e forçar a divisão inventaria uma tese que não existe.
    """
    if not ementa:
        return [], ""
    texto = ementa.strip()
    if _quase_toda_maiuscula(texto):
        return [], texto

    cabeca, _, resto = texto.partition("\n")
    if resto.strip() and _quase_toda_maiuscula(cabeca):
        descritores = [d.strip() for d in cabeca.split(".") if d.strip()]
        return descritores, resto.strip()
    return [], texto


def montar_url_pdf(tipo: str, numero: str | None, ano: int | None) -> str | None:
    """Endereço do PDF do acórdão, quando a espécie tiver um."""
    if tipo != "acordao" or not numero or not ano:
        return None
    return URL_PDF_ACORDAO.format(numero=numero, ano=ano)


def montar_url_processo(processo: str | None) -> str | None:
    """Endereço da consulta processual. O portal não usa ponto de milhar."""
    if not processo:
        return None
    return URL_PROCESSO.format(processo=processo.replace(".", ""))


@dataclass(slots=True)
class Trecho:
    """Uma passagem localizada no inteiro teor, com onde conferi-la."""

    documento: "Resultado"
    pagina: int
    folha: int | None
    trecho: str
    termos: list[str]

    def para_dict(self) -> dict[str, Any]:
        d = self.documento.para_dict()
        # A ementa inteira não interessa aqui: o que se pediu foi a passagem.
        d.pop("ementa", None)
        d.pop("descritores", None)
        d.pop("tese", None)
        return {
            **d,
            "pagina": self.pagina,
            "folha_do_processo": self.folha,
            "trecho": self.trecho,
            "termos_encontrados": self.termos,
            "onde": "inteiro teor (voto/acórdão)",
        }


@dataclass(slots=True)
class Resultado:
    id: str
    tipo: str
    citacao: str
    ementa: str
    trecho: str
    relator: str | None
    processo: str | None
    data_sessao: str | None
    ano: int | None
    assuntos: list[str]
    url_documento: str | None
    url_processo: str | None
    url_portal: str
    # Se o Serviço de Jurisprudência escolheu divulgar este julgado. É a
    # diferença entre orientação que o Tribunal assume e decisão de caso
    # concreto que apenas existe.
    na_curadoria: bool = True

    @property
    def url(self) -> str:
        """O melhor endereço disponível para conferir este documento."""
        return self.url_documento or self.url_processo or self.url_portal

    def para_dict(self) -> dict[str, Any]:
        descritores, tese = separar_ementa(self.ementa)
        return {
            "id": self.id,
            "especie": ROTULOS.get(self.tipo, self.tipo),
            "citacao": self.citacao,
            "trecho": self.trecho,
            "na_jurisprudencia_selecionada": self.na_curadoria,
            "peso_da_fonte": (
                "Ementa da Jurisprudência Selecionada: o Serviço de Jurisprudência "
                "do TCE-RJ escolheu divulgar este julgado como orientação."
                if self.na_curadoria else
                "Acórdão NÃO integra a Jurisprudência Selecionada: foi localizado na "
                "Pesquisa Textual do Tribunal. É decisão de caso concreto, sem ementa "
                "oficial e sem o aval de curadoria — vale como precedente, mas pesa "
                "menos que julgado selecionado, e a tese tem de ser extraída do voto."
            ),
            # Do que tratou o julgado (indexação oficial do Tribunal).
            "descritores": descritores,
            # O que ficou decidido — é isto que fundamenta.
            "tese": tese,
            "ementa": self.ementa,
            "relator": self.relator,
            "processo": self.processo,
            "data_sessao": self.data_sessao,
            "ano": self.ano,
            "assuntos": self.assuntos,
            "url_inteiro_teor": self.url_documento,
            "url_processo": self.url_processo,
            "url_portal": self.url_portal,
        }


class Acervo:
    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)
        if not self.caminho.exists():
            raise FileNotFoundError(
                f"Acervo não encontrado em {self.caminho}. Rode a coleta antes "
                f"(python -m tcerj -c config.json coletar --tipo acordao)."
            )
        self.conexao = sqlite3.connect(
            f"file:{self.caminho.as_posix()}?mode=ro", uri=True, check_same_thread=False
        )
        self.conexao.row_factory = sqlite3.Row

    def fechar(self) -> None:
        self.conexao.close()

    # -- consulta ---------------------------------------------------------

    def pesquisar(
        self,
        consulta: str,
        *,
        especie: str | None = None,
        ano_min: int | None = None,
        ano_max: int | None = None,
        relator: str | None = None,
        limite: int = 10,
    ) -> tuple[list[Resultado], bool, str]:
        """Busca por relevância. Devolve (resultados, abrandou, expressão).

        Tenta primeiro exigir todos os termos. Não achando nada, repete
        aceitando qualquer um deles: é preferível devolver o precedente mais
        próximo, avisando que a correspondência foi parcial, a devolver vazio
        porque a pergunta trazia uma palavra a mais.
        """
        expressao = ""
        for operador in ("AND", "OR"):
            expressao = montar_consulta_fts(consulta, operador)
            if not expressao:
                return [], False, ""
            achados = self._consultar(
                expressao, especie, ano_min, ano_max, relator, limite
            )
            if achados:
                return achados, operador == "OR", expressao
        return [], False, expressao

    def _consultar(
        self,
        expressao: str,
        especie: str | None,
        ano_min: int | None,
        ano_max: int | None,
        relator: str | None,
        limite: int,
    ) -> list[Resultado]:
        sql = [
            "SELECT d.*, snippet(documentos_fts, 1, '', '', ' … ', 28) AS trecho",
            "FROM documentos_fts f JOIN documentos d ON d.id = f.id",
            "WHERE documentos_fts MATCH ?",
        ]
        parametros: list[Any] = [expressao]

        if especie:
            sql.append("AND d.tipo = ?")
            parametros.append(especie)
        if ano_min is not None:
            sql.append("AND d.ano >= ?")
            parametros.append(ano_min)
        if ano_max is not None:
            sql.append("AND d.ano <= ?")
            parametros.append(ano_max)
        if relator:
            sql.append("AND d.relator LIKE ?")
            parametros.append(f"%{relator}%")

        sql.append("ORDER BY rank LIMIT ?")
        parametros.append(max(1, min(limite, 50)))

        linhas = self.conexao.execute(" ".join(sql), parametros).fetchall()
        return [self._resultado(linha, linha["trecho"]) for linha in linhas]

    def obter(self, identificador: str) -> Resultado | None:
        linha = self.conexao.execute(
            "SELECT * FROM documentos WHERE id = ?", (identificador,)
        ).fetchone()
        return self._resultado(linha, linha["ementa"] or "") if linha else None

    def listar(
        self,
        *,
        especie: str | None = None,
        ano: int | None = None,
        relator: str | None = None,
        limite: int = 20,
    ) -> list[Resultado]:
        sql = ["SELECT * FROM documentos WHERE 1=1"]
        parametros: list[Any] = []
        if especie:
            sql.append("AND tipo = ?")
            parametros.append(especie)
        if ano is not None:
            sql.append("AND ano = ?")
            parametros.append(ano)
        if relator:
            sql.append("AND relator LIKE ?")
            parametros.append(f"%{relator}%")
        sql.append("ORDER BY ano DESC, CAST(numero AS INTEGER) DESC LIMIT ?")
        parametros.append(max(1, min(limite, 50)))

        linhas = self.conexao.execute(" ".join(sql), parametros).fetchall()
        return [self._resultado(l, (l["ementa"] or "")[:300]) for l in linhas]

    # -- inteiro teor -----------------------------------------------------

    def pesquisar_paginas(
        self,
        consulta: str,
        *,
        especie: str | None = None,
        ano_min: int | None = None,
        ano_max: int | None = None,
        relator: str | None = None,
        limite: int = 10,
    ) -> tuple[list[Trecho], bool, str]:
        """Procura nas páginas do inteiro teor, e não nas ementas.

        A ementa é o resumo oficial; o voto é onde a tese é construída e
        fundamentada. Separar as duas buscas é deliberado: saber se a
        proposição veio de uma ou de outra é informação jurídica, não detalhe
        de implementação.

        Devolve também a expressão efetivamente executada: uma mesma pergunta
        rende resultados diferentes conforme a formulação, e sem registrar qual
        delas achou cada precedente não há como auditar a pesquisa depois.
        """
        expressao = ""
        for operador in ("AND", "OR"):
            expressao = montar_consulta_fts(consulta, operador)
            if not expressao:
                return [], False, ""
            achados = self._consultar_paginas(
                expressao, especie, ano_min, ano_max, relator, limite
            )
            if achados:
                return achados, operador == "OR", expressao
        return [], False, expressao

    def _consultar_paginas(
        self,
        expressao: str,
        especie: str | None,
        ano_min: int | None,
        ano_max: int | None,
        relator: str | None,
        limite: int,
    ) -> list[Trecho]:
        # O índice tem conteúdo externo: junta-se por rowid, e não por chave.
        # E a página pertence ao documento oficial, do qual pendem uma ou mais
        # ementas — pega-se uma delas para compor a citação, sem multiplicar o
        # mesmo trecho por cada curadoria.
        sql = [
            "SELECT d.*, o.numero AS numero_oficial, o.ano AS ano_oficial,",
            "       o.processo AS processo_oficial, o.tipo AS tipo_oficial,",
            "       p.pagina, p.folha,",
            "       snippet(paginas_fts, 2, '\x02', '\x03', ' … ', 32) AS trecho",
            "FROM paginas_fts f",
            "JOIN paginas p ON p.rowid = f.rowid",
            "JOIN documentos_oficiais o ON o.id = p.documento_id",
            "LEFT JOIN documentos d ON d.id = (",
            "    SELECT x.id FROM documentos x",
            "    WHERE x.tipo = o.tipo AND x.numero = o.numero AND x.ano = o.ano",
            "    ORDER BY x.id LIMIT 1)",
            "WHERE paginas_fts MATCH ?",
        ]
        parametros: list[Any] = [expressao]
        if especie:
            sql.append("AND d.tipo = ?")
            parametros.append(especie)
        if ano_min is not None:
            sql.append("AND d.ano >= ?")
            parametros.append(ano_min)
        if ano_max is not None:
            sql.append("AND d.ano <= ?")
            parametros.append(ano_max)
        if relator:
            sql.append("AND d.relator LIKE ?")
            parametros.append(f"%{relator}%")
        sql.append("ORDER BY rank LIMIT ?")
        parametros.append(max(1, min(limite, 30)))

        achados = []
        for linha in self.conexao.execute(" ".join(sql), parametros):
            # Acórdão fora da curadoria não tem ementa: a citação se monta dos
            # dados do documento oficial. Descartá-lo aqui tornaria invisível
            # justamente o acervo que a Pesquisa Textual acrescentou.
            base = (
                self._resultado(linha, "")
                if linha["id"] is not None
                else self._resultado_sem_ementa(linha)
            )
            bruto = linha["trecho"] or ""
            # Os delimitadores invisíveis marcam o que casou; extraí-los diz ao
            # advogado por que aquele trecho veio, e some do texto exibido.
            termos = sorted({t.lower() for t in re.findall("\x02(.*?)\x03", bruto)})
            achados.append(
                Trecho(
                    documento=base,
                    pagina=linha["pagina"],
                    folha=linha["folha"],
                    trecho=re.sub(r"\s+", " ", bruto.replace("\x02", "").replace("\x03", "")).strip(),
                    termos=termos,
                )
            )
        return achados

    def paginas_do_documento(
        self, identificador: str, inicio: int, fim: int
    ) -> list[dict[str, Any]]:
        """Páginas contíguas de um documento — para ler o argumento inteiro.

        O raciocínio jurídico atravessa a quebra de página; ler só a página que
        casou frequentemente mostra a conclusão sem a premissa. Aceita tanto o
        identificador do documento oficial quanto o de uma de suas ementas.
        """
        oficial = identificador
        registro = self.conexao.execute(
            "SELECT tipo, numero, ano FROM documentos WHERE id = ?", (identificador,)
        ).fetchone()
        if registro and registro["numero"]:
            oficial = f"{registro['tipo']}-{registro['numero']}-{registro['ano']}"

        linhas = self.conexao.execute(
            "SELECT pagina, folha, texto FROM paginas "
            "WHERE documento_id = ? AND pagina BETWEEN ? AND ? ORDER BY pagina",
            (oficial, inicio, fim),
        ).fetchall()
        return [
            {"pagina": l["pagina"], "folha": l["folha"], "texto": l["texto"]}
            for l in linhas
        ]

    # -- súmulas ----------------------------------------------------------

    def sumulas_sobre(self, consulta: str) -> tuple[list[Resultado], bool]:
        """Súmulas pertinentes à consulta. Devolve (achadas, veio_tudo).

        As súmulas do TCE-RJ são poucas — vinte e oito. Quando nenhuma casa por
        palavra, esta função devolve **todas**, e o segundo elemento vem `True`.

        Isso é deliberado. "Não há súmula sobre a matéria" é uma afirmação de
        ausência, e ausência não se prova com busca literal: a súmula pode usar
        vocabulário diverso. Com o conjunto inteiro à vista, quem responde
        confere uma a uma em vez de deduzir do silêncio do índice.
        """
        achadas, _, _ = self.pesquisar(consulta, especie="sumula", limite=28)
        if achadas:
            return achadas, False
        return self.listar(especie="sumula", limite=50), True

    # -- panorama do tema -------------------------------------------------

    def universo(self, expressao: str, *, em_ementas: bool = False) -> int:
        """Quantos documentos casam a expressão, sem limite de resultados.

        A busca devolve uma página; este número é o conjunto de onde ela saiu.
        Sem os dois, contar precedentes engana: dizer "doze julgados nesse
        sentido" tendo examinado doze de quatrocentos descreve a janela da
        busca, e não o Tribunal.

        O denominador tem de vir do mesmo índice que produziu os resultados —
        ementas e páginas de inteiro teor cobrem universos de tamanhos bem
        diferentes, e trocá-los inverteria o sinal de "é amostra".
        """
        if not expressao:
            return 0
        if em_ementas:
            return self.conexao.execute(
                "SELECT COUNT(*) FROM documentos_fts WHERE documentos_fts MATCH ?",
                (expressao,),
            ).fetchone()[0]
        return self.conexao.execute(
            "SELECT COUNT(DISTINCT documento_id) FROM paginas_fts "
            "WHERE paginas_fts MATCH ?", (expressao,)
        ).fetchone()[0]

    def panorama(self, consulta: str, *, ano_min: int | None = None,
                 ano_max: int | None = None) -> dict[str, Any]:
        """Como o tema se distribui no acervo, sem devolver nenhum julgado.

        Responde ao que a leitura de uma página de resultados não responde:
        quantos acórdãos existem sobre isso, em que anos foram julgados,
        quantos o Tribunal escolheu divulgar, e quais trazem rastro de dissenso.

        Nada aqui identifica divergência de teses — para isso é preciso ler os
        votos. O que estes números fazem é dizer QUANTO ficou por ler.
        """
        for operador in ("AND", "OR"):
            expressao = montar_consulta_fts(consulta, operador)
            total = self.universo(expressao)
            if total:
                break
        else:
            return {"consulta": consulta, "acordaos_no_acervo": 0}
        parcial = operador == "OR"

        # Curadoria se mede pela existência de ementa, e não por `status_coleta`
        # — este último só diz se o PDF já foi baixado. Um acórdão descoberto na
        # Pesquisa Textual passa de 'descoberto' a 'ok' assim que é coletado,
        # sem nunca ter entrado na Jurisprudência Selecionada.
        onde = ["SELECT o.ano ano, COUNT(DISTINCT o.id) n,",
                "  EXISTS (SELECT 1 FROM documentos d WHERE d.tipo = o.tipo",
                "          AND d.numero = o.numero AND d.ano = o.ano) sel",
                "FROM paginas_fts f",
                "JOIN paginas p ON p.rowid = f.rowid",
                "JOIN documentos_oficiais o ON o.id = p.documento_id",
                "WHERE paginas_fts MATCH ?"]
        parametros: list[Any] = [expressao]
        if ano_min is not None:
            onde.append("AND o.ano >= ?")
            parametros.append(ano_min)
        if ano_max is not None:
            onde.append("AND o.ano <= ?")
            parametros.append(ano_max)
        onde.append("GROUP BY o.ano, sel")

        por_ano: dict[int, dict[str, int]] = {}
        curados = fora = 0
        for l in self.conexao.execute(" ".join(onde), parametros):
            faixa = por_ano.setdefault(l["ano"], {"ano": l["ano"], "julgados": 0,
                                                  "selecionados": 0})
            faixa["julgados"] += l["n"]
            if l["sel"]:
                curados += l["n"]
                faixa["selecionados"] += l["n"]
            else:
                fora += l["n"]

        # Sinais de dissenso: acórdãos que casam o tema E carregam a marca.
        # Duas subconsultas, cada uma com seu MATCH, cruzadas pelo documento.
        sinais = []
        for marca, rotulo in SINAIS_DE_DISSENSO:
            n = self.conexao.execute(
                "SELECT COUNT(*) FROM ("
                "  SELECT DISTINCT documento_id FROM paginas_fts"
                "  WHERE paginas_fts MATCH ?) a"
                " JOIN (SELECT DISTINCT documento_id FROM paginas_fts"
                "       WHERE paginas_fts MATCH ?) b"
                "   ON a.documento_id = b.documento_id",
                (expressao, f'"{marca}"'),
            ).fetchone()[0]
            if n:
                sinais.append({"sinal": rotulo, "acordaos": n})

        anos = sorted(por_ano.values(), key=lambda f: f["ano"], reverse=True)
        return {
            "consulta": consulta,
            "expressao_executada": expressao,
            "correspondencia_parcial": parcial,
            "acordaos_no_acervo": total,
            "na_jurisprudencia_selecionada": curados,
            "fora_da_curadoria": fora,
            "por_ano": anos,
            "periodo": f"{anos[-1]['ano']}–{anos[0]['ano']}" if anos else None,
            "sinais_de_dissenso": sinais,
            # Sem isto o número engana: nenhum documento reunia todos os termos,
            # então o universo mede a palavra mais comum da consulta, e não o
            # tema. Medido: "zzqqxx inexistente" devolve 103 acórdãos — todos
            # por conta de "inexistente".
            "aviso": (
                "ATENÇÃO: nenhum acórdão reunia todos os termos, e a contagem "
                "caiu para 'qualquer um deles'. Este universo NÃO dimensiona o "
                "tema — mede a palavra mais frequente da consulta. Refaça com "
                "expressão exata entre aspas antes de citar qualquer número."
                if parcial else None
            ),
            "como_ler": (
                "`acordaos_no_acervo` é o universo que casa a expressão; a busca "
                "devolve uma fração dele. Use `por_ano` para ver se o Tribunal "
                "continua decidindo assim ou se o tema esfriou — queda a zero em "
                "anos recentes pede verificação, não conclusão. "
                "`sinais_de_dissenso` aponta acórdãos com rastro de divergência "
                "interna; são raros (menos de 1% do acervo), de modo que a lista "
                "vazia NÃO significa entendimento pacífico."
            ),
        }

    # -- cobertura --------------------------------------------------------

    def cobertura(self) -> dict[str, Any]:
        total = self.conexao.execute("SELECT COUNT(*) FROM documentos").fetchone()[0]
        especies = []
        for linha in self.conexao.execute(
            "SELECT tipo, COUNT(*) n, MIN(ano) a, MAX(ano) b FROM documentos "
            "GROUP BY tipo ORDER BY n DESC"
        ):
            especies.append({
                "especie": ROTULOS.get(linha["tipo"], linha["tipo"]),
                "chave": linha["tipo"],
                "quantidade": linha["n"],
                "periodo": f"{linha['a']}–{linha['b']}" if linha["a"] else None,
            })

        relatores = [
            r[0] for r in self.conexao.execute(
                "SELECT DISTINCT relator FROM documentos WHERE relator IS NOT NULL "
                "ORDER BY relator"
            )
        ]
        temas = [
            r[0] for r in self.conexao.execute(
                "SELECT DISTINCT assuntos FROM documentos "
                "WHERE assuntos NOT IN ('[]','') AND assuntos IS NOT NULL"
            )
        ]
        macro_temas = sorted({t.strip('[]"') for t in temas if t})

        # Duas contagens que não podem ser confundidas: quantos documentos
        # oficiais estão registrados e quantos têm o inteiro teor de fato
        # guardado. A diferença são as pendências.
        com_texto = self.conexao.execute(
            "SELECT COUNT(DISTINCT documento_id) FROM paginas"
        ).fetchone()[0]
        paginas = self.conexao.execute("SELECT COUNT(*) FROM paginas").fetchone()[0]
        caracteres = self.conexao.execute(
            "SELECT COALESCE(SUM(LENGTH(texto)), 0) FROM paginas"
        ).fetchone()[0]
        pendencias = [
            {"situacao": l["status_coleta"], "quantidade": l["n"]}
            for l in self.conexao.execute(
                "SELECT status_coleta, COUNT(*) n FROM documentos_oficiais "
                "WHERE status_coleta <> 'ok' GROUP BY status_coleta"
            )
        ]

        # As duas origens do acervo, que não têm o mesmo peso jurídico. O
        # critério é ter ementa: `status_coleta` diz apenas se o PDF já foi
        # baixado, e usá-lo aqui promoveria a acórdão selecionado todo
        # descoberto que a coleta alcançasse.
        origens = dict(self.conexao.execute(
            "SELECT CASE WHEN EXISTS (SELECT 1 FROM documentos d WHERE d.tipo = o.tipo "
            "  AND d.numero = o.numero AND d.ano = o.ano) THEN 'curadoria' ELSE 'fora' "
            "END, COUNT(*) FROM documentos_oficiais o GROUP BY 1"
        ).fetchall())

        # Período do corpus de inteiro teor, por origem.
        #
        # Declarar só o período das ementas era omissão séria: elas são 6% do
        # acervo, e quem lesse "2021–2026" poderia supor que valia para o
        # resto ou, pior, não supor nada e ficar sem saber. Um acervo que não
        # diz onde começa convida a tratar ausência como inexistência.
        periodos = {
            ("Jurisprudência Selecionada" if l["sel"] else "Pesquisa Textual"): {
                "acordaos": l["n"], "periodo": f"{l['de']}–{l['ate']}",
            }
            for l in self.conexao.execute(
                "SELECT COUNT(*) n, MIN(o.ano) de, MAX(o.ano) ate,"
                "  EXISTS (SELECT 1 FROM documentos d WHERE d.tipo = o.tipo"
                "          AND d.numero = o.numero AND d.ano = o.ano) sel "
                "FROM documentos_oficiais o WHERE o.paginas_total > 0 GROUP BY sel"
            )
        }
        por_ano = [
            {"ano": l["ano"], "acordaos": l["n"]}
            for l in self.conexao.execute(
                "SELECT ano, COUNT(*) n FROM documentos_oficiais "
                "WHERE paginas_total > 0 GROUP BY ano ORDER BY ano"
            )
        ]
        sumulas = self.conexao.execute(
            "SELECT COUNT(*) FROM documentos WHERE tipo = 'sumula'"
        ).fetchone()[0]

        return {
            "ementas": {
                "total": total,
                "por_especie": especies,
                "observacao": "Cada ementa é um ato de curadoria do Tribunal. Um mesmo "
                              "acórdão pode render mais de uma, com teses distintas.",
            },
            "inteiro_teor": {
                "documentos_com_inteiro_teor": com_texto,
                "paginas": paginas,
                "caracteres": caracteres,
                "periodo_por_origem": periodos,
                "acordaos_por_ano": por_ano,
                "pendencias": pendencias,
                "observacao": "Só acórdãos têm inteiro teor. Súmulas, respostas a "
                              "consulta e questões de ordem existem apenas como ementa. "
                              "O período acima é o do corpus textual, e NÃO coincide "
                              "necessariamente com o das ementas: nada anterior ao "
                              "primeiro ano listado foi coletado, e a ausência de um "
                              "julgado antigo é limite da coleta, não do Tribunal.",
            },
            "origem_dos_acordaos": {
                "jurisprudencia_selecionada": origens.get("curadoria", 0),
                "fora_da_curadoria": origens.get("fora", 0),
                "observacao": "A Jurisprudência Selecionada é a curadoria que o Serviço "
                              "de Jurisprudência divulga como orientação. Os demais vêm "
                              "da Pesquisa Textual do Tribunal: são acórdãos reais, sem "
                              "ementa oficial e sem esse aval. Todo resultado declara a "
                              "que origem pertence, em `na_jurisprudencia_selecionada`.",
            },
            "sumulas": {
                "total": sumulas,
                "observacao": "Poucas o bastante para serem lidas por inteiro. Antes de "
                              "dizer que não há súmula sobre a matéria, use `sumulas_sobre` "
                              "— sem casamento por palavra ele devolve todas.",
            },
            "relatores": relatores,
            "macro_temas": macro_temas,
            "alcance_dos_macro_temas": (
                f"Os macro-temas e a lista de relatores descrevem APENAS as {total} "
                f"ementas da curadoria. Os {origens.get('fora', 0)} acórdãos vindos da "
                f"Pesquisa Textual não têm assunto classificado nem relator no registro "
                f"— são recuperáveis por busca textual, não por filtro temático. Não "
                f"conclua, de um macro-tema, que ele cobre o corpus inteiro."
            ),
            # Mantido para quem lia o campo antigo; é o total de ementas.
            "total_de_documentos": total,
            "limites_do_acervo": [
                "O acervo NÃO é o conjunto dos acórdãos do TCE-RJ. Reúne a curadoria da "
                "Jurisprudência Selecionada e o que a Pesquisa Textual alcançou em temas "
                "de licitações e contratos. Não afirme que uma tese inexiste só por não "
                "constar aqui.",
                "Nunca declare pacífico um entendimento por não ter encontrado o "
                "contrário. O que se pode afirmar é o que se leu: 'entre os N acórdãos "
                "que examinei, todos apontam nesse sentido'. Consulte `panorama_do_tema` "
                "para saber quantos ficaram por ler.",
                "O inteiro teor dos acórdãos está disponível e é pesquisável por "
                "`pesquisar_inteiro_teor`, página a página. Não encontrando na ementa, "
                "procure no voto antes de concluir que o Tribunal não se pronunciou.",
                "O inteiro teor reúne, no mesmo documento, a decisão colegiada, o "
                "relatório, as alegações de defesa, a instrução técnica, o parecer do "
                "MPC, precedentes transcritos e o voto. Um trecho isolado pode ser o "
                "oposto do que o Tribunal decidiu: verifique de onde ele vem.",
                "Deliberações e Resoluções não estão no acervo — o TCE-RJ as publica "
                "em atosoficiais.com.br, fora deste portal.",
            ],
        }

    # -- montagem ---------------------------------------------------------

    def _resultado_sem_ementa(self, linha: sqlite3.Row) -> "Resultado":
        """Monta o resultado de um acórdão que não passou pela curadoria.

        Sem ementa não há tese destilada pelo Tribunal, nem relator no
        registro: o que existe é o documento e o que dele se lê. A citação sai
        do próprio acórdão.
        """
        numero = linha["numero_oficial"]
        ano = linha["ano_oficial"]
        processo = linha["processo_oficial"]
        citacao = f"TCE-RJ, Acórdão {numero}/{ano}"
        if processo:
            citacao += f", Processo {processo}"
        return Resultado(
            id=f"acordao-{numero}-{ano}",
            tipo="acordao",
            citacao=citacao,
            ementa="",
            trecho="",
            relator=None,
            processo=processo,
            data_sessao=None,
            ano=ano,
            assuntos=[],
            url_documento=montar_url_pdf("acordao", numero, ano),
            url_processo=montar_url_processo(processo),
            url_portal=PORTAIS.get("acordao", PORTAL_PADRAO),
            na_curadoria=False,
        )

    def _resultado(self, linha: sqlite3.Row, trecho: str) -> Resultado:
        import json

        tipo = linha["tipo"]
        assuntos = json.loads(linha["assuntos"] or "[]")
        return Resultado(
            id=linha["id"],
            tipo=tipo,
            citacao=_citacao(linha),
            ementa=linha["ementa"] or "",
            trecho=re.sub(r"\s+", " ", trecho or "").strip(),
            relator=linha["relator"],
            processo=linha["processo"],
            data_sessao=linha["data_sessao"],
            ano=linha["ano"],
            assuntos=assuntos,
            url_documento=montar_url_pdf(tipo, linha["numero"], linha["ano"]),
            url_processo=montar_url_processo(linha["processo"]),
            url_portal=PORTAIS.get(tipo, PORTAL_PADRAO),
        )


def _citacao(linha: sqlite3.Row) -> str:
    """Referência no formato usado em peça processual."""
    rotulo = ROTULOS.get(linha["tipo"], "Documento")
    base = f"TCE-RJ, {rotulo} {linha['numero'] or 's/n'}"
    if linha["ano"]:
        base += f"/{linha['ano']}"
    if linha["processo"]:
        base += f", Processo {linha['processo']}"
    if linha["relator"]:
        base += f", Rel. {linha['relator']}"
    if linha["data_sessao"]:
        dia, mes, ano = linha["data_sessao"].split("-")[::-1]
        base += f", j. {dia}/{mes}/{ano}"
    return base
