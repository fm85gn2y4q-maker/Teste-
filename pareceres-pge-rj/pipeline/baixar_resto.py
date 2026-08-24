# -*- coding: utf-8 -*-
"""Baixa os PDFs do acervo que ficaram FORA do recorte tematico.

O recorte de contratacoes, acordos e parcerias trouxe 14.420 dos 49.139
documentos. Ficaram de fora 34.719 -- e um deles era o Parecer LRB 01/2007, de
Barroso, sobre defesa de agentes publicos pela PGE: materia institucional, nao
de contratacao, e por isso ausente por construcao.

Sao 14.592 arquivos, ~21 GB, ~12 h. Retomavel: pula o que ja existe em disco,
e vai do mais novo para o mais antigo, para o material recente chegar primeiro.
"""
import collections
import json
import os
import re
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from caminhos import BASE, PDFS as PDFDIR
AQUI = os.path.dirname(os.path.abspath(__file__))
CATALOGO = os.environ.get("PARECERES_CATALOGO", os.path.join(AQUI, "catalogo_pgerj_total.jsonl"))
UPLOAD = "https://documentacao.pge.rj.gov.br/scripts/bnweb/bnmapi.exe?router=upload/%s"
FALHAS = os.path.join(BASE, "_falhas_download_resto.txt")

lock = threading.Lock()
stats = collections.Counter()


def limpa(nome):
    nome = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", nome).strip(". ")
    return nome[:150] or "sem_nome"


def alvo(rec, ax):
    ano = rec.get("anodoc") or "sem_ano"
    arq = ax.get("arquivo") or ("anexo_%s.pdf" % ax["cod_anexo"])
    if not os.path.splitext(arq)[1]:
        arq += (ax.get("extensao") or ".pdf").lower()
    return os.path.join(PDFDIR, str(ano)), "%s_%s" % (rec["codigo"], limpa(arq))


def baixa(item):
    rec, ax = item
    pasta, nome = alvo(rec, ax)
    caminho = os.path.join(pasta, nome)
    if os.path.exists(caminho) and os.path.getsize(caminho) > 1000:
        with lock:
            stats["pulado"] += 1
        return
    os.makedirs(pasta, exist_ok=True)
    for tentativa in range(4):
        try:
            req = urllib.request.Request(UPLOAD % ax["cod_anexo"],
                                         headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                dados = r.read()
            if len(dados) < 1000:
                raise ValueError("resposta muito pequena (%d B)" % len(dados))
            tmp = caminho + ".part"
            with open(tmp, "wb") as f:
                f.write(dados)
            os.replace(tmp, caminho)
            with lock:
                stats["ok"] += 1
                stats["bytes"] += len(dados)
            time.sleep(0.15)
            return
        except Exception as e:
            erro = e
            time.sleep(2 * (tentativa + 1))
    with lock:
        stats["falha"] += 1
        with open(FALHAS, "a", encoding="utf-8") as f:
            f.write("%s\t%s\t%s\t%s\n" % (rec["codigo"], ax["cod_anexo"], nome, erro))


def main():
    tarefas, vistos = [], set()
    for linha in open(CATALOGO, encoding="utf-8"):
        rec = json.loads(linha)
        for ax in rec.get("anexos") or []:
            if ax.get("fonte") or ax["cod_anexo"] in vistos:
                continue
            vistos.add(ax["cod_anexo"])
            tarefas.append((rec, ax))
    tarefas.sort(key=lambda t: -t[0]["codigo"])
    total = len(tarefas)
    print("anexos no acervo inteiro: %d" % total, flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        for i, _ in enumerate(ex.map(baixa, tarefas), 1):
            if i % 500 == 0:
                dec = time.time() - t0
                livre = 0
                try:
                    import shutil as _s
                    livre = _s.disk_usage(BASE).free / 1e9
                except Exception:
                    pass
                print("%d/%d  ok=%d pulado=%d falha=%d  %.1f GB baixados  %.0f/min  livre=%.1f GB"
                      % (i, total, stats["ok"], stats["pulado"], stats["falha"],
                         stats["bytes"] / 1e9, i / max(dec, 1) * 60, livre), flush=True)
                if livre and livre < 3:
                    print("PARANDO: menos de 3 GB livres no disco.", flush=True)
                    break
    print("FIM  ok=%d pulado=%d falha=%d  %.1f GB  em %.0f min"
          % (stats["ok"], stats["pulado"], stats["falha"],
             stats["bytes"] / 1e9, (time.time() - t0) / 60), flush=True)


if __name__ == "__main__":
    main()
