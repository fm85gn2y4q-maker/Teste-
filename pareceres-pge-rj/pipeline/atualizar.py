# -*- coding: utf-8 -*-
"""Colhe do portal so o que entrou depois da ultima coleta.

O `harvest_all.py` varre as 246 paginas do acervo inteiro. Para uma atualizacao
isso e desperdicio: o portal ordena por `codigo desc`, entao o material novo
esta todo nas primeiras paginas, e basta descer ate reencontrar o que ja temos.

O criterio de parada NAO e o maior codigo local. E duas paginas seguidas sem
nenhum registro novo -- porque um documento excluido do portal desloca a
paginacao, e parar no primeiro codigo conhecido deixaria de fora o que veio
logo atras.

Limite conhecido: isto acha documento NOVO, nao documento EDITADO. Ementa
corrigida ou anexo trocado num codigo antigo passa despercebido; para isso, o
que serve e recolher tudo com o `harvest_all.py`.

    python atualizar.py            # colhe e grava
    python atualizar.py --so-ver   # so diz quantos ha, sem gravar

Grava os novos no fim de `catalogo_pgerj_total.jsonl` e a lista de codigos em
`novos.txt`, que e o que as etapas seguintes leem.
"""
import datetime
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

API = "https://documentacao.pge.rj.gov.br/scripts/bnweb/bnmapi.exe?router=search"
AQUI = os.path.dirname(os.path.abspath(__file__))
CATALOGO = os.path.join(AQUI, "catalogo_pgerj_total.jsonl")
NOVOS = os.path.join(AQUI, "novos.txt")

# Os mesmos campos da coleta original: registro novo precisa ter a mesma forma
# do antigo, ou a indexacao encontra chave faltando na metade do acervo.
FIELDS = ("codigo,tipo_sigla,tipo_nome,titulo,datadoc,anodoc,ementa,numero,processo,"
          "precedentes,notas,resumo,classificacao")
EXPAND = "assuntos,links,anexos,membros,andamentos"
LIMIT = 200
PACIENCIA = 2      # paginas seguidas sem novidade que encerram a varredura
TETO = 40          # paginas, ~8.000 documentos: mais que isso e recoleta


def buscar(pagina, tentativas=6):
    params = {"page": str(pagina), "sort": "codigo desc",
              "filter": json.dumps({"exp": [""]}, ensure_ascii=False),
              "limit": str(LIMIT), "fields": FIELDS, "expand": EXPAND}
    url = API + "&" + urllib.parse.urlencode(params)
    erro = None
    for n in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            bruto = urllib.request.urlopen(req, timeout=180).read()
            return json.loads(bruto.decode("utf-8", "ignore"))
        except Exception as e:
            erro = e
            time.sleep(3 * (n + 1))
    raise erro


def conhecidos():
    vistos = set()
    if os.path.exists(CATALOGO):
        with io.open(CATALOGO, encoding="utf-8") as f:
            for linha in f:
                try:
                    vistos.add(json.loads(linha)["codigo"])
                except Exception:
                    pass
    return vistos


def main():
    so_ver = "--so-ver" in sys.argv
    vistos = conhecidos()
    print("catalogo local: %d documentos (maior codigo %d)"
          % (len(vistos), max(vistos) if vistos else 0), flush=True)

    d = buscar(1)
    total = d["pagination"]["total"]
    print("portal agora: %d documentos  (diferenca: %+d)"
          % (total, total - len(vistos)), flush=True)

    novos, secas, pagina = [], 0, 1
    while pagina <= TETO and secas < PACIENCIA:
        d = d if pagina == 1 else buscar(pagina)
        achados = [r for r in d.get("data", []) if r["codigo"] not in vistos]
        for r in achados:
            vistos.add(r["codigo"])
        novos.extend(achados)
        secas = 0 if achados else secas + 1
        print("  pagina %d: +%d  (acumulado %d)" % (pagina, len(achados), len(novos)),
              flush=True)
        if pagina >= d["pagination"]["page_count"]:
            break
        pagina += 1

    if pagina > TETO:
        print("PARE: %d paginas sem fechar a diferenca. Ha muita coisa nova ou o\n"
              "catalogo esta defasado demais -- rode o harvest_all.py." % TETO,
              file=sys.stderr, flush=True)

    print("\nnovos: %d" % len(novos), flush=True)
    for r in novos[:15]:
        print("  %s  %s  %s" % (r["codigo"], r.get("datadoc"), (r.get("titulo") or "")[:70]),
              flush=True)
    if len(novos) > 15:
        print("  ... e mais %d" % (len(novos) - 15), flush=True)

    if so_ver or not novos:
        return 0

    with io.open(CATALOGO, "a", encoding="utf-8") as f:
        for r in sorted(novos, key=lambda x: x["codigo"]):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    io.open(os.path.join(AQUI, "coletado_em.txt"), "w", encoding="utf-8").write(
        datetime.date.today().isoformat() + "\n")
    with io.open(NOVOS, "w", encoding="utf-8") as f:
        for r in sorted(novos, key=lambda x: x["codigo"]):
            f.write("%d\n" % r["codigo"])
    print("\ngravados no catalogo. codigos em %s" % NOVOS, flush=True)
    print("proximo passo:  python incrementar.py", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
