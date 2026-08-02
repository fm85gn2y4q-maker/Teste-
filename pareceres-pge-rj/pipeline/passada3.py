# -*- coding: utf-8 -*-
"""Terceira passada: fecha os tres buracos que faltavam para o acervo da PGE-RJ
poder virar ferramenta de consulta para uma IA.

  1. SINONIMOS   - a busca e literal; o vocabulario juridico nao e.
                   Tesauro medido no proprio acervo, para expandir consulta.
  2. PROVENIENCIA- dentro de um parecer ha relatorio, transcricao de terceiros
                   e opiniao da PGE. Atribuir a Corte um trecho transcrito
                   inverte o entendimento. Marca secao e grau de transcricao
                   PAGINA A PAGINA.
  3. VIGENCIA    - 87% do acervo e anterior a Lei 14.133/2021. Marca o regime
                   de cada parecer e emite alerta quando ele responde sob norma
                   revogada.

Le as paginas do indice numa varredura sequencial (rapido); nao rele PDFs.
"""
import collections
import os
import re
import sqlite3
import sys
import time
import unicodedata

from regime import regime_e_alerta  # unica fonte da verdade

BASE = r"C:\Users\Matheus Menegatti\Documents\PGE-RJ_Pareceres_Contratacoes"
DB = os.path.join(BASE, "pge_rj_pareceres.db")


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


# ---------------------------------------------------------------- 1. TESAURO
# conceito -> formas que o acervo efetivamente usa. Os numeros sao medidos.
TESAURO = {
    "reequilibrio economico-financeiro": [
        "reequilíbrio econômico-financeiro", "recomposição do equilíbrio",
        "revisão de preços", "reajustamento de preços", "revisão contratual",
        "equilíbrio econômico-financeiro", "álea extraordinária", "teoria da imprevisão"],
    "contratacao direta": [
        "contratação direta", "dispensa de licitação", "inexigibilidade de licitação",
        "licitação dispensável", "licitação inexigível", "dispensa de procedimento licitatório"],
    "termo de referencia": [
        "termo de referência", "projeto básico", "especificação do objeto", "anteprojeto"],
    "fase preparatoria": [
        "fase preparatória", "fase interna", "planejamento da contratação",
        "instrução do processo", "estudo técnico preliminar", "documento de formalização da demanda"],
    "adesao a ata": [
        "adesão à ata de registro de preços", "órgão não participante", "carona",
        "adesão tardia", "órgão participante"],
    "terceiro setor": [
        "organização social", "OSCIP", "organização da sociedade civil",
        "entidade sem fins lucrativos", "entidade filantrópica", "contrato de gestão",
        "termo de parceria"],
    "parceria MROSC": [
        "termo de colaboração", "termo de fomento", "acordo de cooperação",
        "chamamento público", "parceria com organização da sociedade civil"],
    "prorrogacao": [
        "prorrogação de prazo", "prorrogação de vigência", "prorrogação contratual",
        "aditamento de prazo", "prorrogação excepcional"],
    "alteracao contratual": [
        "alteração contratual", "termo aditivo", "acréscimo quantitativo",
        "supressão contratual", "alteração qualitativa", "aditamento"],
    "sancao": [
        "sanção administrativa", "penalidade contratual", "multa contratual",
        "impedimento de licitar", "declaração de inidoneidade", "suspensão temporária",
        "advertência"],
    "pesquisa de precos": [
        "pesquisa de preços", "orçamento estimado", "cotação de preços",
        "mapa comparativo", "preço de referência", "ampla pesquisa de mercado"],
    "habilitacao": [
        "habilitação jurídica", "qualificação técnica", "qualificação econômico-financeira",
        "regularidade fiscal", "documentos de habilitação", "atestado de capacidade técnica"],
    "concessao e PPP": [
        "concessão de serviço público", "permissão de serviço público",
        "parceria público-privada", "concessão patrocinada", "concessão administrativa",
        "delegação de serviço público"],
    "uso de bem publico": [
        "cessão de uso", "permissão de uso", "concessão de uso",
        "autorização de uso", "uso de bem público"],
    "convenio": [
        "convênio", "transferência voluntária", "repasse de recursos",
        "instrumento congênere", "plano de trabalho"],
    "extincao contratual": [
        "rescisão contratual", "extinção do contrato", "distrato", "rescisão unilateral",
        "rescisão amigável"],
    "fiscalizacao do contrato": [
        "fiscal do contrato", "gestor do contrato", "gestão do contrato",
        "fiscalização contratual", "recebimento provisório", "recebimento definitivo"],
    "registro de precos": [
        "sistema de registro de preços", "ata de registro de preços", "intenção de registro de preços"],
    "sobrepreco": ["sobrepreço", "superfaturamento", "preço inexequível", "jogo de planilha"],
    "parecer referencial": [
        "parecer referencial", "parecer normativo", "dispensa de análise individualizada",
        "manifestação referencial"],
    "garantia contratual": [
        "garantia contratual", "seguro-garantia", "caução", "fiança bancária"],
    "repactuacao": ["repactuação", "planilha de custos", "convenção coletiva", "custos de mão de obra"],
    "credenciamento": ["credenciamento", "inexigibilidade por credenciamento", "sistema de credenciamento"],
    "subcontratacao": ["subcontratação", "cessão contratual", "sub-rogação"],
    "modalidade": [
        "pregão eletrônico", "concorrência", "tomada de preços", "diálogo competitivo",
        "leilão", "convite", "concurso"],
}


