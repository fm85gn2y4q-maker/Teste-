# -*- coding: utf-8 -*-
"""Le os PDFs baixados da PGE-RJ, extrai o inteiro teor, enriquece com a
legislacao/precedentes/jurisprudencia citados e monta um banco SQLite com
busca em texto integral (FTS5)."""
import fitz, glob, json, os, re, sqlite3, sys, time, unicodedata, collections

BASE = r"C:\Users\Matheus Menegatti\Documents\PGE-RJ_Pareceres_Contratacoes"
PDFDIR = os.path.join(BASE, "PDFs")
AQUI = os.path.dirname(os.path.abspath(__file__))
SEL = os.path.join(AQUI, "selecionados.jsonl")
DB = os.path.join(BASE, "pge_rj_pareceres.db")

MESES = {"janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
         "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------- legislacao
NUM = r"(\d{1,3}(?:\.\d{3})*|\d{1,6})"
ANO = r"((?:19|20)\d{2})"
RX_NORMA = re.compile(
    r"\b(lei\s+complementar|lei\s+delegada|lei|decreto[-\s]?lei|decreto|"
    r"medida\s+provisoria|emenda\s+constitucional|resolucao|deliberacao|portaria|"
    r"instrucao\s+normativa)\s*"
    r"(?:(federal|estadual|municipal|conjunta)\s+)?"
    r"(?:n[ºo°\.\s]*)?\s*" + NUM +
    r"(?:\s*[,/]?\s*de\s+\d{1,2}\s+de\s+(\w+)\s+de\s+" + ANO + r"|\s*/\s*" + ANO + r")?",
    re.I)
RX_CF = re.compile(r"\b(constituicao\s+federal|crfb|cf/?88|carta\s+magna)\b", re.I)
RX_CERJ = re.compile(r"\b(cerj|constituicao\s+estadual)\b", re.I)
RX_SUMULA = re.compile(r"\bsumula\s+(vinculante\s+)?(?:n[ºo°\.\s]*)?\s*(\d{1,4})\s*"
                       r"(?:d[oe]\s+(stf|stj|tst|tcu|tce))?", re.I)
RX_ACORDAO = re.compile(r"\bacordao\s*(?:n[ºo°\.\s]*)?\s*" + NUM + r"\s*/\s*" + ANO +
                        r"(?:\s*[-–]?\s*(tcu|tce|plenario|primeira camara|segunda camara))?", re.I)
RX_PRECEDENTE = re.compile(
    r"\b(parecer(?:\s+conjunto|\s+normativo|\s+referencial)?|promocao|enunciado|"
    r"informacao\s+juridica)\s+([A-Z]{2,8}(?:/[A-Z]{2,8})*)?\s*"
    r"(?:n[ºo°\.\s]*)?\s*(\d{1,9})\s*/\s*" + ANO, re.I)
RX_TRIBUNAL = re.compile(r"\b(STF|STJ|TCU|TCE[-\s]?RJ|TJRJ|TJ/RJ|TRF|TST)\b")


def canon_norma(m):
    tipo = re.sub(r"\s+", " ", norm(m.group(1)).lower()).replace("-", " ")
    tipo = {"lei complementar": "Lei Complementar", "lei delegada": "Lei Delegada",
            "lei": "Lei", "decreto lei": "Decreto-Lei", "decreto": "Decreto",
            "medida provisoria": "Medida Provisoria",
            "emenda constitucional": "Emenda Constitucional", "resolucao": "Resolucao",
            "deliberacao": "Deliberacao", "portaria": "Portaria",
            "instrucao normativa": "Instrucao Normativa"}.get(tipo)
    if not tipo:
        return None
    # a esfera nao entra no rotulo: "Lei Estadual 5.498/2009" e "Lei 5.498/2009"
    # sao a mesma norma e precisam colapsar numa unica entrada
    numero = m.group(3).replace(".", "")
    if not numero or len(numero) > 6:
        return None
    ano = m.group(5) or m.group(6)
    if ano and not (1889 <= int(ano) <= 2030):
        ano = None
    rot = tipo + " " + ("{:,}".format(int(numero)).replace(",", "."))
    if ano:
        rot += "/" + ano
    return rot, tipo, numero, ano


def extrai_citacoes(txt):
    t = norm(txt)
    normas, sumulas, acordaos, precedentes, tribunais = (collections.Counter() for _ in range(5))
    for m in RX_NORMA.finditer(t):
        c = canon_norma(m)
        if c:
            normas[c[0]] += 1
    if RX_CF.search(t):
        normas["Constituicao Federal de 1988"] += len(RX_CF.findall(t))
    if RX_CERJ.search(t):
        normas["Constituicao do Estado do Rio de Janeiro de 1989"] += len(RX_CERJ.findall(t))
    for m in RX_SUMULA.finditer(t):
        corte = (m.group(3) or "").upper()
        sumulas["Sumula %s%s%s" % ("Vinculante " if m.group(1) else "", m.group(2),
                                   " " + corte if corte else "")] += 1
    for m in RX_ACORDAO.finditer(t):
        acordaos["Acordao %s/%s%s" % (m.group(1), m.group(2),
                                      " " + m.group(3).upper() if m.group(3) else "")] += 1
    for m in RX_PRECEDENTE.finditer(t):
        especie = re.sub(r"\s+", " ", m.group(1)).title()
        sigla = (m.group(2) or "").upper()
        precedentes["%s %s%s/%s" % (especie, sigla + " " if sigla else "", m.group(3), m.group(4))] += 1
    for m in RX_TRIBUNAL.finditer(txt):
        tribunais[m.group(1).upper().replace("TJ/RJ", "TJRJ").replace("TCE RJ", "TCE-RJ")] += 1
    return normas, sumulas, acordaos, precedentes, tribunais


# ---------------------------------------------------------------- conclusao
RX_CONCLUSAO = re.compile(
    r"(?:^|\n)\s*(?:iii?v?\.?\s*)?(conclus[aã]o|ante o exposto|isto posto|isso posto|"
    r"do exposto|em face do exposto|pelo exposto|diante do exposto)\b", re.I)


def pega_conclusao(txt, limite=1800):
    ms = list(RX_CONCLUSAO.finditer(txt))
    if not ms:
        return ""
    return re.sub(r"\s+", " ", txt[ms[-1].start():ms[-1].start() + limite]).strip()


# ---------------------------------------------------------------- banco
DDL = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS documentos (
  codigo INTEGER PRIMARY KEY, tipo TEXT, titulo TEXT, numero TEXT, data TEXT, ano INTEGER,
  procuradores TEXT, setores TEXT, orgao TEXT, processo TEXT, ementa TEXT, assuntos TEXT,
  eixos TEXT, criterio TEXT, precedentes_ficha TEXT, arquivo TEXT, paginas INTEGER,
  caracteres INTEGER, tem_texto INTEGER, conclusao TEXT, url_pdf TEXT, url_ficha TEXT);
CREATE TABLE IF NOT EXISTS citacoes (
  codigo INTEGER, especie TEXT, referencia TEXT, ocorrencias INTEGER);
CREATE INDEX IF NOT EXISTS ix_cit_ref ON citacoes(referencia);
CREATE INDEX IF NOT EXISTS ix_cit_cod ON citacoes(codigo);
CREATE INDEX IF NOT EXISTS ix_doc_ano ON documentos(ano);
CREATE VIRTUAL TABLE IF NOT EXISTS busca USING fts5(
  codigo UNINDEXED, titulo, ementa, assuntos, texto, tokenize="unicode61 remove_diacritics 2");
"""


def main():
    meta = {}
    for l in open(SEL, encoding="utf-8"):
        r = json.loads(l)
        meta[r["codigo"]] = r

    fs = sorted(glob.glob(os.path.join(PDFDIR, "**", "*.pdf"), recursive=True))
    print("pdfs: %d | fichas: %d" % (len(fs), len(meta)), flush=True)

    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.executescript(DDL)
    UP = "https://documentacao.pge.rj.gov.br/scripts/bnweb/bnmapi.exe?router=upload/%s"
    FICHA = "https://documentacao.pge.rj.gov.br/bnportal/pt-BR/detalhes/%s"

    t0, semtexto, feitos = time.time(), 0, 0
    for i, f in enumerate(fs, 1):
        cod = None
        m = re.match(r"(\d+)_", os.path.basename(f))
        if m:
            cod = int(m.group(1))
        r = meta.get(cod, {})
        try:
            d = fitz.open(f)
            txt = "\n".join(d[p].get_text() for p in range(d.page_count))
            paginas = d.page_count
            d.close()
        except Exception as e:
            print("ERRO %s: %s" % (f, e), flush=True)
            txt, paginas = "", 0
        chars = len(txt.strip())
        tem = 1 if chars > 200 * max(1, min(paginas, 3)) / 3 else 0
        if not tem:
            semtexto += 1

        ax = [a for a in (r.get("anexos") or []) if not a.get("fonte")]
        procs = [x.get("nome", "") for x in (r.get("membros") or []) if x.get("tipo_relacao") == 9]
        setores = sorted({x.get("nome_setor", "") for x in (r.get("membros") or []) if x.get("nome_setor")})
        orgaos = [x.get("nome", "") for x in (r.get("membros") or []) if x.get("tipo_relacao") == 10]
        assuntos = " | ".join(a.get("nome", "") for a in (r.get("assuntos") or []))

        con.execute("INSERT OR REPLACE INTO documentos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            cod, r.get("tipo_nome"), r.get("titulo"), r.get("numero"), r.get("datadoc"),
            r.get("anodoc"), " | ".join(procs), " | ".join(setores), " | ".join(orgaos),
            r.get("processo"), r.get("ementa"), assuntos, "; ".join(r.get("_eixos") or []),
            r.get("_motivo"), (r.get("precedentes") or "").replace("\n", " "),
            os.path.relpath(f, BASE), paginas, chars, tem, pega_conclusao(txt),
            UP % ax[0]["cod_anexo"] if ax else "", FICHA % cod if cod else ""))

        if chars > 100:
            normas, sums, acs, precs, tribs = extrai_citacoes(txt)
            linhas = []
            for esp, cont in (("norma", normas), ("sumula", sums), ("acordao", acs),
                              ("precedente", precs), ("tribunal", tribs)):
                for ref, n in cont.items():
                    linhas.append((cod, esp, ref, n))
            if linhas:
                con.executemany("INSERT INTO citacoes VALUES (?,?,?,?)", linhas)
        con.execute("INSERT INTO busca VALUES (?,?,?,?,?)",
                    (cod, r.get("titulo"), r.get("ementa"), assuntos, txt))
        feitos += 1
        if i % 400 == 0:
            con.commit()
            dec = time.time() - t0
            print("%d/%d  %.0f/min  sem texto=%d" % (i, len(fs), i / max(dec, 1) * 60, semtexto), flush=True)
    con.commit()

    # fichas sem PDF entram so com metadado
    codigos = {r[0] for r in con.execute("SELECT codigo FROM documentos")}
    faltam = [r for c, r in meta.items() if c not in codigos]
    for r in faltam:
        procs = [x.get("nome", "") for x in (r.get("membros") or []) if x.get("tipo_relacao") == 9]
        setores = sorted({x.get("nome_setor", "") for x in (r.get("membros") or []) if x.get("nome_setor")})
        orgaos = [x.get("nome", "") for x in (r.get("membros") or []) if x.get("tipo_relacao") == 10]
        assuntos = " | ".join(a.get("nome", "") for a in (r.get("assuntos") or []))
        con.execute("INSERT OR REPLACE INTO documentos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            r["codigo"], r.get("tipo_nome"), r.get("titulo"), r.get("numero"), r.get("datadoc"),
            r.get("anodoc"), " | ".join(procs), " | ".join(setores), " | ".join(orgaos),
            r.get("processo"), r.get("ementa"), assuntos, "; ".join(r.get("_eixos") or []),
            r.get("_motivo"), (r.get("precedentes") or "").replace("\n", " "), "", 0, 0, 0, "", "",
            FICHA % r["codigo"]))
        con.execute("INSERT INTO busca VALUES (?,?,?,?,?)",
                    (r["codigo"], r.get("titulo"), r.get("ementa"), assuntos, ""))
    con.commit()

    # --- consolida referencias sem ano ------------------------------------
    # "Lei 8.666" e "Lei 8.666/1993" sao a mesma norma; adota-se, para as
    # citacoes sem ano, o ano majoritario com que aquele numero aparece no acervo.
    modal = {}
    for tipo_num, ano, n in con.execute("""
            SELECT substr(referencia,1,instr(referencia,'/')-1),
                   substr(referencia,instr(referencia,'/')+1), SUM(ocorrencias)
            FROM citacoes WHERE especie='norma' AND instr(referencia,'/')>0
            GROUP BY 1,2"""):
        if tipo_num not in modal or n > modal[tipo_num][1]:
            modal[tipo_num] = (ano, n)
    corrigidas = 0
    for (ref,) in con.execute("""SELECT DISTINCT referencia FROM citacoes
                                 WHERE especie='norma' AND instr(referencia,'/')=0""").fetchall():
        if ref in modal:
            con.execute("UPDATE citacoes SET referencia=? WHERE especie='norma' AND referencia=?",
                        (ref + "/" + modal[ref][0], ref))
            corrigidas += 1
    con.execute("""DELETE FROM citacoes WHERE rowid NOT IN
                   (SELECT MIN(rowid) FROM citacoes GROUP BY codigo,especie,referencia)""")
    con.commit()
    print("referencias sem ano consolidadas: %d" % corrigidas, flush=True)

    con.execute("INSERT INTO busca(busca) VALUES('optimize')")
    con.commit()
    print("FIM: %d com PDF (%d sem camada de texto) + %d so ficha | %.0f min"
          % (feitos, semtexto, len(faltam), (time.time() - t0) / 60), flush=True)
    con.close()


if __name__ == "__main__":
    main()
