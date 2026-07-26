"""Inteiro teor dos acórdãos: download do PDF oficial e texto por página.

A listagem de jurisprudência entrega a ementa; o voto que a fundamenta está no
PDF que o próprio portal publica. Este módulo baixa esse documento e o
converte em texto **por página**, porque é a página que permite conferir a
passagem no original — sem ela, um trecho citado é impossível de auditar.

O PDF do acórdão tem duas partes de naturezas distintas: a primeira página traz
a decisão em campos numerados, e as seguintes reproduzem os votos tal como
juntados ao processo, com o cabeçalho de folha repetido em cada uma.
"""

from __future__ import annotations

import io
import logging
import re
from collections import Counter
from dataclasses import dataclass

from .extracao import corrigir_mojibake

log = logging.getLogger(__name__)

URL_PDF = (
    "https://www.tcerj.tc.br/documento-webapi-externo/api/documento/"
    "acordao/{numero}/{ano}?votoInteiro=true"
)

# "Processo nº 106.426-3/22, fls. 20" — o número de folha do processo, que é
# como se cita peça processual e não coincide com a página do PDF.
_RE_FOLHA = re.compile(r"fls?\.\s*(\d{1,5})", re.IGNORECASE)

# Linha que só tem numeração, traço ou espaço: resto de cabeçalho e rodapé.
_RE_LINHA_VAZIA = re.compile(r"^[\s\-–—_.]*$")

# Palavra quebrada pelo fim da linha ("adminis-\ntração").
_RE_HIFENIZACAO = re.compile(r"(\w)-\n([a-záàâãéêíóôõúç])")


@dataclass(slots=True)
class Pagina:
    numero: int          # índice no PDF, a partir de 1
    folha: int | None    # folha do processo, quando o cabeçalho a declara
    texto: str


URL_PROCESSO = (
    "https://www.tcerj.tc.br/consulta-processo/Processo/List?numeroProcesso={processo}"
)


def url_do_acordao(numero: str | int, ano: int) -> str:
    return URL_PDF.format(numero=numero, ano=ano)


def url_do_processo(processo: str | None) -> str | None:
    """A consulta processual não usa o ponto de milhar."""
    if not processo:
        return None
    return URL_PROCESSO.format(processo=processo.replace(".", ""))


# Um acórdão costuma juntar mais de uma peça — voto do relator, voto-vista,
# voto vencedor —, cada qual com o próprio timbre. Exigir que a moldura cubra
# metade do documento deixaria passar a de todas elas; um quinto já basta,
# desde que a linha seja curta, que é o que distingue timbre de conteúdo.
_FRACAO_MOLDURA = 0.2
_MAXIMO_MOLDURA = 90


def normalizar_linha(linha: str) -> str:
    """Forma canônica de uma linha, usada tanto para detectar quanto para tirar.

    As duas operações precisam ver a mesma coisa: detectar a moldura no texto
    bruto e removê-la no texto já com espaços colapsados deixava passar
    "Gabinete  da Conselheira" — dois espaços na origem, um depois, e a
    comparação falhava em silêncio.
    """
    return re.sub(r"[ \t\xa0]+", " ", linha).strip()


def identidade_oficial(tipo: str, numero: str | int, ano: int) -> str:
    """Identificador do documento oficial, distinto do registro de ementa.

    Um acórdão rende mais de uma ementa selecionada — teses diferentes, sobre
    macro-temas diferentes, do mesmo julgamento. As ementas não são
    duplicatas; o inteiro teor é que é um só, e pertence ao acórdão.
    """
    return f"{tipo}-{numero}-{ano}"


def _repetidas(paginas: list[str]) -> set[str]:
    """Linhas repetidas nas bordas das páginas: cabeçalho, rodapé, timbre.

    Não são conteúdo e poluiriam a busca — "Processo nº 106.426-3/22"
    apareceria como resultado em qualquer consulta que citasse o número, e o
    nome do gabinete, em toda consulta pelo relator.
    """
    if len(paginas) < 4:
        return set()
    contagem: Counter[str] = Counter()
    for texto in paginas:
        # Só as bordas: uma frase repetida no miolo é conteúdo, não moldura.
        linhas = [normalizar_linha(l) for l in texto.splitlines()]
        linhas = [l for l in linhas if l]
        contagem.update(set(linhas[:3] + linhas[-3:]))

    minimo = max(3, int(len(paginas) * _FRACAO_MOLDURA))
    return {
        linha
        for linha, n in contagem.items()
        if n >= minimo and len(linha) <= _MAXIMO_MOLDURA
    }


