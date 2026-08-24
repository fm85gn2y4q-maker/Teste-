# -*- coding: utf-8 -*-
"""Corrige os tres defeitos da indexacao:
  1. numeros truncados e ruido de OCR na extracao de normas
  2. variantes duplicadas de sumula/acordao/precedente
  3. os 10 documentos cujo segundo anexo foi sobrescrito
Reaproveita o texto ja guardado no banco - nao rele os PDFs, salvo os 10.
"""
import collections, glob, os, re, sqlite3, sys, time, unicodedata

from caminhos import BASE, DB


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def rx(p):
    return re.compile(p, re.I)


# --- numero: milhar com ponto OU com espaco (OCR) OU corrido -----------------
# o defeito antigo era "(\d{1,3}(?:\.\d{3})*|\d{1,6})": a 1a alternativa casava
# "866" dentro de "8666" e a 2a nunca era tentada. Agora a 1a exige o grupo.
NUM = r"(\d{1,3}(?:[.\s]\d{3})+|\d{1,6})"
ANO = r"((?:19|20)\d{2})"
# "n", "nº", "n.", "nO", "nQ", "ng", "n2", "nnQ" - variantes de OCR de "nº".
# O digito so e absorvido se vier colado ao "n" E seguido de espaco ("n2 362"),
# senao a classe comeria o primeiro algarismo do numero da norma.
NO = r"(?:n[ºo°ªnNgGqQ.]{0,3}(?:\d(?=\s))?[\s.]*)?"

RX_NORMA = re.compile(
    r"\b(lei\s+complementar|lc|lei\s+delegada|lei|decreto[-\s]?lei|decreto|"
    r"medida\s+provisoria|emenda\s+constitucional|resolucao|deliberacao|portaria|"
    r"instrucao\s+normativa)\s*"
    r"(?:(federal|estadual|municipal|conjunta)\s+)?" + NO + r"\s*" + NUM +
    r"(?:\s*[,/]?\s*de\s+\d{1,2}\s+de\s+(\w+)\s+de\s+" + ANO + r"|\s*/\s*(?:19|20)?" + r"(\d{2,4})" + r")?",
    re.I)
RX_CF = rx(r"\b(constituicao\s+federal|crfb|cf/?88|carta\s+magna)\b")
RX_CERJ = rx(r"\b(cerj|constituicao\s+estadual)\b")
RX_SUMULA = rx(r"\bsumula\s+(vinculante\s+)?" + NO + r"\s*(\d{1,4})\s*"
               r"(?:d[oe]\s+(stf|stj|tst|tcu|tce))?")
RX_ACORDAO = rx(r"\bacordao\s*" + NO + r"\s*" + NUM + r"\s*/\s*" + ANO +
                r"(?:\s*[-\u2013]?\s*(tcu|tce|plenario|primeira camara|segunda camara))?")
RX_PRECEDENTE = rx(r"\b(parecer(?:\s+conjunto|\s+normativo|\s+referencial)?|promocao|enunciado|"
                   r"informacao\s+juridica)\s+([A-Z]{2,8}(?:/[A-Z]{2,8})*)?\s*" + NO +
                   r"\s*(\d{1,9})\s*/\s*" + ANO)
RX_TRIBUNAL = re.compile(r"\b(STF|STJ|TCU|TCE[-\s]?RJ|TJRJ|TJ/RJ|TRF|TST)\b")

TIPOS = {"lei complementar": "Lei Complementar", "lc": "Lei Complementar", "lei delegada": "Lei Delegada", "lei": "Lei",
         "decreto lei": "Decreto-Lei", "decreto": "Decreto", "medida provisoria": "Medida Provisoria",
         "emenda constitucional": "Emenda Constitucional", "resolucao": "Resolucao",
         "deliberacao": "Deliberacao", "portaria": "Portaria", "instrucao normativa": "Instrucao Normativa"}
# "Nº" que vazava para o campo da sigla do precedente
SIGLA_FALSA = {"NO", "N", "No", "NUM", "N0"}


def limpa_num(s):
    return re.sub(r"[.\s]", "", s or "")


def canon_norma(m):
    tipo = TIPOS.get(re.sub(r"\s+", " ", norm(m.group(1)).lower()).replace("-", " "))
    if not tipo:
        return None
    numero = limpa_num(m.group(3))
    if not numero or len(numero) > 6:
        return None
    ano = m.group(5) or m.group(6)
    if ano and len(ano) == 2:                       # "/93" -> 1993
        ano = ("19" if int(ano) > 30 else "20") + ano
    if ano and not (1889 <= int(ano) <= 2030):
        ano = None
    # numero curto sem ano e ruido de OCR ("Lei 8", "Decreto 2") - descarta
    if not ano and len(numero.lstrip("0")) < 3:
        return None
    if int(numero) == 0:
        return None
    rot = tipo + " " + "{:,}".format(int(numero)).replace(",", ".")
    return (rot + "/" + ano if ano else rot), None


