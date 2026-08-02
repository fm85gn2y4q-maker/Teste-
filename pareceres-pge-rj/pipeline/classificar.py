# -*- coding: utf-8 -*-
"""Seleciona, no acervo integral da PGE-RJ, os documentos sobre contratacoes,
acordos e parcerias (1o, 2o e 3o setores), e os classifica por eixo tematico.
A selecao e feita localmente sobre ementa + assuntos indexados + leis citadas."""
import json, os, re, unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
ENTRADA = os.path.join(AQUI, "catalogo_pgerj_total.jsonl")


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def rx(p):
    return re.compile(p, re.I)


# --- leis que, citadas, praticamente definem a materia -----------------------
LEIS = rx(r"\b(8\.?666|14\.?133|10\.?520|13\.?019|8\.?987|11\.?079|9\.?637|9\.?790|"
          r"12\.?462|13\.?303|11\.?107|14\.?026|12\.?232)\b")

# --- descritores/expressoes que sozinhos ja caracterizam --------------------
FORTE = rx(r"licita|licitat|pregao|edital|concorrencia publica|tomada de preco|"
           r"dialogo competitivo|registro de preco|ata de registro|credenciamento|"
           r"dispensa de licitacao|inexigibilidade|contratacao direta|contrato administrativo|"
           r"termo aditivo|aditamento contratual|alteracao contratual|prorrogacao de contrato|"
           r"prorrogacao contratual|reequilibrio|repactuacao|rescisao contratual|"
           r"termo de referencia|projeto basico|projeto executivo|estudo tecnico preliminar|"
           r"servico de engenharia|fiscal do contrato|sancao administrativa|"
           r"penalidade contratual|inadimplemento contratual|"
           r"convenio|termo de colaboracao|termo de fomento|acordo de cooperacao|"
           r"cooperacao tecnica|chamamento publico|convocacao publica|mrosc|"
           r"organizacao social|organizacao da sociedade civil|oscip|contrato de gestao|"
           r"termo de parceria|entidade filantropica|"
           r"parceria publico-privada|concessao de servico|permissao de servico|"
           r"concessao de uso|permissao de uso|cessao de uso|concessao administrativa|"
           r"concessao patrocinada|contrato de concessao|termo de outorga|"
           r"consorcio publico|contrato de programa|contrato de rateio|"
           r"minuta de edital|minuta de contrato|minuta padrao|pesquisa de preco|"
           r"menor preco|maior desconto|tecnica e preco|proposta comercial|"
           r"documentos? de habilitacao|habilitacao (juridica|tecnica|fiscal|economic)|"
           r"licitante|subcontratacao|garantia contratual")

# --- termos ambiguos: so contam se houver corroboracao ----------------------
AMBIGUO = rx(r"\bcontrato\b|\bcontratacao\b|\bcontratada?\b|prestacao de servico|"
             r"\bprorrogacao\b|\breajuste\b|\bconcessao\b|\bcessao\b|\bpermissao\b|"
             r"\bobra\b|obra publica|concessionaria|permissionaria|\bleilao\b|"
             r"\bfornecimento\b|\bempenho\b|habilitacao")
# corroboracao exige vocabulario de contratacao, nao apenas de direito publico
CORROBORA = rx(r"contrat|licita|edital|convenio|aditiv|minuta|proposta|"
               r"execucao do (contrato|ajuste)|equilibrio economico|pagamento de|"
               r"despesa publica|dotacao|empenho|objeto do ajuste|ajuste")

# --- exclusoes: homonimos de outro ramo -------------------------------------
NEGATIVO = rx(r"contrato de trabalho|sucessao trabalhista|\bfgts\b|contratacao temporaria|"
              r"reajuste de salario|contrato de financiamento|contrato de mutuo|"
              r"tempo de servico|averbacao|aposentadoria|pensao|licenca-premio|"
              r"progressao funcional|contrato de locacao de imovel residencial|"
              r"plano de saude|contrato de seguro de vida|contrato de cambio")

