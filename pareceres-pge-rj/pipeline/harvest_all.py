# -*- coding: utf-8 -*-
"""Colhe o catalogo de pareceres da PGE-RJ (BNPortal) sobre contratacoes,
acordos e parcerias (1o, 2o e 3o setores)."""
import json, os, sys, time, urllib.parse, urllib.request

API = "https://documentacao.pge.rj.gov.br/scripts/bnweb/bnmapi.exe?router=search"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalogo_pgerj_total.jsonl")
STATE = OUT + ".state"

TERMOS = [
    "LICITAÇÃO", "LICITATÓRIO", "EDITAL", "PREGÃO", "CONCORRÊNCIA PÚBLICA",
    "TOMADA DE PREÇOS", "DIÁLOGO COMPETITIVO", "REGISTRO DE PREÇOS", "CREDENCIAMENTO",
    "DISPENSA DE LICITAÇÃO", "INEXIGIBILIDADE", "CONTRATAÇÃO DIRETA",
    "CONTRATO ADMINISTRATIVO", "TERMO ADITIVO", "PRORROGAÇÃO CONTRATUAL",
    "REEQUILÍBRIO", "REPACTUAÇÃO", "REAJUSTE CONTRATUAL", "RESCISÃO CONTRATUAL",
    "TERMO DE REFERÊNCIA", "PROJETO BÁSICO", "CONVÊNIO", "TERMO DE COLABORAÇÃO",
    "TERMO DE FOMENTO", "ACORDO DE COOPERAÇÃO", "MROSC", "ORGANIZAÇÃO SOCIAL",
    "OSCIP", "CONTRATO DE GESTÃO", "TERMO DE PARCERIA", "PARCERIA PÚBLICO-PRIVADA",
    "CONCESSÃO DE SERVIÇO PÚBLICO", "PERMISSÃO DE SERVIÇO PÚBLICO", "CONCESSÃO DE USO",
    "PERMISSÃO DE USO", "CESSÃO DE USO", "CHAMAMENTO PÚBLICO", "CONVOCAÇÃO PÚBLICA",
]
EXP = ""

FIELDS = ("codigo,tipo_sigla,tipo_nome,titulo,datadoc,anodoc,ementa,numero,processo,"
          "precedentes,notas,resumo,classificacao")
EXPAND = "assuntos,links,anexos,membros,andamentos"
LIMIT = 200


def fetch(page, tries=5):
    params = {"page": str(page), "sort": "codigo desc",
              "filter": json.dumps({"exp": [EXP]}, ensure_ascii=False),
              "limit": str(LIMIT), "fields": FIELDS, "expand": EXPAND}
    url = API + "&" + urllib.parse.urlencode(params)
    err = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=180).read()
            return json.loads(raw.decode("utf-8", "ignore"))
        except Exception as e:
            err = e
            time.sleep(3 * (n + 1))
    raise err


def main():
    start = 1
    seen = set()
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            for line in f:
                try:
                    seen.add(json.loads(line)["codigo"])
                except Exception:
                    pass
    if os.path.exists(STATE):
        start = int(open(STATE).read().strip()) + 1

    d = fetch(1)
    total = d["pagination"]["total"]
    pages = d["pagination"]["page_count"]
    print("total=%d paginas=%d (retomando na pagina %d)" % (total, pages, start), flush=True)

    with open(OUT, "a", encoding="utf-8") as out:
        for p in range(start, pages + 1):
            d = fetch(p) if p != 1 else d
            novos = 0
            for rec in d.get("data", []):
                if rec["codigo"] in seen:
                    continue
                seen.add(rec["codigo"])
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                novos += 1
            out.flush()
            open(STATE, "w").write(str(p))
            print("pagina %d/%d  +%d  acumulado=%d" % (p, pages, novos, len(seen)), flush=True)
    print("FIM. registros unicos =", len(seen), flush=True)


if __name__ == "__main__":
    main()