def extrai(txt):
    """Devolve lista de (especie, referencia, qualificador, ocorrencias)."""
    t = norm(txt)
    c = collections.Counter()
    for m in RX_NORMA.finditer(t):
        r = canon_norma(m)
        if r:
            c[("norma", r[0], "")] += 1
    n = len(RX_CF.findall(t))
    if n:
        c[("norma", "Constituicao Federal de 1988", "")] += n
    n = len(RX_CERJ.findall(t))
    if n:
        c[("norma", "Constituicao do Estado do Rio de Janeiro de 1989", "")] += n
    for m in RX_SUMULA.finditer(t):
        # a corte vira qualificador: "Sumula 247" e "Sumula 247 TCU" deixam de ser duas
        c[("sumula", "Sumula %s%s" % ("Vinculante " if m.group(1) else "", m.group(2)),
           (m.group(3) or "").upper())] += 1
    for m in RX_ACORDAO.finditer(t):
        c[("acordao", "Acordao %s/%s" % (limpa_num(m.group(1)), m.group(2)),
           (m.group(3) or "").upper())] += 1
    for m in RX_PRECEDENTE.finditer(t):
        sigla = (m.group(2) or "").upper()
        if sigla in SIGLA_FALSA:
            sigla = ""
        especie = re.sub(r"\s+", " ", m.group(1)).title()
        c[("precedente", "%s %s/%s" % (especie, int(m.group(3)), m.group(4)), sigla)] += 1
    for m in RX_TRIBUNAL.finditer(txt):
        c[("tribunal", m.group(1).upper().replace("TJ/RJ", "TJRJ").replace("TCE RJ", "TCE-RJ"), "")] += 1
    return [(e, r, q, n) for (e, r, q), n in c.items()]


def main():
    con = sqlite3.connect(DB)
    antes = con.execute("SELECT COUNT(*) FROM citacoes").fetchone()[0]

    # ---------- defeito 3: anexos sobrescritos --------------------------------
    print("[3] anexos perdidos por colisao de codigo", flush=True)
    porcod = collections.defaultdict(list)
    for f in glob.glob(os.path.join(BASE, "PDFs", "**", "*.pdf"), recursive=True):
        m = re.match(r"(\d+)_", os.path.basename(f))
        if m:
            porcod[int(m.group(1))].append(f)
    dups = {k: sorted(v) for k, v in porcod.items() if len(v) > 1}
    print("    codigos com mais de um anexo: %d" % len(dups), flush=True)
    import fitz
    for cod, fs in dups.items():
        textos, pags = [], 0
        for f in fs:
            d = fitz.open(f)
            textos.append("\n".join(d[p].get_text() for p in range(d.page_count)))
            pags += d.page_count
            d.close()
        txt = "\n\n".join(textos)
        con.execute("UPDATE documentos SET arquivo=?, paginas=?, caracteres=? WHERE codigo=?",
                    (" | ".join(os.path.relpath(f, BASE) for f in fs), pags, len(txt.strip()), cod))
        row = con.execute("SELECT titulo, ementa, assuntos FROM documentos WHERE codigo=?", (cod,)).fetchone()
        con.execute("DELETE FROM busca WHERE codigo=?", (cod,))
        con.execute("INSERT INTO busca VALUES (?,?,?,?,?)", (cod, row[0], row[1], row[2], txt))
    con.commit()
    print("    %d documentos reindexados com todos os anexos" % len(dups), flush=True)

    # ---------- defeitos 1 e 2: reextrair citacoes do texto guardado ----------
    print("\n[1+2] reextraindo citacoes do texto ja guardado", flush=True)
    con.execute("DROP TABLE IF EXISTS citacoes")
    con.execute("""CREATE TABLE citacoes (codigo INTEGER, especie TEXT, referencia TEXT,
                   qualificador TEXT, ocorrencias INTEGER)""")
    t0, n = time.time(), 0
    cods = [r[0] for r in con.execute("SELECT codigo FROM documentos WHERE caracteres>100")]
    for cod in cods:
        row = con.execute("SELECT texto FROM busca WHERE codigo=?", (cod,)).fetchone()
        if not row or not row[0]:
            continue
        linhas = [(cod, e, r, q, o) for e, r, q, o in extrai(row[0])]
        if linhas:
            con.executemany("INSERT INTO citacoes VALUES (?,?,?,?,?)", linhas)
        n += 1
        if n % 1000 == 0:
            con.commit()
            print("    %d/%d  %.0f/min" % (n, len(cods), n / max(time.time() - t0, 1) * 60), flush=True)
    con.commit()

    # ---------- consolida referencias sem ano --------------------------------
    modal = {}
    for tn, ano, s in con.execute("""SELECT substr(referencia,1,instr(referencia,'/')-1),
             substr(referencia,instr(referencia,'/')+1), SUM(ocorrencias) FROM citacoes
             WHERE especie='norma' AND instr(referencia,'/')>0 GROUP BY 1,2"""):
        if tn not in modal or s > modal[tn][1]:
            modal[tn] = (ano, s)
    corr = 0
    for (ref,) in con.execute("""SELECT DISTINCT referencia FROM citacoes WHERE especie='norma'
                                 AND instr(referencia,'/')=0 AND referencia NOT LIKE 'Constituicao%'""").fetchall():
        if ref in modal:
            con.execute("UPDATE citacoes SET referencia=? WHERE especie='norma' AND referencia=?",
                        (ref + "/" + modal[ref][0], ref))
            corr += 1
    con.execute("""DELETE FROM citacoes WHERE rowid NOT IN
                   (SELECT MIN(rowid) FROM citacoes GROUP BY codigo,especie,referencia,qualificador)""")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cit_ref ON citacoes(referencia)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cit_cod ON citacoes(codigo)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_cit_esp ON citacoes(especie)")
    con.commit()
    depois = con.execute("SELECT COUNT(*) FROM citacoes").fetchone()[0]
    print("\n    sem ano consolidadas: %d | citacoes: %d -> %d | %.0f min"
          % (corr, antes, depois, (time.time() - t0) / 60), flush=True)
    con.execute("INSERT INTO busca(busca) VALUES('optimize')")
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
