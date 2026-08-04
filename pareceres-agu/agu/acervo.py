"""Acesso ao acervo consultivo da AGU.

O banco é somente leitura: quem coleta e indexa é outro programa. Aqui só se
consulta, e cada resultado carrega o que decide o peso do documento numa peça —
o grau de vinculação declarado, a situação do ato, o regime de licitação e o
link de conferência.
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

AVISO_ENTE = (
    "Acervo federal. Nenhuma manifestação da AGU vincula Estado, Distrito "
    "Federal ou Município — para o ente subnacional é precedente persuasivo.")

ROTULO_SECAO = {
    "relatorio": "relatório (recontagem do que o órgão consulente afirmou)",
    "fundamentacao": "fundamentação",
    "conclusao": "conclusão",
    "indefinida": "seção não identificada",
}

ROTULO_ORIGEM = {
    "pdf": None,
    "pagina_oficial": None,
    "sapiens_exige_autenticacao": (
        "Sem inteiro teor: a AGU publica esta manifestação no Sapiens, cujo "
        "acesso anônimo devolve a tela de login. Há ementa e assunto; a "
        "fundamentação NÃO pode ser conferida por este acervo."),
    "sem_arquivo": (
        "Sem inteiro teor: a consulta pública não indica arquivo para esta "
        "manifestação."),
    "arquivo_publico_indisponivel": (
        "Sem inteiro teor: o arquivo indicado não pôde ser lido."),
    "digitalizacao_sem_texto": (
        "Digitalização sem camada de texto, e o reconhecimento não produziu "
        "nada aproveitável. O inteiro teor existe em imagem, mas não é "
        "pesquisável nem transcrevível."),
    "enunciado_nao_publicado": (
        "A página oficial não reproduz o enunciado deste ato — traz apenas o "
        "título e a situação. Leia o ato pelo link antes de citar."),
}

CAMARAS = {
    "CNLCA": "Câmara Nacional de Licitações e Contratos Administrativos",
    "CNCIC": "Câmara Nacional de Convênios e Instrumentos Congêneres",
    "CNMLC": "Câmara Nacional de Modelos de Licitações e Contratos",
    "CNPAT": "Câmara Nacional de Patrimônio Público",
    "CNASP": "Câmara Nacional de Assuntos de Servidor Público",
    "CNDE": "Câmara Nacional de Direito Eleitoral",
    "CNS": "Câmara Nacional de Sustentabilidade",
    "CNPDI": "Câmara Nacional de Pesquisa, Desenvolvimento e Inovação",
    "CNPAD": "Câmara Nacional de Procedimentos Administrativos Disciplinares",
    "CNIR": "Câmara Nacional de Infraestrutura e Regulação",
    "CNU": "Câmara Nacional de Uniformização (extinta)",
    # ATENÇÃO: na fonte, `CONUNI` NÃO é o órgão que produziu o documento — é o
    # rótulo geral do que não foi atribuído a nenhuma Câmara Temática. São 1.471
    # documentos de 2007 a 2026, dos quais 1.416 são do DECOR. Traduzir a sigla
    # por "Consultoria Nacional da União de Uniformização" fazia o servidor
    # anunciar 1.471 documentos de um órgão que não os produziu.
    "CONUNI": ("órgão não especificado pela fonte — inclui o DECOR e a extinta "
               "CNU, além da própria CONUNI"),
}


def _sem_acento(texto: str) -> str:
    forma = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in forma if unicodedata.category(c) != "Mn")


def montar_consulta_fts(texto: str, operador: str = "AND") -> str:
    """Traduz o que o usuário escreveu numa expressão FTS5 válida.

    Preserva expressões entre aspas e liga o resto pelo operador. Sem isto, um
    apóstrofo ou um hífen viram erro de sintaxe e a consulta falha inteira em
    vez de simplesmente achar menos.
    """
    if not texto or not texto.strip():
        return ""
    termos: list[str] = []
    for pedaco in re.findall(r'"[^"]+"|\S+', texto.strip()):
        if pedaco.startswith('"') and pedaco.endswith('"') and len(pedaco) > 2:
            interno = pedaco[1:-1].replace('"', " ").strip()
            if interno:
                termos.append(f'"{interno}"')
            continue
        limpo = re.sub(r"[^0-9A-Za-zÀ-ÿ*]+", " ", pedaco).strip()
        if not limpo:
            continue
        if limpo.upper() in {"AND", "OR", "NOT", "NEAR"}:
            termos.append(limpo.upper())
            continue
        termos.append(f'"{limpo}"' if " " in limpo else limpo)
    if not termos:
        return ""
    saida: list[str] = []
    for i, t in enumerate(termos):
        if i and t not in {"AND", "OR", "NOT"} and termos[i - 1] not in {"AND", "OR", "NOT"}:
            saida.append(operador)
        saida.append(t)
    return " ".join(saida)


@dataclass
class Trecho:
    codigo: int
    pagina: int
    texto: str
    secao: str
    transcricao: int

    def para_dict(self) -> dict[str, Any]:
        aviso = None
        if self.transcricao >= 50:
            aviso = ("Página majoritariamente composta de transcrição de terceiro "
                     "(doutrina, jurisprudência, norma ou manifestação citada). NÃO "
                     "atribua este trecho à AGU sem ler o contexto ao redor.")
        elif self.secao == "relatorio":
            aviso = ("Trecho no relatório: é a recontagem do que o órgão consulente "
                     "afirmou, não o entendimento da AGU.")
        return {
            "pagina": self.pagina,
            "trecho": self.texto,
            "secao": ROTULO_SECAO.get(self.secao, self.secao or "?"),
            "transcricao_percent": self.transcricao,
            "aviso_proveniencia": aviso,
        }


@dataclass
class Documento:
    codigo: int
    fonte: str
    especie: str | None
    citacao: str | None
    numero: int | None
    ano: int | None
    orgao: str | None
    grupo: str | None
    assunto: str | None
    ementa: str | None
    texto: str | None
    vinculacao: str | None
    vinculacao_chave: str | None
    vinculacao_explicacao: str | None
    vigencia_declarada: str | None
    situacao_declarada: str | None
    ato_revogador: str | None
    ato_reanalise: str | None
    relacionadas: str | None
    aprovacao: str | None
    despachos: str | None
    regime: str | None
    alerta_vigencia: str | None
    paginas: int
    tem_texto: int
    origem_texto: str | None
    ocr_confianca: int | None
    aviso_fonte: str | None
    url_inteiro_teor: str | None
    url_publicacao: str | None
    trechos: list[Trecho] = field(default_factory=list)

    def para_dict(self, com_texto: bool = True) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.codigo,
            "citacao": self.citacao,
            "especie": self.especie,
            "ano": self.ano,
            "orgao": CAMARAS.get(self.orgao or "", self.orgao) if self.orgao else self.grupo,
            "vinculacao_declarada": self.vinculacao or self.grupo,
            "alcance": self.vinculacao_explicacao,
        }
        if self.assunto:
            d["assunto"] = self.assunto
        if self.ementa:
            d["ementa"] = self.ementa
        if com_texto and self.texto:
            d["texto"] = self.texto

        ressalvas = []
        if self.situacao_declarada:
            ressalvas.append(f"a fonte declara: {self.situacao_declarada}")
        if self.ato_revogador:
            ressalvas.append(f"revogada por {self.ato_revogador}")
        if self.ato_reanalise:
            ressalvas.append(f"reanalisada em {self.ato_reanalise}")
        if self.vigencia_declarada and self.vigencia_declarada not in ("1", "None"):
            ressalvas.append(
                f"marcador de vigência da fonte fora do normal (valor {self.vigencia_declarada})")
        if self.aprovacao and self.aprovacao.upper() not in ("APROVADO",):
            ressalvas.append(f"aprovação: {self.aprovacao}")
        if ressalvas:
            d["ressalvas_de_vigencia"] = ressalvas
            d["aviso_vigencia"] = (
                "Não use como fundamento sem ler o ato indicado: a fonte registra "
                "alteração no estado deste documento.")

        if self.regime:
            d["regime"] = self.regime
        if self.alerta_vigencia:
            d["alerta_regime"] = self.alerta_vigencia
        if self.relacionadas:
            d["manifestacoes_relacionadas"] = self.relacionadas
        if self.despachos:
            # O campo guarda a cadeia de despachos no CONUNI e os links do ato
            # nas ONs e súmulas. Rotular tudo de "despacho" faria o servidor
            # anunciar despacho onde não há.
            rotulo = "despachos" if self.fonte == "conuni" else "links_do_ato"
            try:
                d[rotulo] = json.loads(self.despachos)
            except json.JSONDecodeError:
                pass
        if self.paginas:
            d["paginas"] = self.paginas
        if self.aviso_fonte:
            # o que a própria coleta não conseguiu determinar: sobe antes de
            # tudo, porque alcança a citação
            d["aviso_da_fonte"] = self.aviso_fonte
        if self.origem_texto == "ocr":
            # A confiança não é acurácia: é quanto do reconhecido são palavras
            # que o acervo conhece. Serve para calibrar o quanto se pode
            # confiar no trecho antes de conferir no PDF.
            d["texto_veio_de_ocr"] = True
            d["ocr_confianca"] = self.ocr_confianca
            d["aviso"] = (
                f"Texto obtido por reconhecimento óptico de uma digitalização "
                f"(confiança {self.ocr_confianca}/100, medida contra o vocabulário "
                f"do próprio acervo). NÃO é transcrição fiel. Nesta base o "
                f"reconhecimento acerta a prosa da AGU e erra os blocos de "
                f"doutrina e norma transcritos, que estão em fonte degradada. "
                f"Confira no PDF antes de reproduzir qualquer citação literal.")
        else:
            aviso_origem = ROTULO_ORIGEM.get(self.origem_texto or "")
            if aviso_origem:
                d["aviso"] = aviso_origem
        for rotulo, url in (("url_inteiro_teor", self.url_inteiro_teor),
                            ("url_publicacao", self.url_publicacao)):
            if url:
                d[rotulo] = url
        if self.trechos:
            d["paginas_encontradas"] = [t.para_dict() for t in self.trechos]
        return d


_NOMES = ["codigo", "fonte", "especie", "citacao", "numero", "ano", "orgao",
          "grupo", "assunto", "ementa", "texto", "vinculacao", "vinculacao_chave",
          "vinculacao_explicacao", "vigencia_declarada", "situacao_declarada",
          "ato_revogador", "ato_reanalise", "relacionadas", "aprovacao",
          "despachos", "regime", "alerta_vigencia", "paginas", "tem_texto",
          "origem_texto", "ocr_confianca", "aviso_fonte", "url_inteiro_teor",
          "url_publicacao"]

_CAMPOS = ", ".join(_NOMES)
# Nas consultas com JOIN, `codigo` existe nas duas tabelas e o SQLite recusa a
# coluna ambígua. Qualificar não é estilo: sem isto a busca não roda.
_CAMPOS_D = ", ".join(f"d.{n}" for n in _NOMES)


class Acervo:
    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)
        if not self.caminho.exists():
            raise FileNotFoundError(f"banco não encontrado: {self.caminho}")
        uri = f"file:{self.caminho.as_posix()}?mode=ro"
        self.con = sqlite3.connect(uri, uri=True, check_same_thread=False)
        self.con.row_factory = sqlite3.Row

    def fechar(self) -> None:
        self.con.close()

    def _doc(self, linha: sqlite3.Row) -> Documento:
        return Documento(**{k: linha[k] for k in linha.keys() if k != "trechos"})

    def obter(self, codigo: int) -> Documento | None:
        linha = self.con.execute(
            f"SELECT {_CAMPOS} FROM documentos WHERE codigo = ?", (codigo,)).fetchone()
        return self._doc(linha) if linha else None

    def _por_codigos(self, codigos: Iterable[int]) -> dict[int, Documento]:
        codigos = list(codigos)
        if not codigos:
            return {}
        marcas = ",".join("?" * len(codigos))
        linhas = self.con.execute(
            f"SELECT {_CAMPOS} FROM documentos WHERE codigo IN ({marcas})", codigos)
        return {l["codigo"]: self._doc(l) for l in linhas}

    # ------------------------------------------------------------------ busca
    def pesquisar(self, consulta: str, limite: int = 10, fonte: str | None = None,
                  ano_min: int | None = None, ano_max: int | None = None,
                  vinculacao: str | None = None, orgao: str | None = None,
                  operador: str = "AND") -> tuple[list[Documento], str, int]:
        expressao = montar_consulta_fts(consulta, operador)
        if not expressao:
            return [], "", 0
        filtros, params = [], [expressao]
        if fonte:
            filtros.append("d.fonte = ?")
            params.append(fonte)
        if ano_min:
            filtros.append("d.ano >= ?")
            params.append(ano_min)
        if ano_max:
            filtros.append("d.ano <= ?")
            params.append(ano_max)
        if vinculacao:
            filtros.append("d.vinculacao_chave = ?")
            params.append(vinculacao)
        if orgao:
            filtros.append("d.orgao = ?")
            params.append(orgao.upper())
        onde = (" AND " + " AND ".join(filtros)) if filtros else ""
        total = self.con.execute(
            f"""SELECT COUNT(*) FROM busca b JOIN documentos d ON d.codigo = b.codigo
                WHERE busca MATCH ?{onde}""", params).fetchone()[0]
        linhas = self.con.execute(
            f"""SELECT {_CAMPOS_D} FROM busca b JOIN documentos d ON d.codigo = b.codigo
                WHERE busca MATCH ?{onde}
                -- ordena por relevância, mas o que vincula sobe: uma ON vale
                -- mais numa peça que um parecer de alcance restrito
                ORDER BY bm25(busca, 0.0, 5.0, 6.0, 8.0, 6.0), d.vinculacao_ordem DESC,
                         d.ano DESC
                LIMIT ?""", params + [limite])
        return [self._doc(l) for l in linhas], expressao, total

    def pesquisar_paginas(self, consulta: str, limite: int = 8,
                          paginas_por_doc: int = 3, ano_min: int | None = None,
                          ano_max: int | None = None, so_fundamentacao: bool = False,
                          operador: str = "AND") -> tuple[list[Documento], str, int]:
        expressao = montar_consulta_fts(consulta, operador)
        if not expressao:
            return [], "", 0
        filtros, params = [], [expressao]
        if ano_min:
            filtros.append("d.ano >= ?")
            params.append(ano_min)
        if ano_max:
            filtros.append("d.ano <= ?")
            params.append(ano_max)
        if so_fundamentacao:
            filtros.append("COALESCE(p.secao,'') IN ('fundamentacao','conclusao')")
        onde = (" AND " + " AND ".join(filtros)) if filtros else ""
        total = self.con.execute(
            f"""SELECT COUNT(DISTINCT f.codigo) FROM paginas_fts f
                JOIN documentos d ON d.codigo = f.codigo
                LEFT JOIN paginas p ON p.codigo = f.codigo AND p.pagina = f.pagina
                WHERE paginas_fts MATCH ?{onde}""", params).fetchone()[0]
        linhas = self.con.execute(
            f"""SELECT f.codigo, f.pagina,
                       snippet(paginas_fts, 2, '«', '»', ' … ', 26) AS trecho,
                       COALESCE(p.secao,'indefinida') AS secao,
                       COALESCE(p.transcricao,0) AS transcricao,
                       bm25(paginas_fts) AS score
                FROM paginas_fts f
                JOIN documentos d ON d.codigo = f.codigo
                LEFT JOIN paginas p ON p.codigo = f.codigo AND p.pagina = f.pagina
                WHERE paginas_fts MATCH ?{onde}
                ORDER BY score LIMIT ?""", params + [limite * paginas_por_doc * 3])
        por_doc: dict[int, list[Trecho]] = {}
        ordem: list[int] = []
        for l in linhas:
            lista = por_doc.setdefault(l["codigo"], [])
            if l["codigo"] not in ordem:
                ordem.append(l["codigo"])
            if len(lista) < paginas_por_doc:
                lista.append(Trecho(l["codigo"], l["pagina"], " ".join(l["trecho"].split()),
                                    l["secao"], l["transcricao"]))
            if len(ordem) >= limite and all(len(por_doc[c]) >= paginas_por_doc for c in ordem):
                break
        fichas = self._por_codigos(ordem[:limite])
        saida = []
        for cod in ordem[:limite]:
            d = fichas.get(cod)
            if d:
                d.trechos = por_doc[cod]
                saida.append(d)
        return saida, expressao, total

    def paginas_do_documento(self, codigo: int, inicio: int, quantidade: int = 3,
                             ) -> list[dict[str, Any]]:
        fim = inicio + max(1, min(quantidade, 10)) - 1
        linhas = self.con.execute(
            """SELECT f.pagina, f.texto, COALESCE(p.secao,'indefinida') AS secao,
                      COALESCE(p.transcricao,0) AS transcricao
               FROM paginas_fts f
               LEFT JOIN paginas p ON p.codigo = f.codigo AND p.pagina = f.pagina
               WHERE f.codigo = ? AND f.pagina BETWEEN ? AND ?
               ORDER BY f.pagina""", (codigo, inicio, fim))
        saida = []
        for l in linhas:
            t = Trecho(codigo, l["pagina"], (l["texto"] or "").strip(),
                       l["secao"], l["transcricao"])
            d = t.para_dict()
            d["texto"] = d.pop("trecho")
            saida.append(d)
        return saida

    # ---------------------------------------------------------------- tesauro
    def sinonimos(self, termo: str) -> list[dict[str, Any]]:
        chave = _sem_acento(termo).lower()
        conceitos: list[str] = []
        for conceito, variante in self.con.execute(
                "SELECT conceito, variante FROM sinonimos"):
            if chave in _sem_acento(conceito).lower() or chave in _sem_acento(variante).lower():
                if conceito not in conceitos:
                    conceitos.append(conceito)
        saida = []
        for c in conceitos:
            variantes = [dict(variante=r["variante"], documentos=r["documentos"])
                         for r in self.con.execute(
                             """SELECT variante, documentos FROM sinonimos
                                WHERE conceito = ? ORDER BY documentos DESC""", (c,))]
            saida.append({"conceito": c, "variantes": variantes,
                          "soma_documentos": sum(v["documentos"] for v in variantes)})
        return saida

    # --------------------------------------------------------------- citações
    def quem_citou(self, referencia: str, limite: int = 25) -> dict[str, Any]:
        chave = f"%{referencia.strip()}%"
        refs = self.con.execute(
            """SELECT referencia, especie, COUNT(DISTINCT codigo) AS docs,
                      SUM(ocorrencias) AS cit
               FROM citacoes WHERE referencia LIKE ?
               GROUP BY referencia, especie ORDER BY docs DESC LIMIT 8""",
            (chave,)).fetchall()
        if not refs:
            return {"referencia": referencia, "encontrado": False, "documentos": []}
        principal = refs[0]
        linhas = self.con.execute(
            f"""SELECT {_CAMPOS_D} FROM citacoes c JOIN documentos d ON d.codigo = c.codigo
                WHERE c.referencia = ?
                -- do mais RECENTE para o mais antigo: o que aconteceu por último
                -- é o que decide o estado da norma
                ORDER BY d.ano DESC, d.vinculacao_ordem DESC LIMIT ?""",
            (principal["referencia"], limite))
        return {
            "referencia": principal["referencia"],
            "encontrado": True,
            "especie": principal["especie"],
            "documentos_que_citam": principal["docs"],
            "ocorrencias": principal["cit"],
            "outras_referencias_parecidas": [
                dict(referencia=r["referencia"], documentos=r["docs"]) for r in refs[1:]],
            "documentos": [self._doc(l).para_dict(com_texto=False) for l in linhas],
            "aviso": AVISO_ENTE,
        }

    # ------------------------------------------------------ situação do ato
    def situacao_do_ato(self, alvo: str) -> dict[str, Any]:
        """O que a fonte declara sobre o estado de uma ON, súmula ou manifestação.

        Não responde "está em vigor": responde o que a AGU publicou.
        """
        chave = f"%{_sem_acento(alvo).lower().strip()}%"
        linhas = self.con.execute(
            f"""SELECT {_CAMPOS} FROM documentos
                WHERE lower(citacao) LIKE ? OR lower(citacao) LIKE ?
                ORDER BY ano DESC LIMIT 12""",
            (chave, f"%{alvo.lower().strip()}%")).fetchall()
        achados = [self._doc(l) for l in linhas]
        # quem, no acervo, aponta mudança de estado deste ato
        apontam = self.con.execute(
            f"""SELECT {_CAMPOS} FROM documentos
                WHERE COALESCE(ato_revogador,'') LIKE ?
                   OR COALESCE(situacao_declarada,'') LIKE ?
                   OR COALESCE(relacionadas,'') LIKE ?
                ORDER BY ano DESC LIMIT 12""",
            (chave, chave, chave)).fetchall()
        return {
            "consulta": alvo,
            "atos_encontrados": [d.para_dict() for d in achados],
            "atos_que_mencionam_mudanca": [
                self._doc(l).para_dict(com_texto=False) for l in apontam],
            "advertencia": (
                "Isto NÃO é declaração de vigência. É o que a fonte publicou: a "
                "situação que a AGU registrou na página do ato ou na consulta "
                "pública, na data da coleta. Não alcança revogação tácita, "
                "alteração por norma superveniente nem decisão judicial. "
                "Ausência de ressalva significa que a fonte nada declarou — não "
                "que o ato esteja íntegro."),
            "aviso_ente": AVISO_ENTE,
        }

    # ------------------------------------------------------------- listagem
    def listar(self, fonte: str | None = None, ano: int | None = None,
               orgao: str | None = None, vinculacao: str | None = None,
               so_com_inteiro_teor: bool = False, so_com_ressalva: bool = False,
               limite: int = 30) -> list[Documento]:
        filtros, params = [], []
        if fonte:
            filtros.append("fonte = ?")
            params.append(fonte)
        if ano:
            filtros.append("ano = ?")
            params.append(ano)
        if orgao:
            filtros.append("orgao = ?")
            params.append(orgao.upper())
        if vinculacao:
            filtros.append("vinculacao_chave = ?")
            params.append(vinculacao)
        if so_com_inteiro_teor:
            filtros.append("tem_texto = 1")
        if so_com_ressalva:
            filtros.append("""(COALESCE(situacao_declarada,'') <> ''
                               OR COALESCE(ato_revogador,'') <> ''
                               OR vigencia_declarada NOT IN ('1','None'))""")
        onde = ("WHERE " + " AND ".join(filtros)) if filtros else ""
        linhas = self.con.execute(
            f"""SELECT {_CAMPOS} FROM documentos {onde}
                ORDER BY vinculacao_ordem DESC, ano DESC, numero DESC LIMIT ?""",
            params + [limite])
        return [self._doc(l) for l in linhas]

    # ------------------------------------------------------------- cobertura
    def cobertura(self) -> dict[str, Any]:
        base: dict[str, Any] = {}
        for r in self.con.execute("SELECT chave, valor FROM cobertura"):
            try:
                base[r["chave"]] = json.loads(r["valor"])
            except (json.JSONDecodeError, TypeError):
                base[r["chave"]] = r["valor"]
        base["por_camara"] = {
            CAMARAS.get(k or "", k or "(sem câmara)"): v
            for k, v in self.con.execute(
                "SELECT orgao, COUNT(*) FROM documentos WHERE fonte='conuni' GROUP BY 1")}
        base["regimes_entre_os_com_texto"] = dict(self.con.execute(
            "SELECT COALESCE(regime,'(não identificado)'), COUNT(*) FROM documentos "
            "WHERE tem_texto = 1 GROUP BY 1"))
        return base