# ------------------------------------------------------------ 2. PROVENIENCIA
# fim do relatorio: a partir daqui o parecerista fala por si
FIM_RELATORIO = re.compile(
    r"\be\s+o\s+(?:breve\s+|sucinto\s+)?relat[oó]rio\b|\bfeito\s+o\s+relat[oó]rio\b"
    r"|\bpasso\s+a\s+opinar\b|\bpassa-se\s+a\s+opinar\b|\bpasso\s+ao\s+exame\b"
    r"|\brelatados[,\.]|\bera\s+o\s+que\s+cumpria\s+relatar\b", re.I)
# marcadores explicitos de que o que vem a seguir e palavra de terceiro
VERBIS = re.compile(
    r"\bin\s+verbis\b|\bverbis\b|\bipsis\s+litteris\b|\btranscrev[oa]\b|\btranscri[cç][aã]o\b"
    r"|\bnas\s+palavras\s+de\b|\bsegundo\s+(?:o\s+)?(?:professor|autor|doutrinador)\b"
    r"|\bleciona\b|\bensina\b|\bpreleciona\b|\bassevera\b|\bcolaciona\b"
    r"|\bconforme\s+(?:se\s+)?(?:extrai|depreende)\b|\bementa:\s", re.I)
ASPAS = re.compile(r"[\u201c\u201d\"\u00ab\u00bb\u2018\u2019']")


def mede_transcricao(txt):
    """0 a 100: quanto da pagina parece ser palavra de terceiro, nao da PGE."""
    if not txt or len(txt) < 200:
        return 0
    t = txt
    # caracteres entre aspas (curvas, retas ou francesas)
    dentro, aberto, ini = 0, False, 0
    for i, c in enumerate(t):
        if ASPAS.match(c):
            if aberto:
                if i - ini < 4000:
                    dentro += i - ini
                aberto = False
            else:
                aberto, ini = True, i
    frac = 100.0 * dentro / len(t)
    # linhas recuadas em bloco tambem indicam transcricao
    linhas = t.split("\n")
    recuadas = sum(1 for l in linhas if l.startswith("        ") and len(l.strip()) > 30)
    if linhas:
        frac += 40.0 * recuadas / len(linhas)
    if VERBIS.search(norm(t)):
        frac += 30
    return int(min(100, round(frac)))


