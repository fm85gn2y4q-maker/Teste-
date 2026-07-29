"""Coletor do eJURIS — a base histórica (acórdãos e monocráticas do eJUD).

O eJURIS é ASP.NET WebForms. Duas consequências práticas:

* **Estado no formulário.** Toda requisição precisa devolver `__VIEWSTATE`,
  `__VIEWSTATEGENERATOR` e `__EVENTVALIDATION` que vieram na página
  anterior, além de `__EVENTTARGET` para simular o clique. Paginar não é
  mudar um parâmetro na URL: é postar o formulário inteiro dizendo qual
  botão foi apertado.
* **Sessão importa.** Os tokens são válidos para aquela sessão e aquela
  página. Reaproveitar o `__VIEWSTATE` de uma busca em outra devolve erro
  ou, pior, o resultado da busca anterior.

Os nomes dos campos abaixo estão marcados como CALIBRAR. Não os adivinhe:
rode `python -m tjrj.tools.calibrar ejuris`, que salva o HTML real e lista
os campos do formulário, e preencha com o que aparecer.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any, Iterator

from ..config import CFG, Config
from ..http import Cliente
from ..parse.normalize import numero_cnj
from .base import NaoCalibrado, Referencia, ResultadoBusca, Teor
from .planner import Fatia

log = logging.getLogger("tjrj.ejuris")

PAGINA_BUSCA = "ConsultarJurisprudencia.aspx"

# ---------------------------------------------------------------------------
# CALIBRAR: nomes reais dos campos do formulário e dos elementos de resultado.
# O valor None significa "ainda não confirmado contra o site" — e faz o
# coletor levantar NaoCalibrado em vez de devolver vazio silenciosamente.
# ---------------------------------------------------------------------------
CAMPOS: dict[str, str | None] = {
    "data_inicial": None,      # ex.: "ctl00$ContentPlaceHolder1$txtDataInicial"
    "data_final": None,        # ex.: "ctl00$ContentPlaceHolder1$txtDataFinal"
    "texto": None,             # campo de pesquisa livre
    "orgao_julgador": None,
    "tipo_decisao": None,
    "botao_pesquisar": None,   # __EVENTTARGET do botão
}

SELETORES: dict[str, str | None] = {
    "linha_resultado": None,   # ex.: "div.linkArquivo" ou "table#tabResultado tr"
    "total": None,             # elemento com "N documentos encontrados"
    "link_teor": None,         # âncora para o inteiro teor
    "proxima_pagina": None,    # __EVENTTARGET da próxima página
}

_RE_TOTAL = re.compile(r"([\d.]+)\s+(?:documento|resultado|registro)s?\b", re.I)
_RE_DATA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_CAMPOS_ESTADO = ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION", "__VIEWSTATEENCRYPTED")


class EJuris:
    nome = "ejuris"

    def __init__(self, cliente: Cliente | None = None, cfg: Config = CFG):
        self.cfg = cfg
        self.cliente = cliente or Cliente(cfg)
        self._estado: dict[str, str] = {}

    # -- infraestrutura WebForms ----------------------------------------
    @property
    def url_busca(self) -> str:
        return self.cfg.ejuris_base.rstrip("/") + "/" + PAGINA_BUSCA

    def _abrir_formulario(self) -> str:
        r = self.cliente.pegar(self.url_busca, cache=False)  # tokens não se cacheiam
        html = r.texto
        self._estado = extrair_estado(html)
        if "__VIEWSTATE" not in self._estado:
            raise NaoCalibrado(
                "eJURIS: __VIEWSTATE",
                "a página não devolveu o formulário esperado — verifique se a URL mudou.",
            )
        return html

    def _postar(self, evento: str, campos: dict[str, Any]) -> str:
        corpo = {**self._estado, "__EVENTTARGET": evento, "__EVENTARGUMENT": "", **campos}
        r = self.cliente.pegar(self.url_busca, metodo="POST", dados=corpo, cache=False)
        html = r.texto
        novo = extrair_estado(html)
        if novo:
            self._estado = novo  # o estado avança a cada post; guardar o velho quebra a paginação
        return html

    def _campos_da_fatia(self, fatia: Fatia) -> dict[str, Any]:
        faltando = [k for k in ("data_inicial", "data_final", "botao_pesquisar") if not CAMPOS[k]]
        if faltando:
            raise NaoCalibrado(f"eJURIS: campos {faltando}")
        campos = {
            CAMPOS["data_inicial"]: fatia.inicio.strftime("%d/%m/%Y"),
            CAMPOS["data_final"]: fatia.fim.strftime("%d/%m/%Y"),
        }
        for chave, valor in fatia.facetas.items():
            nome = CAMPOS.get(chave)
            if not nome:
                raise NaoCalibrado(f"eJURIS: faceta '{chave}'")
            campos[nome] = valor
        return campos

    # -- contrato Coletor -----------------------------------------------
    def contar(self, fatia: Fatia) -> int:
        self._abrir_formulario()
        html = self._postar(CAMPOS["botao_pesquisar"] or "", self._campos_da_fatia(fatia))
        return ler_total(html)

    def listar(self, fatia: Fatia) -> Iterator[ResultadoBusca]:
        self._abrir_formulario()
        html = self._postar(CAMPOS["botao_pesquisar"] or "", self._campos_da_fatia(fatia))

        vistos: set[str] = set()
        pagina = 1
        while True:
            linhas = list(_extrair_linhas(html))
            if not linhas:
                if pagina == 1:
                    log.info("eJURIS: fatia %s sem resultados", fatia)
                return

            for res in linhas:
                # A paginação WebForms às vezes repete a última página quando
                # o post falha. Sem esta guarda, o laço nunca termina.
                if res.referencia.id_externo in vistos:
                    continue
                vistos.add(res.referencia.id_externo)
                yield res

            alvo = SELETORES.get("proxima_pagina")
            if not alvo or not _tem_proxima(html):
                return
            pagina += 1
            html = self._postar(alvo, {})

    def obter_teor(self, ref: Referencia) -> Teor | None:
        if not ref.url:
            return None
        r = self.cliente.pegar(ref.url)
        if r.status != 200 or not r.conteudo:
            return None
        from ..parse.texto import paginar

        paginas, origem = paginar(r.conteudo, r.headers.get("content-type", ""))
        return Teor(referencia=ref, paginas=paginas, origem=origem, url=ref.url)

    def valores_de_faceta(self, chave: str, fatia: Fatia) -> list[str]:
        if chave != "orgao_julgador":
            return []
        html = self._abrir_formulario()
        return _opcoes_do_select(html, CAMPOS.get("orgao_julgador"))


# --- funções puras, testáveis sem rede --------------------------------------

_RE_INPUT_HIDDEN = re.compile(
    r"<input[^>]+type=[\"']hidden[\"'][^>]*>", re.I
)
_RE_ATTR = re.compile(r"(\w+)=[\"']([^\"']*)[\"']")


def extrair_estado(html: str) -> dict[str, str]:
    """Lê __VIEWSTATE e companhia do HTML."""
    estado: dict[str, str] = {}
    for tag in _RE_INPUT_HIDDEN.findall(html or ""):
        attrs = dict(_RE_ATTR.findall(tag))
        nome = attrs.get("name") or attrs.get("id")
        if nome in _CAMPOS_ESTADO:
            estado[nome] = attrs.get("value", "")
    return estado


def ler_total(html: str) -> int:
    """Extrai 'N documentos encontrados'. Zero quando não encontra o rótulo.

    Um total ilegível é tratado como zero de propósito? Não: devolvemos 0 e
    quem chama deve tratar 0 com desconfiança quando a lista vier cheia. Ver
    `planner.total_por_sondagem` para o caminho alternativo.
    """
    m = _RE_TOTAL.search(html or "")
    if not m:
        return 0
    return int(m.group(1).replace(".", ""))


def ler_data(texto: str) -> date | None:
    m = _RE_DATA.search(texto or "")
    if not m:
        return None
    try:
        return datetime.strptime(m.group(0), "%d/%m/%Y").date()
    except ValueError:
        return None


def _extrair_linhas(html: str) -> Iterator[ResultadoBusca]:
    seletor = SELETORES.get("linha_resultado")
    if not seletor:
        raise NaoCalibrado("eJURIS: seletor de linha de resultado")

    from selectolax.parser import HTMLParser  # dependência só do caminho com rede

    arvore = HTMLParser(html)
    for no in arvore.css(seletor):
        texto = no.text(separator=" ", strip=True)
        link = no.css_first(SELETORES.get("link_teor") or "a")
        url = link.attributes.get("href") if link else None
        ident = url or texto[:120]
        yield ResultadoBusca(
            referencia=Referencia(id_externo=ident, sistema="ejuris", url=url),
            numero_cnj=numero_cnj(texto),
            data_julgamento=ler_data(texto),
            ementa=texto,
            url_fonte=url,
            bruto={"html": no.html},
        )


def _tem_proxima(html: str) -> bool:
    alvo = SELETORES.get("proxima_pagina")
    return bool(alvo and alvo in (html or ""))


def _opcoes_do_select(html: str, nome_campo: str | None) -> list[str]:
    if not nome_campo:
        return []
    from selectolax.parser import HTMLParser

    arvore = HTMLParser(html)
    select = arvore.css_first(f'select[name="{nome_campo}"]')
    if select is None:
        return []
    valores = []
    for op in select.css("option"):
        v = op.attributes.get("value") or ""
        if v and v not in ("0", "-1", ""):
            valores.append(v)
    return valores
