# -*- coding: utf-8 -*-
"""Baixa os PDFs dos pareceres catalogados, do mais novo para o mais antigo.
Retomavel: pula o que ja existe em disco."""
import json, os, re, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

from caminhos import BASE, PDFS as PDFDIR
CAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "selecionados.jsonl")
UPLOAD = "https://documentacao.pge.rj.gov.br/scripts/bnweb/bnmapi.exe?router=upload/%s"
FALHAS = os.path.join(BASE, "_falhas_download.txt")

lock = threading.Lock()
stats = {"ok": 0, "pulado": 0, "falha": 0, "bytes": 0}


def limpa(nome):
    nome = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", nome).strip(". ")
    return nome[:150] or "sem_nome"


def alvo(rec, ax):
    ano = rec.get("anodoc") or "sem_ano"
    d = os.path.join(PDFDIR, str(ano))
    arq = ax.get("arquivo") or ("anexo_%s.pdf" % ax["cod_anexo"])
    if not os.path.splitext(arq)[1]:
        arq += (ax.get("extensao") or ".pdf").lower()
    return d, "%s_%s" % (rec["codigo"], limpa(arq))


def baixa(item):
    rec, ax = item
    d, nome = alvo(rec, ax)
    caminho = os.path.join(d, nome)
    if os.path.exists(caminho) and os.path.getsize(caminho) > 1000:
        with lock:
            stats["pulado"] += 1
        return
    os.makedirs(d, exist_ok=True)
    url = UPLOAD % ax["cod_anexo"]
    for tentativa in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
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
    tarefas = []
    vistos = set()
    with open(CAT, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            for ax in rec.get("anexos") or []:
                if ax.get("fonte"):      # anexo herdado de andamento/precedente
                    continue
                if ax["cod_anexo"] in vistos:
                    continue
                vistos.add(ax["cod_anexo"])
                tarefas.append((rec, ax))
    tarefas.sort(key=lambda t: -t[0]["codigo"])   # do mais novo para o mais antigo
    total = len(tarefas)
    print("anexos proprios a baixar: %d" % total, flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        for i, _ in enumerate(ex.map(baixa, tarefas), 1):
            if i % 200 == 0:
                dec = time.time() - t0
                print("%d/%d  ok=%d pulado=%d falha=%d  %.1f GB  %.0f/min"
                      % (i, total, stats["ok"], stats["pulado"], stats["falha"],
                         stats["bytes"] / 1e9, i / max(dec, 1) * 60), flush=True)
    print("FIM  ok=%d pulado=%d falha=%d  total=%.2f GB  em %.0f min"
          % (stats["ok"], stats["pulado"], stats["falha"], stats["bytes"] / 1e9,
             (time.time() - t0) / 60), flush=True)


if __name__ == "__main__":
    main()
