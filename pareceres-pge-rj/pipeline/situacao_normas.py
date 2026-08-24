# -*- coding: utf-8 -*-
"""Etapa 11: o que o acervo diz que aconteceu com cada norma.

O campo `alerta_vigencia` so sabe de uma morte: a revogacao da lei geral de
licitacao. Nao sabe de declaracao de inconstitucionalidade, de suspensao de
eficacia, nem de alteracao posterior -- e foi por isso que a Lei Estadual
6.450/2013, derrubada pelo Orgao Especial do TJRJ com efeito erga omnes e ex
tunc, passou batida numa consulta real.

Aqui se constroi o analogo do `verificar_vigencia`: uma tabela do que os
proprios pareceres DECLARAM sobre o estado de uma norma.

O QUE ESTA TABELA NAO E: ela nao afirma que uma norma esta em vigor. Ela
registra o que documentos do acervo disseram ter acontecido. Ausencia aqui
significa que nenhum parecer selecionado tocou no assunto -- nao significa
norma saudavel.

A leitura e feita na EMENTA, e nao no inteiro teor, de proposito: a ementa e o
resumo oficial, curto, e quando ela anuncia uma mudanca de estado a norma
afetada esta ali do lado. No corpo do parecer, "inconstitucionalidade" aparece
em toda discussao doutrinaria, e a proximidade nao significa nada.
"""
import collections
import os
import re
import sqlite3
import unicodedata

from caminhos import DB


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


# Exige o ANUNCIO de uma mudanca de estado, nao a mera discussao do tema.
# "inconstitucionalidade" sozinho aparece em qualquer parecer que examine
# minuta de projeto de lei; nao serve.
# As ementas vêm do portal com espaços comidos -- "DECLARAÇÃO
# DEINCONSTITUCIONALIDADE", "LEI ESTADUAL Nº6.450/2013". Por isso o espaço é
# sempre `\s*` e nunca literal: exigindo espaço, o caso que motivou esta tabela
# nao era encontrado.
SITUACOES = [
    ("inconstitucionalidade",
     r"declarac\w*\s*de\s*inconstitucional|declarad\w*\s*inconstitucional"
     r"|inconstitucionalidade\s*declarada|julgad\w*\s*inconstitucional"
     r"|representacao\s*de\s*inconstitucionalidade|reconhecid\w*\s*a\s*inconstitucionalidade"
     r"|\bincidente\s*de\s*inconstitucionalidade"),
    ("revogacao",
     r"\brevogad\w*|\brevogacao\b|\brevoga\b|\bab-?rogad\w*"),
    ("suspensao",
     r"suspensao\s*(?:da\s*|de\s*)?eficacia|eficacia\s*suspensa"
     r"|suspens\w*\s*(?:a|os|as)\s*eficacia|medida\s*cautelar\s*deferida"),
    ("alteracao",
     r"alterad\w*\s*pel[ao]\b|alteracao\s*promovida\s*pel|nova\s*redacao\s*dada"),
]
RX = [(k, re.compile(v)) for k, v in SITUACOES]

# Distancia maxima, em caracteres, entre a marca de situacao e a norma a que
# ela se refere. Medido: 150 mantem os casos verdadeiros e corta o grosso dos
# falsos, em ementas longas que citam meia duzia de normas.
JANELA = 150

# Norma citada dentro da propria ementa.
NUM = r"(\d{1,3}(?:[.\s]\d{3})+|\d{1,6})"
RX_NORMA = re.compile(
    r"\b(lei complementar|lc|lei|decreto[-\s]?lei|decreto|medida provisoria|"
    r"emenda constitucional|resolucao|deliberacao|portaria|instrucao normativa)\s*"
    r"(?:(?:federal|estadual|municipal)\s+)?(?:n[ºo°ª.\s]{0,3})?\s*" + NUM +
    r"(?:\s*[,/]?\s*de\s+\d{1,2}\s+de\s+\w+\s+de\s+((?:19|20)\d{2})"
    r"|\s*/\s*(?:19|20)?(\d{2,4}))?")
TIPOS = {"lei complementar": "Lei Complementar", "lc": "Lei Complementar", "lei": "Lei",
         "decreto lei": "Decreto-Lei", "decreto": "Decreto",
         "medida provisoria": "Medida Provisoria",
         "emenda constitucional": "Emenda Constitucional", "resolucao": "Resolucao",
         "deliberacao": "Deliberacao", "portaria": "Portaria",
         "instrucao normativa": "Instrucao Normativa"}


def normas_da_ementa(ementa):
    achadas = []
    for m in RX_NORMA.finditer(norm(ementa)):
        tipo = TIPOS.get(re.sub(r"\s+", " ", m.group(1)).replace("-", " "))
        if not tipo:
            continue
        numero = re.sub(r"[.\s]", "", m.group(2))
        if not numero or len(numero) > 6 or int(numero) == 0:
            continue
        ano = m.group(3) or m.group(4)
        if ano and len(ano) == 2:
            ano = ("19" if int(ano) > 30 else "20") + ano
        if ano and not (1889 <= int(ano) <= 2030):
            ano = None
        if not ano and len(numero.lstrip("0")) < 3:
            continue
        rot = tipo + " " + "{:,}".format(int(numero)).replace(",", ".")
        achadas.append(rot + "/" + ano if ano else rot)
    return sorted(set(achadas))


DDL = """
DROP TABLE IF EXISTS situacao_normas;
CREATE TABLE situacao_normas (
  norma TEXT, situacao TEXT, codigo INTEGER, ano INTEGER, citacao TEXT, trecho TEXT);
CREATE INDEX ix_sit_norma ON situacao_normas(norma);
"""


def main():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(DDL)

    linhas, contagem, sem_norma = [], collections.Counter(), 0
    for cod, ano, titulo, ementa in con.execute(
            """SELECT codigo, ano, titulo, ementa FROM documentos
               WHERE COALESCE(ementa,'') <> ''"""):
        e = norm(ementa)
        for situacao, rx in RX:
            m = rx.search(e)
            if not m:
                continue
            # Só as normas PERTO da marca. Sem isto, uma ementa que cita cinco
            # normas e diz que UMA foi revogada carimbava as cinco -- e o
            # apontamento falso é pior que apontamento nenhum, porque parece
            # conferência feita.
            ini, fim = max(0, m.start() - JANELA), m.end() + JANELA
            normas = normas_da_ementa(ementa[ini:fim])
            if not normas:
                sem_norma += 1
                continue
            trecho = re.sub(r"\s+", " ", ementa[max(0, m.start() - 120):m.start() + 200]).strip()
            for n in normas:
                linhas.append((n, situacao, cod, ano, titulo, trecho))
                contagem[situacao] += 1
    con.executemany("INSERT INTO situacao_normas VALUES (?,?,?,?,?,?)", linhas)
    con.commit()

    print("registros: %d | ementas com marca mas sem norma identificada: %d"
          % (len(linhas), sem_norma))
    print("por situacao:", contagem.most_common())
    print("\nnormas com mais apontamentos:")
    for n, s, q in con.execute(
            """SELECT norma, situacao, COUNT(*) FROM situacao_normas
               GROUP BY norma, situacao ORDER BY 3 DESC LIMIT 12"""):
        print("  %-34s %-22s %d" % (n, s, q))
    print("\nLei 6.450/2013:")
    for r in con.execute(
            """SELECT ano, citacao, situacao, substr(trecho,1,90) FROM situacao_normas
               WHERE norma='Lei 6.450/2013' ORDER BY ano DESC"""):
        print("  [%s] %-30s %-24s %s" % r)
    con.close()


if __name__ == "__main__":
    main()
