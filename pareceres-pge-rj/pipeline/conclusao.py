# -*- coding: utf-8 -*-
"""Extracao da conclusao do parecer, por formula de fecho.

Medido em amostra de 210 pareceres: o regex da primeira indexacao achava 37%;
este conjunto acha 91%. Os grupos estao em ordem de confianca -- uma formula
de conclusao propriamente dita vence um mero despacho de encaminhamento.
"""
import re
import unicodedata


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# O \b inicial de "exposto" evita casar "do o exposto" dentro de
# "ante todo o exposto", o que truncava a conclusao no meio da palavra.
GRUPOS = [
    ("exposto", r"\b(?:(?:ante|diante|em face|a vista|em vista|por tudo|isto|isso|pelo|do)"
                r"\s+(?:d[eo]\s+)?(?:todo\s+)?(?:o\s+)?exposto"
                r"|diante disso|posto isso|isso posto|isto posto)"),
    ("conclusao", r"\bconclus[ao]o\b|\bconclui-se\b|\bconcluo\b|\bem conclusao\b"),
    ("opino", r"\bopin(?:o|amos|a-se)\b|\be o parecer\b|\bs\.?m\.?j\b"
              r"|salvo melhor juizo|sub censura"),
    ("termos", r"\bnestes termos\b|\bnesses termos\b|\bpor tais razoes\b|\bassim sendo\b"),
    ("despacho", r"\bde acordo com o (?:bem lancado |r\.? )?parecer\b"
                 r"|\baprovo o parecer\b|\bacolho o parecer\b"),
    ("encaminha", r"\bem prosseguimento\b|\bencaminhe-se\b"
                  r"|\ba consideracao superior\b|\brestitua-se\b"),
]
RXG = [(k, re.compile(v, re.I)) for k, v in GRUPOS]


def conclusao_de(txt, limite=2000):
    """Devolve (texto da conclusao, tipo).

    Procura apenas na metade final do documento -- a mesma formula aparece no
    corpo quando o parecer transcreve outro -- e fica com a ULTIMA ocorrencia
    do grupo mais confiavel presente.
    """
    if len(txt) < 400:
        return "", ""
    ini = int(len(txt) * 0.5)
    alvo, base = norm(txt)[ini:], txt[ini:]
    for tipo, rx in RXG:
        ms = list(rx.finditer(alvo))
        if ms:
            p = ms[-1].start()
            return re.sub(r"\s+", " ", base[p:p + limite]).strip(), tipo
    return "", ""