def _limpar(texto: str, moldura: set[str]) -> str:
    """Normalização mínima: tira moldura, junta a palavra partida, enxuga espaço."""
    linhas = []
    for linha in texto.splitlines():
        enxuta = normalizar_linha(linha)
        if not enxuta or _RE_LINHA_VAZIA.match(enxuta):
            continue
        if enxuta in moldura:
            continue
        # Cabeçalho de folha varia o número a cada página e escapa da moldura.
        if _RE_FOLHA.search(enxuta) and len(enxuta) < 60:
            continue
        linhas.append(enxuta)

    junto = "\n".join(linhas)
    junto = _RE_HIFENIZACAO.sub(r"\1\2", junto)
    return junto.strip()


def paginas_do_pdf(conteudo: bytes) -> list[Pagina]:
    """Converte o PDF em páginas de texto normalizado."""
    import fitz  # importado aqui: só a ingestão precisa do PyMuPDF

    with fitz.open(stream=io.BytesIO(conteudo), filetype="pdf") as documento:
        brutas = [pagina.get_text() for pagina in documento]

    moldura = _repetidas(brutas)
    paginas: list[Pagina] = []
    for indice, bruta in enumerate(brutas, start=1):
        bruta = corrigir_mojibake(bruta)
        achado = _RE_FOLHA.search(bruta[:400])
        limpa = _limpar(bruta, moldura)
        if not limpa:
            continue  # página em branco ou só moldura
        paginas.append(
            Pagina(
                numero=indice,
                folha=int(achado.group(1)) if achado else None,
                texto=limpa,
            )
        )
    return paginas


def relimpar(paginas: list[Pagina]) -> list[Pagina]:
    """Repassa a remoção de moldura sobre páginas já extraídas.

    Serve ao reparo de material já coletado: o defeito estava na comparação,
    não na leitura do PDF, e rebaixar mil documentos por erro de programação
    seria carregar o servidor do Tribunal à toa.
    """
    moldura = _repetidas([p.texto for p in paginas])
    saida = []
    for pagina in paginas:
        limpa = _limpar(pagina.texto, moldura)
        if limpa:
            saida.append(Pagina(numero=pagina.numero, folha=pagina.folha, texto=limpa))
    return saida


