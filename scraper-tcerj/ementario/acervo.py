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
    ) -> tuple[list[Resultado], bool]:
        """Busca por relevância. Devolve (resultados, houve_abrandamento).

        Tenta primeiro exigir todos os termos. Não achando nada, repete
        aceitando qualquer um deles: é preferível devolver o precedente mais
        próximo, avisando que a correspondência foi parcial, a devolver vazio
        porque a pergunta trazia uma palavra a mais.
        """
        for operador in ("AND", "OR"):
            expressao = montar_consulta_fts(consulta, operador)
            if not expressao:
                return [], False
            achados = self._consultar(
                expressao, especie, ano_min, ano_max, relator, limite
            )
            if achados:
                return achados, operador == "OR"
        return [], False

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
    ) -> tuple[list[Trecho], bool]:
        """Procura nas páginas do inteiro teor, e não nas ementas.

        A ementa é o resumo oficial; o voto é onde a tese é construída e
        fundamentada. Separar as duas buscas é deliberado: saber se a
        proposição veio de uma ou de outra é informação jurídica, não detalhe
        de implementação.
        """
        for operador in ("AND", "OR"):
            expressao = montar_consulta_fts(consulta, operador)
            if not expressao:
                return [], False
            achados = self._consultar_paginas(
                expressao, especie, ano_min, ano_max, relator, limite
            )
            if achados:
                return achados, operador == "OR"
        return [], False

    def _consultar_paginas(
        self,
        expressao: str,
        especie: str | None,
        ano_min: int | None,
        ano_max: int | None,
        relator: str | None,
        limite: int,
    ) -> list[Trecho]:
        sql = [
            "SELECT d.*, f.pagina, p.folha,",
            "       snippet(paginas_fts, 2, '\x02', '\x03', ' … ', 32) AS trecho",
            "FROM paginas_fts f",
            "JOIN documentos d ON d.id = f.documento_id",
            "JOIN paginas p ON p.documento_id = f.documento_id AND p.pagina = f.pagina",
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
            base = self._resultado(linha, "")
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
        casou frequentemente mostra a conclusão sem a premissa.
        """
        linhas = self.conexao.execute(
            "SELECT pagina, folha, texto FROM paginas "
            "WHERE documento_id = ? AND pagina BETWEEN ? AND ? ORDER BY pagina",
            (identificador, inicio, fim),
        ).fetchall()
        return [
            {"pagina": l["pagina"], "folha": l["folha"], "texto": l["texto"]}
            for l in linhas
        ]

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

        return {
            "total_de_documentos": total,
            "por_especie": especies,
            "relatores": relatores,
            "macro_temas": macro_temas,
            "limites_do_acervo": [
                "A base de acórdãos é a Jurisprudência Selecionada do TCE-RJ: ementas "
                "escolhidas pelo Serviço de Jurisprudência, NÃO o conjunto de todos os "
                "acórdãos do Tribunal. Não afirme que uma tese inexiste só por não "
                "constar aqui.",
                "Não há inteiro teor de votos ou acórdãos: o que existe é a ementa "
                "(descritores + tese).",
                "Deliberações e Resoluções não estão no acervo — o TCE-RJ as publica "
                "em atosoficiais.com.br, fora deste portal.",
                "Os endpoints do Tribunal não devolvem link por documento; a URL "
                "apontada é a tela pública de consulta da espécie.",
            ],
        }

    # -- montagem ---------------------------------------------------------

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
