# -*- coding: utf-8 -*-
"""Extracao da conclusao do parecer, por formula de fecho.

Medido em amostra de 210 pareceres: o regex da primeira indexacao achava 37%;
este conjunto acha 91%. Os grupos estao em ordem de confianca -- uma formula
de conclusao propriamente dita vence um mero despacho de encaminhamento.

Uma armadilha custou caro: o parecer costuma trazer, DEPOIS da propria
conclusao, pecas de terceiro reproduzidas -- decisao do Tribunal de Contas,
manifestacao do Ministerio Publico de Contas, oficio de outro orgao. Como se
fica com a ULTIMA formula de fecho, a conclusao capturada passava a ser a do
terceiro. No Parecer FMF 75/2020 o campo trazia "Decido: I - Pela CONCESSAO DE
TUTELA PROVISORIA ... CONSELHEIRA ANDREA SIQUEIRA MARTINS", que e do TCE-RJ.
Dai o `parece_alheio`.
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

# Marcas de que o trecho e peca de OUTRO orgao, reproduzida dentro do parecer.
ALHEIO = re.compile(
    # Tribunal de Contas
    r"tce-?rj|ritcerj|tribunal de contas"
    r"|conselheir[ao]|ministerio publico de contas"
    r"|secretaria geral de controle externo"
    r"|tutela provisoria|www\.tcerj\.tc\.br"
    # Ministerio Publico e Defensoria: o parecer tambem reproduz peca deles
    r"|ministerio publico do estado|\bmprj\b|promotoria de justica"
    r"|promotoria de tutela coletiva|promotor[a]? de justica"
    r"|defensoria publica|procuradoria da republica|\bmpf\b"
    # verbos de decisao que a PGE nao usa em parecer
    r"|\bdecido\s*:|acordam os|vistos, relatados|\brequer\s+o\s+ministerio",
    re.I)
# Duas marcas distintas ja bastam; uma so pode ser mera citacao no corpo.
MINIMO_ALHEIO = 2


# Se a marca de terceiro aparece logo no inicio, a candidata E a peca dele.
# 500 era largo demais: alcancava a cauda e condenava a conclusao legitima.
CABECA = 200
# Abaixo disto nao se corta: sobraria fragmento sem sentido.
MINIMO_CORTE = 120


def parece_alheio(trecho):
    achados = set(m.group(0).lower() for m in ALHEIO.finditer(norm(trecho)))
    return len(achados) >= MINIMO_ALHEIO


def corta_cauda_alheia(trecho):
    """Corta a candidata onde comeca a peca de terceiro reproduzida depois.

    Sem isto, a conclusao legitima era descartada por engano: a fatia de 2.000
    caracteres a partir dela alcancava a decisao do Tribunal que vinha adiante,
    e a candidata inteira parecia alheia.
    """
    alvo = norm(trecho)
    for m in ALHEIO.finditer(alvo):
        if m.start() >= MINIMO_CORTE:
            return trecho[:m.start()].rstrip(" -–—|;,")
    return trecho


def conclusao_de(txt, limite=2000):
    """Devolve (texto da conclusao, tipo, alheio).

    Procura apenas na metade final do documento -- a mesma formula aparece no
    corpo quando o parecer transcreve outro -- e fica com a ULTIMA ocorrencia
    do grupo mais confiavel que NAO pareca peca de terceiro. Se todas as
    candidatas parecerem alheias, devolve a ultima e marca alheio=True, para
    que quem consome saiba desconfiar.
    """
    if len(txt) < 400:
        return "", "", False
    ini = int(len(txt) * 0.5)
    alvo, base = norm(txt)[ini:], txt[ini:]
    ultima = None
    for tipo, rx in RXG:
        for m in reversed(list(rx.finditer(alvo))):
            bruto = re.sub(r"\s+", " ", base[m.start():m.start() + limite]).strip()
            if ultima is None:
                ultima = (bruto, tipo)
            # a autoria se decide pelo INICIO do trecho, nao pela cauda
            if parece_alheio(bruto[:CABECA]):
                continue
            return corta_cauda_alheia(bruto).strip(), tipo, False
    if ultima:
        return ultima[0], ultima[1], True
    return "", "", False
