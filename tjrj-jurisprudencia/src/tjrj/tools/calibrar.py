"""Calibrador: descobre a estrutura real das páginas do TJRJ.

Por que este arquivo existe: os coletores de `crawl/` dependem de nomes de
campo e seletores que só o site real conhece, e **chutar** esses nomes é o
erro clássico deste tipo de projeto — o coletor "funciona", devolve zero
resultados, e a base nasce vazia sem nenhum erro na tela.

Então nada é chutado. Este script baixa as páginas, salva o HTML cru para
inspeção e imprime o que encontrou: campos de formulário, selects e seus
valores, tabelas candidatas a lista de resultados. Você (ou o Claude Code
rodando na sua máquina, com a página em mãos) preenche `CAMPOS` e
`SELETORES` com o que aparecer aqui.

    python -m tjrj.tools.calibrar ejuris
    python -m tjrj.tools.calibrar eproc
    python -m tjrj.tools.calibrar datajud
"""

from __future__ import annotations

import sys
from pathlib import Path

from ..config import CFG
from ..http import Cliente

SAIDA = CFG.dados / "calibracao"


def _salvar(nome: str, conteudo: bytes) -> Path:
    SAIDA.mkdir(parents=True, exist_ok=True)
    caminho = SAIDA / nome
    caminho.write_bytes(conteudo)
    return caminho


def _relatar_formulario(html: str) -> None:
    try:
        from selectolax.parser import HTMLParser
    except ImportError:
        print("!! instale selectolax para o relatório estruturado")
        return

    arvore = HTMLParser(html)

    print("\n--- CAMPOS DE FORMULÁRIO ---")
    for tag in arvore.css("input, select, textarea"):
        nome = tag.attributes.get("name") or tag.attributes.get("id")
        if not nome:
            continue
        tipo = tag.attributes.get("type", tag.tag)
        if nome.startswith("__"):
            print(f"  [estado] {nome}")
            continue
        print(f"  {nome:60s} tipo={tipo}")

    print("\n--- SELECTS E VALORES (candidatos a faceta) ---")
    for sel in arvore.css("select"):
        nome = sel.attributes.get("name") or sel.attributes.get("id") or "?"
        opcoes = [
            (o.attributes.get("value") or "", o.text(strip=True)) for o in sel.css("option")
        ]
        print(f"  {nome}  ({len(opcoes)} opções)")
        for v, t in opcoes[:8]:
            print(f"      {v!r:24s} {t[:60]}")
        if len(opcoes) > 8:
            print(f"      ... mais {len(opcoes) - 8}")

    print("\n--- BOTÕES (candidatos a __EVENTTARGET) ---")
    for b in arvore.css("input[type=submit], button, a[href^='javascript:__doPostBack']"):
        rotulo = b.attributes.get("value") or b.text(strip=True)
        alvo = b.attributes.get("name") or b.attributes.get("href", "")[:80]
        print(f"  {rotulo[:40]:40s} -> {alvo}")

    print("\n--- BLOCOS REPETIDOS (candidatos a linha de resultado) ---")
    contagem: dict[str, int] = {}
    for no in arvore.css("div, tr, li"):
        classe = no.attributes.get("class")
        if classe:
            chave = f"{no.tag}.{classe.split()[0]}"
            contagem[chave] = contagem.get(chave, 0) + 1
    for chave, n in sorted(contagem.items(), key=lambda x: -x[1])[:15]:
        print(f"  {n:5d}x  {chave}")


def calibrar_ejuris() -> None:
    from ..crawl.ejuris import PAGINA_BUSCA, extrair_estado

    url = CFG.ejuris_base.rstrip("/") + "/" + PAGINA_BUSCA
    print(f"GET {url}")
    with Cliente(CFG, cache=False) as c:
        r = c.pegar(url, cache=False)
    print(f"HTTP {r.status}  {len(r.conteudo)} bytes")
    print("salvo em:", _salvar("ejuris_busca.html", r.conteudo))

    estado = extrair_estado(r.texto)
    print(f"\ncampos de estado ASP.NET encontrados: {sorted(estado)}")
    if "__VIEWSTATE" not in estado:
        print("!! sem __VIEWSTATE: a URL provavelmente mudou ou houve redirecionamento")
    _relatar_formulario(r.texto)
    print(
        "\nPreencha CAMPOS e SELETORES em src/tjrj/crawl/ejuris.py com os nomes acima.\n"
        "Depois rode uma janela de 1 dia e confira o total contra a tela do site."
    )


def calibrar_eproc() -> None:
    from ..crawl.eproc import ACAO_JURIS

    for rotulo, base in (("1º grau", CFG.eproc_base), ("2º grau", CFG.eproc_2g_base)):
        url = base.rstrip("/") + "/" + ACAO_JURIS
        print(f"\n=== {rotulo}: GET {url}")
        try:
            with Cliente(CFG, cache=False) as c:
                r = c.pegar(url, cache=False)
        except Exception as e:
            print(f"!! {type(e).__name__}: {e}")
            continue
        print(f"HTTP {r.status}  {len(r.conteudo)} bytes")
        print("salvo em:", _salvar(f"eproc_{rotulo[0]}g.html", r.conteudo))
        _relatar_formulario(r.texto)


def calibrar_datajud() -> None:
    from datetime import date, timedelta

    from ..crawl.datajud import DataJud

    dj = DataJud()
    fim = date.today()
    inicio = fim - timedelta(days=7)
    print(f"contando processos ajuizados em {inicio}..{fim}")
    try:
        total = dj.contar(inicio, fim)
    except PermissionError as e:
        print(f"!! {e}")
        return
    print(f"total: {total}")

    print("\namostra de 1 processo (campos disponíveis):")
    for p in dj.varrer(inicio, fim, pagina=1):
        for k, v in sorted(p.bruto.items()):
            resumo = str(v)
            print(f"  {k:24s} {resumo[:90]}")
        print(f"\n  movimentos: {len(p.movimentos)}   assuntos: {len(p.assuntos)}")
        print("  >> confirme: há algum campo com ementa ou texto? (esperado: NÃO)")
        break


ALVOS = {"ejuris": calibrar_ejuris, "eproc": calibrar_eproc, "datajud": calibrar_datajud}


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv or argv[0] not in ALVOS:
        print(f"uso: python -m tjrj.tools.calibrar [{'|'.join(ALVOS)}]")
        return 2
    ALVOS[argv[0]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