def impressao_digital(paginas: list[Pagina]) -> str:
    """Hash do texto integral normalizado.

    Não entra na identidade — serve de controle: revela o mesmo documento
    guardado sob identificadores diferentes, ou arquivo trocado pelo Tribunal
    entre uma coleta e outra.
    """
    import hashlib

    junto = "\n".join(p.texto for p in sorted(paginas, key=lambda p: p.numero))
    return hashlib.sha256(junto.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------


async def coletar(
    config,
    armazenamento,
    *,
    tipo=None,
    max_documentos: int | None = None,
    reverificar: bool = False,
    ao_progresso=None,
) -> dict[str, int]:
    """Atualiza o inteiro teor: o que falta, o que ficou pendente, e só isso.

    O portal não oferece `ETag` nem aceita `HEAD` — verificar se um documento
    mudou custa o mesmo que rebaixá-lo. Por isso o padrão é **não** reconferir
    o que já está guardado: `reverificar` existe para quando se quiser fazê-lo
    de propósito. Nesse caso a impressão digital evita reescrever o banco
    quando nada mudou, o que importa porque cada reescrita vira um arquivo
    novo no histórico.
    """
    from .http import Cliente, ErroHttp

    fila = armazenamento.oficiais_sem_texto(tipo=tipo)
    if reverificar:
        ja_tem = armazenamento.oficiais_com_texto()
        conhecidos = {p["oficial"] for p in fila}
        for linha in armazenamento.conexao.execute(
            "SELECT id AS oficial, tipo, numero, ano, processo "
            "FROM documentos_oficiais WHERE status_coleta = 'ok'"
        ):
            if linha["oficial"] in ja_tem and linha["oficial"] not in conhecidos:
                fila.append(dict(linha))

    if max_documentos is not None:
        fila = fila[:max_documentos]

    log.info("Documentos na fila: %d%s", len(fila),
             " (incluindo reverificação)" if reverificar else "")
    contagem = {"novos": 0, "atualizados": 0, "inalterados": 0,
                "paginas": 0, "falhas": 0}

    async with Cliente(config) as cliente:
        for pendente in fila:
            oficial = pendente["oficial"]
            url = url_do_acordao(pendente["numero"], pendente["ano"])
            comum = dict(
                tipo=pendente["tipo"], numero=str(pendente["numero"]),
                ano=pendente["ano"], processo=pendente["processo"], url=url,
            )

            def anotar(status: str, detalhe: str | None = None) -> None:
                armazenamento.registrar_oficial(
                    oficial, **comum, status=status, detalhe=detalhe
                )

            try:
                resposta = await cliente.obter(url)
            except ErroHttp as erro:
                # 404 é ausência estrutural — o Tribunal não publicou. Os
                # demais são transitórios e merecem nova tentativa depois.
                estrutural = getattr(erro, "status", None) == 404
                anotar("http_404" if estrutural else "erro_temporario", str(erro))
                log.warning("Falha em %s: %s", oficial, erro)
                contagem["falhas"] += 1
                continue

            if "pdf" not in resposta.headers.get("content-type", "").lower():
                # O portal responde 200 com página de erro quando o documento
                # não está publicado; sem esta checagem, ela viraria "texto".
                anotar("sem_texto", resposta.headers.get("content-type"))
                contagem["falhas"] += 1
                continue

            try:
                paginas = paginas_do_pdf(resposta.content)
            except Exception as erro:  # noqa: BLE001 - PDF de terceiro, formato imprevisível
                anotar("erro_temporario", f"PDF ilegível: {erro}")
                log.warning("PDF ilegível em %s: %s", oficial, erro)
                contagem["falhas"] += 1
                continue

            if not paginas:
                anotar("sem_texto", "PDF sem texto aproveitável")
                contagem["falhas"] += 1
                continue

            impressao = impressao_digital(paginas)
            if impressao == armazenamento.impressao_de(oficial):
                # Mesmo conteúdo: não se toca no banco, só na data da conferência.
                armazenamento.registrar_oficial(
                    oficial, **comum, paginas_total=len(paginas),
                    impressao=impressao, status="ok",
                )
                contagem["inalterados"] += 1
                continue

            novo = not armazenamento.impressao_de(oficial)
            contagem["paginas"] += armazenamento.gravar_paginas(oficial, paginas)
            armazenamento.registrar_oficial(
                oficial, **comum, paginas_total=len(paginas),
                impressao=impressao, status="ok",
            )
            armazenamento.marcar_visitado(url, "ok")
            contagem["novos" if novo else "atualizados"] += 1

            feitos = contagem["novos"] + contagem["atualizados"]
            if ao_progresso and feitos and feitos % 25 == 0:
                ao_progresso(feitos, contagem["paginas"], contagem["falhas"])

    return contagem


# ---------------------------------------------------------------------------
# Reparo do que já foi coletado
# ---------------------------------------------------------------------------


def reparar(armazenamento, ao_progresso=None) -> dict[str, int]:
    """Reagrupa as páginas por documento oficial e repassa a limpeza.

    Transformação determinística sobre material já coletado: corrige um erro
    de modelagem (páginas guardadas por registro de ementa, e não por acórdão)
    e um de comparação (moldura detectada no texto bruto, removida no texto
    normalizado) sem tocar no servidor do Tribunal.
    """
    conexao = armazenamento.conexao
    antes_paginas = conexao.execute("SELECT COUNT(*) FROM paginas").fetchone()[0]

    # De cada registro de ementa para o documento oficial correspondente.
    mapa: dict[str, dict] = {}
    for linha in conexao.execute(
        "SELECT id, tipo, numero, ano, processo FROM documentos "
        "WHERE numero IS NOT NULL AND ano IS NOT NULL"
    ):
        mapa[linha["id"]] = {
            "oficial": identidade_oficial(linha["tipo"], linha["numero"], linha["ano"]),
            "tipo": linha["tipo"], "numero": str(linha["numero"]),
            "ano": linha["ano"], "processo": linha["processo"],
        }

    # Junta as páginas por documento oficial, mantendo a primeira versão de
    # cada página: cópias do mesmo PDF são idênticas.
    por_oficial: dict[str, dict[int, Pagina]] = {}
    dados: dict[str, dict] = {}
    for linha in conexao.execute(
        "SELECT documento_id, pagina, folha, texto FROM paginas ORDER BY documento_id, pagina"
    ):
        info = mapa.get(linha["documento_id"])
        oficial = info["oficial"] if info else linha["documento_id"]
        if info:
            dados.setdefault(oficial, info)
        por_oficial.setdefault(oficial, {}).setdefault(
            linha["pagina"],
            Pagina(numero=linha["pagina"], folha=linha["folha"], texto=linha["texto"]),
        )

    conexao.execute("DELETE FROM paginas")  # os gatilhos limpam o índice
    conexao.commit()

    documentos = paginas_finais = 0
    for oficial, paginas in por_oficial.items():
        limpas = relimpar(sorted(paginas.values(), key=lambda p: p.numero))
        if not limpas:
            continue
        paginas_finais += armazenamento.gravar_paginas(oficial, limpas)
        info = dados.get(oficial, {})
        armazenamento.registrar_oficial(
            oficial,
            tipo=info.get("tipo", "acordao"),
            numero=info.get("numero", ""),
            ano=info.get("ano", 0),
            processo=info.get("processo"),
            url=url_do_acordao(info.get("numero", ""), info.get("ano", 0)),
            paginas_total=len(limpas),
            impressao=impressao_digital(limpas),
        )
        documentos += 1
        if ao_progresso and documentos % 100 == 0:
            ao_progresso(documentos, paginas_finais)

    return {
        "documentos_oficiais": documentos,
        "paginas_antes": antes_paginas,
        "paginas_depois": paginas_finais,
    }
