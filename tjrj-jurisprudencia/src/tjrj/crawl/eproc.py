"""Coletor do eproc — a base nova (decisões incorporadas a partir de 05/02/2026).

O eproc é PHP (linhagem TRF4) e, ao contrário do eJURIS, é razoavelmente
amigável: as ações vão em `externo_controlador.php?acao=...` e a paginação
costuma ser um parâmetro, não um post de formulário inteiro. Ainda assim,
duas armadilhas:

* **Cookie de sessão.** A primeira requisição estabelece a sessão; sem
  reaproveitá-la, a segunda cai numa página de erro que devolve HTTP 200 —
  erro que se parece com "nenhum resultado".
* **Dois graus, dois hosts.** 1º e 2º grau são instalações distintas. Uma
  base "do TJRJ" que aponte só para uma delas está pela metade.

O eproc é também a fonte das **partes**, via consulta pública processual —
e é por isso que ele merece uma leitura atenta de docs/JURIDICO.md antes de
ser ligado no modo que preenche a tabela `parte`.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Iterator

from ..config import CFG, Config
from ..http import Cliente
from ..parse.normalize import numero_cnj
from .base import NaoCalibrado, Referencia, ResultadoBusca, Teor
from .planner import Fatia

log = logging.getLogger("tjrj.eproc")

ACAO_JURIS = "externo_controlador.php?acao=jurisprudencia_pesquisar"
ACAO_PROCESSO = "externo_controlador.php?acao=processo_consulta_publica"

# CALIBRAR: nomes reais dos parâmetros da busca de jurisprudência.
PARAMS: dict[str, str | None] = {
    "data_inicial": None,     # ex.: "dta_inicial"
    "texto": None,
    "orgao_julgador": None,
    "data_final": None,
    "pagina": None,
    "tipo_decisao": None,
}

SELETORES: dict[str, str | None] = {
    "linha_resultado": None,
    "total": None,
    "link_teor": None,
}

_RE_TOTAL = re.compile(r"([\d.]+)\s+(?:documento|resultado|registro)s?\b", re.I)


class EProc:
    nome = "eproc"

    def __init__(self, cliente: Cliente | None = None, cfg: Config = CFG, grau: str = "2"):
        self.cfg = cfg
        self.grau = grau
        self.cliente = cliente or Cliente(cfg)

    @property
    def base(self) -> str:
        raiz = self.cfg.eproc_2g_base if self.grau == "2" else self.cfg.eproc_base
        return raiz.rstrip("/") + "/"

    def _params(self, fatia: Fatia, pagina: int = 1) -> dict[str, Any]:
        faltando = [k for k in ("data_inicial", "data_final") if not PARAMS[k]]
        if faltando:
            raise NaoCalibrado(f"eproc: parâmetros {faltando}")
        p: dict[str, Any] = {
            PARAMS["data_inicial"]: fatia.inicio.strftime("%d/%m/%Y"),
            PARAMS["data_final"]: fatia.fim.strftime("%d/%m/%Y"),
        }
        if PARAMS.get("pagina"):
            p[PARAMS["pagina"]] = pagina
        for chave, valor in fatia.facetas.items():
            nome = PARAMS.get(chave)
            if not nome:
                raise NaoCalibrado(f"eproc: faceta '{chave}'")
            p[nome] = valor
        return p

    def contar(self, fatia: Fatia) -> int:
        r = self.cliente.pegar(self.base + ACAO_JURIS, params=self._params(fatia))
        m = _RE_TOTAL.search(r.texto)
        return int(m.group(1).replace(".", "")) if m else 0

    def listar(self, fatia: Fatia) -> Iterator[ResultadoBusca]:
        vistos: set[str] = set()
        pagina = 1
        while True:
            r = self.cliente.pegar(self.base + ACAO_JURIS, params=self._params(fatia, pagina))
            linhas = list(_extrair_linhas(r.texto, self.base, self.grau))
            novos = [x for x in linhas if x.referencia.id_externo not in vistos]
            if not novos:
                return  # página repetida ou vazia: fim real da fatia
            for res in novos:
                vistos.add(res.referencia.id_externo)
                yield res
            if not PARAMS.get("pagina"):
                return
            pagina += 1

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
        return []

    # -- partes ----------------------------------------------------------
    def partes(self, numero: str) -> list[dict[str, Any]]:
        """Partes e advogados pela consulta pública processual.

        Leia docs/JURIDICO.md antes de usar em massa: nome de parte é dado
        pessoal, processo em segredo de justiça não entra, e o que se pode
        guardar não é o mesmo que se pode publicar.
        """
        if not SELETORES.get("linha_resultado"):
            raise NaoCalibrado("eproc: consulta pública de partes")
        r = self.cliente.pegar(self.base + ACAO_PROCESSO, params={"num_processo": numero})
        return _extrair_partes(r.texto)


def _extrair_linhas(html: str, base: str, grau: str) -> Iterator[ResultadoBusca]:
    seletor = SELETORES.get("linha_resultado")
    if not seletor:
        raise NaoCalibrado("eproc: seletor de linha de resultado")

    from selectolax.parser import HTMLParser

    for no in HTMLParser(html).css(seletor):
        texto = no.text(separator=" ", strip=True)
        link = no.css_first(SELETORES.get("link_teor") or "a")
        href = link.attributes.get("href") if link else None
        url = href if (href or "").startswith("http") else (base + (href or "")) if href else None
        yield ResultadoBusca(
            referencia=Referencia(
                id_externo=url or texto[:120], sistema="eproc", url=url, extra={"grau": grau}
            ),
            numero_cnj=numero_cnj(texto),
            ementa=texto,
            url_fonte=url,
            bruto={"html": no.html},
        )


def _extrair_partes(html: str) -> list[dict[str, Any]]:
    raise NaoCalibrado("eproc: extração de partes")