# ---------------------------------------------------------------- 3. VIGENCIA
def main():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")

    # ---------- 1. tesauro medido -------------------------------------------
    print("[1] tesauro: medindo cada variante no acervo", flush=True)
    con.execute("DROP TABLE IF EXISTS sinonimos")
    con.execute("""CREATE TABLE sinonimos (conceito TEXT, variante TEXT,
                   documentos INTEGER, paginas INTEGER)""")
    linhas = []
    for conceito, variantes in TESAURO.items():
        for v in variantes:
            try:
                d, p = con.execute(
                    "SELECT COUNT(DISTINCT codigo), COUNT(*) FROM paginas_fts WHERE paginas_fts MATCH ?",
                    ('"%s"' % v,)).fetchone()
            except sqlite3.OperationalError:
                d = p = 0
            linhas.append((conceito, v, d, p))
    con.executemany("INSERT INTO sinonimos VALUES (?,?,?,?)", linhas)
    con.execute("CREATE INDEX ix_sin_con ON sinonimos(conceito)")
    con.commit()
    print("    %d variantes em %d conceitos" % (len(linhas), len(TESAURO)), flush=True)

    # ---------- 2. proveniencia pagina a pagina ------------------------------
    print("\n[2] proveniencia: secao e grau de transcricao, pagina a pagina", flush=True)
    for col, tipo in (("secao", "TEXT"), ("transcricao", "INTEGER")):
        try:
            con.execute("ALTER TABLE paginas ADD COLUMN %s %s" % (col, tipo))
        except sqlite3.OperationalError:
            pass
    t0 = time.time()
    porcod = collections.defaultdict(list)
    for cod, pag, txt in con.execute("SELECT codigo,pagina,texto FROM paginas_fts ORDER BY codigo,pagina"):
        porcod[cod].append((pag, txt or ""))
    print("    %d documentos lidos em %.0fs" % (len(porcod), time.time() - t0), flush=True)

    ups, secoes = [], collections.Counter()
    conclusoes = dict(con.execute("SELECT codigo, conclusao FROM documentos"))
    for cod, pags in porcod.items():
        fim_rel = None
        for pag, txt in pags:
            if FIM_RELATORIO.search(norm(txt)):
                fim_rel = pag
                break
        conc = (conclusoes.get(cod) or "")[:60]
        ini_conc = None
        if conc:
            alvo = norm(conc)
            for pag, txt in pags:
                if alvo[:40] and alvo[:40] in norm(txt):
                    ini_conc = pag
        for pag, txt in pags:
            if ini_conc and pag >= ini_conc:
                sec = "conclusao"
            elif fim_rel and pag <= fim_rel:
                sec = "relatorio"
            elif fim_rel:
                sec = "fundamentacao"
            else:
                sec = "indefinida"
            secoes[sec] += 1
            ups.append((sec, mede_transcricao(txt), cod, pag))
    con.executemany("UPDATE paginas SET secao=?, transcricao=? WHERE codigo=? AND pagina=?", ups)
    con.commit()
    print("    paginas classificadas: %s" % dict(secoes), flush=True)

    # ---------- 3. vigencia e regime ----------------------------------------
    print("\n[3] vigencia: regime de cada parecer", flush=True)
    for col in ("regime", "alerta_vigencia"):
        try:
            con.execute("ALTER TABLE documentos ADD COLUMN %s TEXT" % col)
        except sqlite3.OperationalError:
            pass
    refs = collections.defaultdict(set)
    for cod, r in con.execute("SELECT codigo, referencia FROM citacoes WHERE especie='norma'"):
        refs[cod].add(r)
    ups, regs = [], collections.Counter()
    for cod, ano, eixos in con.execute("SELECT codigo, ano, eixos FROM documentos"):
        reg, al = regime_e_alerta(ano, refs.get(cod, set()), eixos or "")
        regs[reg] += 1
        ups.append((reg, al, cod))
    con.executemany("UPDATE documentos SET regime=?, alerta_vigencia=? WHERE codigo=?", ups)
    con.execute("CREATE INDEX IF NOT EXISTS ix_doc_reg ON documentos(regime)")
    con.commit()
    print("    %s" % dict(regs), flush=True)

    # ---------- cobertura declarada -----------------------------------------
    con.execute("DROP TABLE IF EXISTS cobertura")
    con.execute("CREATE TABLE cobertura (chave TEXT, valor TEXT)")
    g = lambda s: con.execute(s).fetchone()[0]
    dados = [
        ("fonte", "Acervo publico da Procuradoria-Geral do Estado do Rio de Janeiro (BNPortal)"),
        ("coletado_em", "2026-07-30"),
        ("documentos", str(g("SELECT COUNT(*) FROM documentos"))),
        ("com_inteiro_teor", str(g("SELECT COUNT(*) FROM documentos WHERE paginas>0"))),
        ("so_ficha_sem_pdf", str(g("SELECT COUNT(*) FROM documentos WHERE paginas=0"))),
        ("paginas", str(g("SELECT COUNT(*) FROM paginas"))),
        ("sem_camada_de_texto", str(g("SELECT COUNT(*) FROM documentos WHERE paginas>0 AND tem_texto=0"))),
        ("periodo", "%s a %s" % (g("SELECT MIN(ano) FROM documentos WHERE ano>1900"),
                                 g("SELECT MAX(ano) FROM documentos"))),
        ("anteriores_a_14133", str(g("SELECT COUNT(*) FROM documentos WHERE ano<2021"))),
        ("autoridade", "Parecer da PGE-RJ vincula a Administracao estadual fluminense nos termos "
                       "da legislacao propria. Para municipio e precedente PERSUASIVO, nao norma."),
        ("recorte", "Acervo INTEGRAL da PGE-RJ. O recorte tematico de contratacoes, acordos "
                    "e parcerias permanece marcado no campo no_recorte (14.420 documentos) e "
                    "pode ser usado como filtro em listar_documentos. Fora dele ha materia de "
                    "pessoal, tributaria, previdenciaria e constitucional."),
        ("limite_busca", "A busca e literal. Consulte a tabela sinonimos antes de concluir que "
                         "o acervo nao trata de um tema."),
    ]
    con.executemany("INSERT INTO cobertura VALUES (?,?)", dados)
    con.commit()
    print("\nFIM.", flush=True)
    con.close()


if __name__ == "__main__":
    main()
