"""Descoberta do endpoint interno do portal, por interceptação de rede.

O portal de jurisprudência é uma aplicação JavaScript: o HTML servido vem
praticamente vazio e os resultados chegam por chamadas assíncronas. Em vez de
adivinhar essas chamadas, abrimos a página num navegador real, executamos uma
busca e gravamos o tráfego que ela dispara. A partir das respostas JSON o
módulo infere onde ficam a lista de itens e os parâmetros de paginação, e
devolve uma configuração pronta para o modo `api`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config import Config, ConfigApi

log = logging.getLogger(__name__)

# Cabeçalhos que não devem ser gravados nem reaproveitados.
_CABECALHOS_SENSIVEIS = {"cookie", "authorization", "set-cookie", "x-xsrf-token"}

_CHAVES_PAGINA = ("page", "pagina", "pageNumber", "offset", "inicio", "start", "_page")
_CHAVES_TAMANHO = (
    "size", "tamanho", "tamanhoPagina", "pageSize", "limit", "qtd", "quantidade", "rows",
)
_CHAVES_TOTAL = (
    "totalElements", "total", "totalRegistros", "totalCount", "numFound", "recordsTotal",
)


def sem_sensiveis(cabecalhos: dict[str, str]) -> dict[str, str]:
    """Remove credenciais e identificadores de sessão."""
    return {k: v for k, v in cabecalhos.items() if k.lower() not in _CABECALHOS_SENSIVEIS}


@dataclass(slots=True)
class ChamadaCapturada:
    url: str
    metodo: str
    cabecalhos: dict[str, str]
    corpo_requisicao: Any | None
    status: int
    tipo_conteudo: str
    amostra: Any | None = None
    # Quanto o formato da resposta se parece com uma listagem de resultados.
    pontuacao: int = 0
    caminho_itens: str = ""
    campo_total: str | None = None
    quantidade_itens: int = 0

    def para_dict(self) -> dict[str, Any]:
        # O relatório vai para disco e costuma ser versionado junto com o
        # projeto: cabeçalhos de sessão são removidos aqui, no único ponto de
        # saída, e não apenas no momento da captura.
        return {
            "url": self.url,
            "metodo": self.metodo,
            "cabecalhos": sem_sensiveis(self.cabecalhos),
            "corpo_requisicao": self.corpo_requisicao,
            "status": self.status,
            "tipo_conteudo": self.tipo_conteudo,
            "pontuacao": self.pontuacao,
            "caminho_itens": self.caminho_itens,
            "campo_total": self.campo_total,
            "quantidade_itens": self.quantidade_itens,
            "amostra": self.amostra,
        }


@dataclass(slots=True)
class Relatorio:
    chamadas: list[ChamadaCapturada] = field(default_factory=list)
    portais_visitados: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)

    def melhor(self) -> ChamadaCapturada | None:
        candidatas = [c for c in self.chamadas if c.pontuacao > 0]
        if not candidatas:
            return None
        return max(candidatas, key=lambda c: (c.pontuacao, c.quantidade_itens))

    def salvar(self, destino: str | Path) -> Path:
        caminho = Path(destino)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(
            json.dumps(
                {
                    "portais_visitados": self.portais_visitados,
                    "erros": self.erros,
                    "chamadas": [c.para_dict() for c in self.chamadas],
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        return caminho


# ---------------------------------------------------------------------------
# Análise das respostas
# ---------------------------------------------------------------------------


def localizar_lista(dados: Any, prefixo: str = "", profundidade: int = 0) -> tuple[str, int]:
    """Acha o caminho da maior lista de objetos dentro da resposta.

    Retorna (caminho_pontilhado, quantidade). Uma lista de dicionários com
    vários campos é o formato típico de uma página de resultados.
    """
    if profundidade > 4:
        return "", 0

    if isinstance(dados, list):
        objetos = [i for i in dados if isinstance(i, dict)]
        if objetos:
            return prefixo, len(objetos)
        return "", 0

    if isinstance(dados, dict):
        melhor_caminho, melhor_qtd = "", 0
        for chave, valor in dados.items():
            caminho = f"{prefixo}.{chave}" if prefixo else chave
            achado, qtd = localizar_lista(valor, caminho, profundidade + 1)
            if qtd > melhor_qtd:
                melhor_caminho, melhor_qtd = achado, qtd
        return melhor_caminho, melhor_qtd

    return "", 0


def _campo_total(dados: Any) -> str | None:
    if not isinstance(dados, dict):
        return None
    for chave in dados:
        if chave in _CHAVES_TOTAL:
            return chave
    for chave, valor in dados.items():
        if isinstance(valor, int) and re.search(r"total|count|found", chave, re.I):
            return chave
    return None


def pontuar(chamada: ChamadaCapturada) -> ChamadaCapturada:
    """Avalia o quanto a resposta se parece com uma listagem de jurisprudência."""
    dados = chamada.amostra
    if dados is None:
        return chamada

    caminho, quantidade = localizar_lista(dados)
    chamada.caminho_itens = caminho
    chamada.quantidade_itens = quantidade
    chamada.campo_total = _campo_total(dados)

    if quantidade == 0:
        return chamada

    pontos = 10 + min(quantidade, 50)
    if chamada.campo_total:
        pontos += 15

    # Presença de vocabulário jurídico nas chaves e nos valores é o sinal mais
    # forte de que se trata mesmo do acervo de jurisprudência.
    texto = json.dumps(dados, ensure_ascii=False)[:20000].lower()
    for termo in (
        "ementa", "acordao", "acórdão", "relator", "processo", "sumula",
        "súmula", "deliberacao", "deliberação", "enunciado", "julgamento",
        "sessao", "sessão", "inteiroteor", "conselheiro",
    ):
        if termo in texto:
            pontos += 8

    if re.search(r"jurisprud|acord|deliberac|sumula|enunciado|publicac", chamada.url, re.I):
        pontos += 20

    chamada.pontuacao = pontos
    return chamada


def marcar_paginacao_no_caminho(caminho: str) -> tuple[str, int | None, int | None]:
    """Substitui por marcadores os valores de paginação embutidos no caminho.

    Endpoints no estilo `/consulta/pagina/2/tamanhoPagina/50` não aceitam
    página e tamanho como parâmetro: eles fazem parte da própria rota. A URL
    é devolvida com `{pagina}`/`{tamanho}` no lugar dos números, junto com os
    valores que estavam ali — que são a primeira página e o tamanho usados
    pelo portal.
    """
    segmentos = caminho.split("/")
    paginas = {c.lower() for c in _CHAVES_PAGINA}
    tamanhos = {c.lower() for c in _CHAVES_TAMANHO}
    pagina = tamanho = None

    for i in range(len(segmentos) - 1):
        nome, valor = segmentos[i].lower(), segmentos[i + 1]
        if not valor.isdigit():
            continue
        # Tamanho antes de página: "tamanhoPagina" também termina em "pagina".
        if nome in tamanhos:
            tamanho = max(int(valor), 1)
            segmentos[i + 1] = "{tamanho}"
        elif nome in paginas:
            pagina = int(valor)
            segmentos[i + 1] = "{pagina}"

    return "/".join(segmentos), pagina, tamanho


def inferir_api(chamada: ChamadaCapturada, termo: str | None = None) -> ConfigApi:
    """Converte a chamada vencedora em configuração reutilizável.

    `termo` é a palavra usada na busca-sonda: encontrá-la entre os parâmetros
    revela qual campo carrega o texto pesquisado.
    """
    partes = urlparse(chamada.url)
    query = {k: v[0] for k, v in parse_qs(partes.query).items()}

    corpo = chamada.corpo_requisicao if isinstance(chamada.corpo_requisicao, dict) else None
    fonte_parametros: dict[str, Any] = {**query, **(corpo or {})}

    campo_pagina = _primeira_chave(fonte_parametros, _CHAVES_PAGINA) or "page"
    campo_tamanho = _primeira_chave(fonte_parametros, _CHAVES_TAMANHO) or "size"

    primeira = 0
    valor_pagina = fonte_parametros.get(campo_pagina)
    if isinstance(valor_pagina, (int, str)) and str(valor_pagina).isdigit():
        primeira = int(valor_pagina)

    tamanho = 50
    valor_tamanho = fonte_parametros.get(campo_tamanho)
    if isinstance(valor_tamanho, (int, str)) and str(valor_tamanho).isdigit():
        tamanho = max(int(valor_tamanho), 1)

    caminho, pagina_na_rota, tamanho_na_rota = marcar_paginacao_no_caminho(partes.path)
    if pagina_na_rota is not None:
        primeira = pagina_na_rota
    if tamanho_na_rota is not None:
        tamanho = tamanho_na_rota

    identificado = _campo_com_valor(fonte_parametros, termo)
    campo_termo = identificado or "termo"

    # A busca-sonda usou um termo qualquer só para fazer o portal reagir.
    # Guardá-lo na configuração filtraria toda coleta futura em silêncio. Só
    # se remove o campo que comprovadamente carregava esse valor — se a sonda
    # não o identificou, nada aqui é palpite.
    if identificado:
        query = {k: v for k, v in query.items() if k != identificado}
        if corpo is not None:
            corpo = {k: v for k, v in corpo.items() if k != identificado}

    return ConfigApi(
        url=f"{partes.scheme}://{partes.netloc}{caminho}",
        metodo=chamada.metodo.upper(),
        cabecalhos={
            k: v
            for k, v in chamada.cabecalhos.items()
            if k.lower() in {"accept", "content-type", "x-requested-with"}
        },
        parametros=query,
        corpo=corpo,
        campo_pagina=campo_pagina,
        campo_tamanho=campo_tamanho,
        campo_termo=campo_termo,
        primeira_pagina=primeira,
        tamanho_pagina=tamanho,
        caminho_itens=chamada.caminho_itens,
        caminho_total=chamada.campo_total or "total",
    )


def _campo_com_valor(dados: dict[str, Any], valor: str | None) -> str | None:
    """Acha a chave cujo valor é o termo pesquisado."""
    if not valor:
        return None
    alvo = valor.strip().lower()
    for chave, atual in dados.items():
        if isinstance(atual, str) and atual.strip().lower() == alvo:
            return chave
    return None


def _primeira_chave(dados: dict[str, Any], candidatas: tuple[str, ...]) -> str | None:
    minusculas = {k.lower(): k for k in dados}
    for candidata in candidatas:
        if candidata.lower() in minusculas:
            return minusculas[candidata.lower()]
    return None


# ---------------------------------------------------------------------------
# Captura com navegador real
# ---------------------------------------------------------------------------

# Termo genérico o bastante para retornar resultados em qualquer das bases.
TERMO_SONDA = "licitação"


async def descobrir(
    config: Config,
    *,
    termo: str = TERMO_SONDA,
    headless: bool = True,
    limite_amostra: int = 400_000,
) -> Relatorio:
    """Visita os portais, dispara uma busca e grava as chamadas de rede."""
    from playwright.async_api import async_playwright

    relatorio = Relatorio()

    async with async_playwright() as playwright:
        navegador = await playwright.chromium.launch(
            headless=headless, executable_path=config.executavel_navegador()
        )
        contexto = await navegador.new_context(
            user_agent=config.user_agent, locale="pt-BR"
        )
        pagina = await contexto.new_page()

        # O corpo precisa ser lido enquanto a resposta ainda existe: assim que
        # a página navega para o portal seguinte, o Chromium a descarta e
        # `text()` falha. Adiar essa leitura para o fim da varredura só
        # preservava as chamadas do último portal visitado.
        capturas: list[ChamadaCapturada] = []
        leituras: list[asyncio.Task] = []

        async def registrar(resposta) -> None:
            chamada = await _capturar(resposta, limite_amostra)
            if chamada is not None:
                capturas.append(chamada)

        def ao_receber(resposta) -> None:
            if _e_json(resposta):
                leituras.append(asyncio.create_task(registrar(resposta)))

        pagina.on("response", ao_receber)

        for caminho in config.portais:
            url = config.url_absoluta(caminho)
            log.info("Visitando %s", url)
            try:
                await pagina.goto(url, wait_until="domcontentloaded", timeout=60_000)
                await _tentar_busca(pagina, termo, config)
                await pagina.wait_for_timeout(4_000)
                relatorio.portais_visitados.append(url)
            except Exception as erro:  # noqa: BLE001 - queremos seguir para o próximo portal
                mensagem = f"{url}: {type(erro).__name__}: {erro}"
                log.warning("Falha ao visitar %s", mensagem)
                relatorio.erros.append(mensagem)

            # Esvazia as leituras deste portal antes de navegar para o próximo.
            if leituras:
                await asyncio.gather(*leituras, return_exceptions=True)
                leituras.clear()

        for chamada in capturas:
            # Pontua sobre a resposta inteira e só então encolhe para o
            # relatório: encolher antes fazia toda listagem valer 3 itens,
            # apagando o sinal de tamanho e mentindo no "itens por página"
            # que se lê para julgar a escolha.
            pontuar(chamada)
            chamada.amostra = _encolher(chamada.amostra)
            relatorio.chamadas.append(chamada)

        await contexto.close()
        await navegador.close()

    relatorio.chamadas.sort(key=lambda c: c.pontuacao, reverse=True)
    return relatorio


def _e_json(resposta) -> bool:
    try:
        if resposta.request.resource_type not in {"xhr", "fetch"}:
            return False
        return "json" in (resposta.headers or {}).get("content-type", "").lower()
    except Exception:  # noqa: BLE001 - resposta pode já ter sido descartada
        return False


async def _capturar(resposta, limite: int) -> ChamadaCapturada | None:
    requisicao = resposta.request
    try:
        texto = await resposta.text()
    except Exception as erro:  # noqa: BLE001 - corpo indisponível após navegação
        log.debug("Corpo indisponível para %s: %s", requisicao.url, erro)
        return None

    if len(texto) > limite:
        texto = texto[:limite]
    try:
        amostra = json.loads(texto)
    except json.JSONDecodeError:
        return None

    corpo_requisicao: Any | None = None
    if requisicao.post_data:
        try:
            corpo_requisicao = json.loads(requisicao.post_data)
        except json.JSONDecodeError:
            corpo_requisicao = requisicao.post_data

    return ChamadaCapturada(
        url=requisicao.url,
        metodo=requisicao.method,
        cabecalhos=sem_sensiveis(requisicao.headers or {}),
        corpo_requisicao=corpo_requisicao,
        status=resposta.status,
        tipo_conteudo=(resposta.headers or {}).get("content-type", ""),
        amostra=amostra,
    )


def _encolher(dados: Any, maximo_itens: int = 3) -> Any:
    """Reduz listas longas para manter o relatório legível."""
    if isinstance(dados, list):
        return [_encolher(i, maximo_itens) for i in dados[:maximo_itens]]
    if isinstance(dados, dict):
        return {k: _encolher(v, maximo_itens) for k, v in dados.items()}
    if isinstance(dados, str) and len(dados) > 2000:
        return dados[:2000] + "…"
    return dados


async def _tentar_busca(pagina, termo: str, config: Config) -> None:
    """Preenche o primeiro campo de busca visível e submete.

    Sem submeter, muitos portais não disparam a chamada de listagem. Falhas aqui
    são toleradas: a simples carga da página já costuma revelar endpoints.
    """
    try:
        campo = pagina.locator(config.seletores.campo_busca).first
        await campo.wait_for(state="visible", timeout=8_000)
        await campo.fill(termo)
        await campo.press("Enter")
        await pagina.wait_for_timeout(3_000)
    except Exception as erro:  # noqa: BLE001 - busca é o melhor esforço
        log.debug("Não foi possível submeter a busca: %s", erro)

    try:
        botao = pagina.locator(config.seletores.botao_buscar).first
        if await botao.is_visible(timeout=3_000):
            await botao.click(timeout=5_000)
            await pagina.wait_for_timeout(3_000)
    except Exception as erro:  # noqa: BLE001
        log.debug("Botão de busca não acionado: %s", erro)
