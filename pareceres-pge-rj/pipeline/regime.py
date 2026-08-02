# -*- coding: utf-8 -*-
"""Regime de vigencia de cada parecer.

A primeira versao olhava so as leis de licitacao, e por isso rotulava como
"Lei 8.666/1993" todo parecer de organizacao social -- que se rege pela Lei
9.637/98 e pelas leis estaduais proprias, citando a 8.666 apenas de passagem.
O alerta nao era falso, mas era enganoso quanto ao que de fato governa o tema.

Agora a materia de terceiro setor e reconhecida ANTES da de licitacao.
"""

# Leis proprias do terceiro setor, na ordem em que devem prevalecer
TERCEIRO_SETOR = [
    ("Lei 13.019/2014", "Lei 13.019/2014 (MROSC)"),
    ("Lei 9.637/1998", "Lei 9.637/1998 (organizacao social)"),
    ("Lei 9.790/1999", "Lei 9.790/1999 (OSCIP)"),
]
LICITACAO = ("Lei 8.666/1993", "Lei 10.520/2002", "Lei 12.462/2011")


def regime_e_alerta(ano, refs, eixos=""):
    """(regime, alerta). `refs` sao as normas citadas; `eixos`, a classificacao
    tematica do documento."""
    tem = lambda p: any(r.startswith(p) for r in refs)
    tem133 = tem("Lei 14.133")
    tem_lic = any(tem(p) for p in LICITACAO)
    eixos = eixos or ""

    # --- terceiro setor vem primeiro: e lei propria, nao lei de licitacao ---
    for prefixo, rotulo in TERCEIRO_SETOR:
        if tem(prefixo):
            al = ("Materia de terceiro setor, regida por lei propria. A citacao da "
                  "legislacao de licitacao e lateral: nao trate este parecer como "
                  "superado apenas por ser anterior a Lei 14.133/2021.")
            if tem("Lei 13.019"):
                al += (" A Lei 13.019/2014 esta em vigor; confira alteracoes "
                       "posteriores e a regulamentacao municipal aplicavel.")
            return rotulo, al
    if "Terceiro setor" in eixos:
        return ("Terceiro setor (lei estadual/municipal propria)",
                "Materia de terceiro setor. As leis estaduais 5.498/2009 e 6.043/2011 "
                "nao alcancam municipio: confira a lei local antes de transpor a tese.")

    # --- demais: regime de licitacao -----------------------------------------
    if tem133 and tem_lic:
        return ("transicao 8.666/14.133",
                "Cita os dois regimes; verifique a qual deles a conclusao se refere.")
    if tem133:
        return "Lei 14.133/2021", ""
    if tem_lic:
        al = ("Responde sob a Lei 8.666/93, revogada pela Lei 14.133/2021 desde "
              "30/12/2023. Confira se a tese sobrevive ao novo regime antes de usar.")
        return "Lei 8.666/1993", al
    if tem("Lei 8.987") or tem("Lei 11.079"):
        return ("Concessao/PPP (Lei 8.987/1995 · Lei 11.079/2004)",
                "Regido por lei propria de concessoes, nao pela lei geral de licitacao.")
    if tem("Lei 13.303"):
        return "Lei 13.303/2016 (estatais)", ""
    al = "Parecer anterior a Lei 14.133/2021." if (ano and ano < 2021) else ""
    return "outro/nao identificado", al