EIXOS = [
    ("Licitacao", rx(r"licita|pregao|edital|concorrencia|tomada de preco|dialogo competitivo|"
                     r"leilao|registro de preco|credenciamento|chamamento publico|"
                     r"convocacao publica|licitante|habilitacao|menor preco|tecnica e preco|"
                     r"pesquisa de preco|14\.?133|8\.?666|10\.?520")),
    ("Contratacao direta", rx(r"dispensa de licitacao|\bdispensa\b|inexigibilidade|contratacao direta")),
    ("Contrato administrativo", rx(r"contrato administrativo|termo aditivo|aditamento|"
                                   r"alteracao contratual|prorrogacao|reequilibrio|repactuacao|"
                                   r"reajuste|rescisao|termo de referencia|projeto basico|"
                                   r"sancao administrativa|penalidade|inadimplemento|"
                                   r"fiscal do contrato|garantia contratual|subcontratacao")),
    ("Obras e engenharia", rx(r"obra publica|\bobra\b|servico de engenharia|projeto executivo|"
                              r"medicao|cronograma fisico|12\.?462|\brdc\b")),
    ("Terceiro setor", rx(r"organizacao social|organizacao da sociedade civil|oscip|"
                          r"contrato de gestao|termo de parceria|termo de colaboracao|"
                          r"termo de fomento|acordo de cooperacao|mrosc|filantrop|"
                          r"9\.?637|9\.?790|13\.?019")),
    ("Convenio e cooperacao", rx(r"convenio|cooperacao tecnica|consorcio publico|"
                                 r"contrato de programa|contrato de rateio|11\.?107")),
    ("Concessao, PPP e uso de bem", rx(r"concessao|permissao|cessao de uso|permissionaria|"
                                       r"concessionaria|parceria publico-privada|8\.?987|11\.?079")),
    ("Estatais", rx(r"13\.?303|empresa publica|sociedade de economia mista|estatal")),
]


def texto_do(r):
    partes = [r.get("titulo") or "", r.get("ementa") or "", r.get("resumo") or "",
              r.get("notas") or "", r.get("classificacao") or ""]
    partes += [a.get("nome", "") for a in (r.get("assuntos") or [])]
    return norm(" ".join(partes))


def avalia(r):
    """Retorna (tematico: bool, eixos: list, motivo: str)."""
    t = texto_do(r)
    assuntos = norm(" | ".join(a.get("nome", "") for a in (r.get("assuntos") or [])))
    ementa = norm(r.get("ementa") or "")

    forte = bool(FORTE.search(t))
    lei = bool(LEIS.search(t))
    ambiguo = bool(AMBIGUO.search(assuntos) or AMBIGUO.search(ementa))
    corrob = bool(CORROBORA.search(t))
    negativo = bool(NEGATIVO.search(t))

    if forte or lei:
        tematico, motivo = True, ("descritor forte" if forte else "lei de regencia")
        if negativo and not forte:
            tematico, motivo = False, "homonimo de outro ramo"
    elif ambiguo and corrob and not negativo:
        tematico, motivo = True, "termo ambiguo corroborado"
    else:
        tematico, motivo = False, "sem sinal tematico"

    eixos = [nome for nome, pat in EIXOS if pat.search(t)] if tematico else []
    return tematico, eixos, motivo


def main():
    recs = [json.loads(l) for l in open(ENTRADA, encoding="utf-8")]
    sel, fora = [], []
    for r in recs:
        ok, eixos, motivo = avalia(r)
        r["_eixos"], r["_motivo"] = eixos, motivo
        (sel if ok else fora).append(r)
    print("acervo total: %d | tematicos: %d (%.1f%%) | descartados: %d"
          % (len(recs), len(sel), 100 * len(sel) / len(recs), len(fora)))
    import collections
    print("\nmotivos (incluidos):", collections.Counter(r["_motivo"] for r in sel).most_common())
    print("eixos:", collections.Counter(e for r in sel for e in (r["_eixos"] or ["(nenhum)"])).most_common())
    com = sum(1 for r in sel if [a for a in (r.get("anexos") or []) if not a.get("fonte")])
    print("\ntematicos com PDF proprio: %d" % com)
    with open(os.path.join(AQUI, "selecionados.jsonl"), "w", encoding="utf-8") as f:
        for r in sel:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(AQUI, "descartados.jsonl"), "w", encoding="utf-8") as f:
        for r in fora:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
