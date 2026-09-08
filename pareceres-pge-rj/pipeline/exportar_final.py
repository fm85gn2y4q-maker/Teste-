# -*- coding: utf-8 -*-
"""Exporta o resultado final: CSV do nucleo tematico, CSV do acervo integral
(para conferencia) e estatisticas."""
import csv, json, os, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
from caminhos import REGISTROS as BASE
from classificar import avalia
UPLOAD = "https://documentacao.pge.rj.gov.br/scripts/bnweb/bnmapi.exe?router=upload/%s"
DETALHE = "https://documentacao.pge.rj.gov.br/bnportal/pt-BR/detalhes/%s"

COLS = ["codigo", "tipo", "titulo", "numero", "data", "ano", "eixos", "criterio",
        "ementa", "assuntos", "procuradores", "setores", "orgao_interessado",
        "processo", "precedentes", "tem_pdf", "arquivos", "url_pdf", "url_ficha"]


def linha(r):
    ass = [a.get("nome", "") for a in (r.get("assuntos") or [])]
    proprios = [a for a in (r.get("anexos") or []) if not a.get("fonte")]
    procs = [m.get("nome", "") for m in (r.get("membros") or []) if m.get("tipo_relacao") == 9]
    setores = sorted({m.get("nome_setor", "") for m in (r.get("membros") or []) if m.get("nome_setor")})
    orgaos = [m.get("nome", "") for m in (r.get("membros") or []) if m.get("tipo_relacao") == 10]
    return {
        "codigo": r.get("codigo"), "tipo": r.get("tipo_nome"), "titulo": r.get("titulo"),
        "numero": r.get("numero"), "data": r.get("datadoc"), "ano": r.get("anodoc"),
        "eixos": "; ".join(r.get("_eixos") or []), "criterio": r.get("_motivo", ""),
        "ementa": (r.get("ementa") or "").replace("\n", " ").replace(";", ",").strip(),
        "assuntos": " | ".join(ass), "procuradores": " | ".join(procs),
        "setores": " | ".join(setores), "orgao_interessado": " | ".join(orgaos),
        "processo": r.get("processo"),
        "precedentes": (r.get("precedentes") or "").replace("\n", " ").strip(),
        "tem_pdf": "sim" if proprios else "nao",
        "arquivos": " | ".join(a.get("arquivo", "") for a in proprios),
        "url_pdf": " | ".join(UPLOAD % a["cod_anexo"] for a in proprios),
        "url_ficha": DETALHE % r.get("codigo"),
    }


def grava(recs, caminho):
    recs = sorted(recs, key=lambda r: -(r.get("codigo") or 0))
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in recs:
            w.writerow(linha(r))
    print("gravado: %s (%d linhas)" % (caminho, len(recs)))


def main():
    os.makedirs(BASE, exist_ok=True)
    # O nucleo e CALCULADO, nao lido de arquivo. Ele vinha de
    # `selecionados.jsonl`, congelado na primeira coleta: documento novo sobre
    # licitacao ficava de fora do CSV de trabalho para sempre, sem sinal
    # nenhum. A regra de pertencer ao recorte mora em `avalia`, e e a mesma que
    # o `indexar_total` usa -- uma definicao so.
    tot = [json.loads(l) for l in open(os.path.join(AQUI, "catalogo_pgerj_total.jsonl"), encoding="utf-8")]
    historico = {json.loads(l)["codigo"]
                 for l in open(os.path.join(AQUI, "selecionados.jsonl"), encoding="utf-8")}
    sel = [r for r in tot if avalia(r)[0] or r["codigo"] in historico]
    grava(sel, os.path.join(BASE, "01_nucleo_contratacoes_parcerias.csv"))
    grava(tot, os.path.join(BASE, "02_acervo_integral_PGE-RJ.csv"))
    for nome, arq in [("selecionados.jsonl", "01_nucleo_contratacoes_parcerias.jsonl"),
                      ("catalogo_pgerj_total.jsonl", "02_acervo_integral_PGE-RJ.jsonl")]:
        with open(os.path.join(AQUI, nome), encoding="utf-8") as i, \
             open(os.path.join(BASE, arq), "w", encoding="utf-8") as o:
            o.write(i.read())

    anos = collections.Counter(r.get("anodoc") for r in sel)
    print("\npor decada:", sorted(collections.Counter(
        (a // 10 * 10) if isinstance(a, int) else "?" for a in anos.elements()).items(), key=lambda x: str(x[0])))
    print("tipos:", collections.Counter(r.get("tipo_nome") for r in sel).most_common(8))


if __name__ == "__main__":
    main()
