"""Etapa 3 — monta o banco a partir do que foi colhido e baixado.

Reconstrói tudo o que toca: rodar de novo é seguro, e é a forma de aplicar uma
correção. Não é incremental.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import autoridade  # noqa: E402
import referencias  # noqa: E402

AQUI = Path(__file__).resolve().parent
ACERVO = Path.home() / "Documents" / "AGU_Acervo_Consultivo"
PDFS = ACERVO / "pdfs"
OCR = ACERVO / "ocr"
BANCO = ACERVO / "agu_consultivo.db"

# ---------------------------------------------------------------- proveniência

# Cabeçalhos que marcam a virada de seção nos pareceres da AGU. O documento do
# Sapiens é numerado e usa caixa alta; o marcador é o que separa o que o órgão
# consulente afirmou daquilo que a AGU concluiu.
_MARCA_RELATORIO = re.compile(
    r"(?im)^\s*(?:[IVX]+\s*[-–.)]\s*)?(RELAT[ÓO]RIO|DOS?\s+FATOS|"
    r"DA\s+CONSULTA|I\s*[-–]\s*RELAT[ÓO]RIO)\s*$")
_MARCA_FUNDAMENTO = re.compile(
    r"(?im)^\s*(?:[IVX]+\s*[-–.)]\s*)?(FUNDAMENTA[ÇC][ÃA]O|AN[ÁA]LISE|M[ÉE]RITO|"
    r"DO\s+M[ÉE]RITO|DA\s+AN[ÁA]LISE|RAZ[ÕO]ES)\s*$")
_MARCA_CONCLUSAO = re.compile(
    r"(?im)^\s*(?:[IVX]+\s*[-–.)]\s*)?(CONCLUS[ÃA]O|DA\s+CONCLUS[ÃA]O|"
    r"CONCLUS[ÕO]ES)\s*$")
# Fórmula que fecha o relatório mesmo sem cabeçalho.
_FIM_RELATORIO = re.compile(
    r"(?i)(é\s+o\s+relat[óo]rio|passo\s+a\s+opinar|era\s+o\s+que\s+cumpria)")

_ASPAS = re.compile(r"[«»“”\"]")


def _transcricao(texto: str) -> int:
    """0 a 100: quanto da página é palavra de terceiro, aproximadamente.

    Conta o que está entre aspas e os blocos recuados de citação. É estimativa,
    e serve para um único fim: avisar antes de atribuir à AGU um trecho que ela
    apenas transcreveu.
    """
    if not texto:
        return 0
    marcas = _ASPAS.findall(texto)
    dentro = 0
    aberto = False
    inicio = 0
    for m in _ASPAS.finditer(texto):
        if not aberto:
            aberto, inicio = True, m.end()
        else:
            dentro += m.start() - inicio
            aberto = False
    # linhas de citação recuada: começam com espaços e terminam sem pontuação
    # de fecho, padrão do parecer que transcreve doutrina em bloco
    recuadas = sum(len(l) for l in texto.split("\n")
                   if l.startswith(("    ", "\t")) and len(l.strip()) > 40)
    total = max(len(texto), 1)
    return min(100, round(100 * (dentro + recuadas) / total)) if marcas or recuadas else 0


def _secoes(paginas: list[str]) -> list[str]:
    """Rotula cada página com a seção em que ela cai."""
    estado = "indefinida"
    saida = []
    for texto in paginas:
        # a virada vale a partir da página em que o cabeçalho aparece
        if _MARCA_RELATORIO.search(texto):
            estado = "relatorio"
        if _MARCA_FUNDAMENTO.search(texto) or (
                estado == "relatorio" and _FIM_RELATORIO.search(texto)):
            estado = "fundamentacao"
        if _MARCA_CONCLUSAO.search(texto):
            estado = "conclusao"
        saida.append(estado)
    return saida


# -------------------------------------------------------------------- regime

_REGIMES = (
    ("Lei 14.133/2021", re.compile(r"(?i)\b14\.?133\b")),
    ("Lei 8.666/1993", re.compile(r"(?i)\b8\.?666\b")),
    ("Lei 13.019/2014 (parcerias)", re.compile(r"(?i)\b13\.?019\b")),
    ("Lei 8.112/1990 (servidor)", re.compile(r"(?i)\b8\.?112\b")),
)

ALERTA_8666 = (
    "Documento fundado na Lei 8.666/1993, revogada em 30/12/2023 pela Lei "
    "14.133/2021. A tese pode continuar correta e o fundamento legal, não.")


def _regime(texto: str) -> tuple[str | None, str | None]:
    achados = [rotulo for rotulo, padrao in _REGIMES if padrao.search(texto)]
    if not achados:
        return None, None
    rotulo = "; ".join(achados)
    alerta = ALERTA_8666 if any("8.666" in a for a in achados) and not any(
        "14.133" in a for a in achados) else None
    return rotulo, alerta


# ------------------------------------------------------------------- leitura

def _ler_pdf(caminho: Path) -> list[str]:
    import fitz
    try:
        with fitz.open(caminho) as doc:
            return [p.get_text() or "" for p in doc]
    except Exception:
        return []


_TOKEN = re.compile(r"[A-Za-zÀ-ÿ]{4,}")


def _vocabulario(textos: list[str]) -> set[str]:
    """As palavras que o próprio acervo usa, colhidas do texto nativo.

    Serve de régua para o OCR: não há como saber se "pretoóriana" está certo
    sem uma referência, e a melhor referência disponível é o vocabulário dos
    documentos que vieram com camada de texto.
    """
    vocab: set[str] = set()
    for t in textos:
        vocab.update(p.lower() for p in _TOKEN.findall(t))
    return vocab


def _confianca_ocr(texto: str, vocab: set[str]) -> int:
    """0 a 100: quanto do reconhecido é palavra que o acervo conhece.

    Não é acurácia — é o sinal mais honesto que dá para produzir sem gabarito.
    Página de prosa da AGU pontua alto; bloco transcrito em fonte degradada,
    baixo, e é exatamente ali que o OCR falha.
    """
    palavras = [p.lower() for p in _TOKEN.findall(texto)]
    if len(palavras) < 20:
        return 0
    return round(100 * sum(1 for p in palavras if p in vocab) / len(palavras))


def _ler_ocr(ident: int) -> list[str]:
    caminho = OCR / f"{ident}.json"
    if not caminho.exists():
        return []
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _jsonl(nome: str) -> list[dict]:
    caminho = AQUI / nome
    if not caminho.exists():
        return []
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines()]


# ------------------------------------------------------------------- esquema

ESQUEMA = """
DROP TABLE IF EXISTS documentos;
DROP TABLE IF EXISTS paginas;
DROP TABLE IF EXISTS paginas_fts;
DROP TABLE IF EXISTS busca;
DROP TABLE IF EXISTS citacoes;
DROP TABLE IF EXISTS sinonimos;
DROP TABLE IF EXISTS cobertura;

CREATE TABLE documentos (
  codigo INTEGER PRIMARY KEY,
  fonte TEXT, especie TEXT, citacao TEXT,
  numero INTEGER, ano INTEGER, orgao TEXT, grupo TEXT,
  assunto TEXT, ementa TEXT, texto TEXT,
  vinculacao TEXT, vinculacao_chave TEXT, vinculacao_ordem INTEGER,
  vinculacao_explicacao TEXT,
  vigencia_declarada TEXT, situacao_declarada TEXT,
  ato_revogador TEXT, ato_reanalise TEXT, relacionadas TEXT,
  aprovacao TEXT, despachos TEXT,
  regime TEXT, alerta_vigencia TEXT,
  paginas INTEGER DEFAULT 0, tem_texto INTEGER DEFAULT 0,
  origem_texto TEXT, ocr_confianca INTEGER, aviso_fonte TEXT,
  url_inteiro_teor TEXT, url_publicacao TEXT
);
CREATE TABLE paginas (
  codigo INTEGER, pagina INTEGER, caracteres INTEGER,
  secao TEXT, transcricao INTEGER,
  PRIMARY KEY (codigo, pagina)
);
CREATE VIRTUAL TABLE paginas_fts USING fts5(codigo UNINDEXED, pagina UNINDEXED, texto);
CREATE VIRTUAL TABLE busca USING fts5(codigo UNINDEXED, citacao, assunto, ementa, texto);
CREATE TABLE citacoes (
  codigo INTEGER, especie TEXT, referencia TEXT, ocorrencias INTEGER
);
CREATE INDEX ix_cit_ref ON citacoes(referencia);
CREATE TABLE sinonimos (conceito TEXT, variante TEXT, documentos INTEGER);
CREATE TABLE cobertura (chave TEXT PRIMARY KEY, valor TEXT);
CREATE INDEX ix_doc_ano ON documentos(ano);
CREATE INDEX ix_doc_vinc ON documentos(vinculacao_chave);
CREATE INDEX ix_doc_fonte ON documentos(fonte);
"""

# Tesauro: conceitos e as formas em que aparecem. As contagens são medidas
# depois, no próprio acervo — variante sem ocorrência é ruído e não entra.
CONCEITOS = {
    "equilíbrio econômico-financeiro": [
        "equilíbrio econômico-financeiro", "reequilíbrio econômico-financeiro",
        "reajuste", "repactuação", "revisão contratual", "teoria da imprevisão"],
    "contratação direta": [
        "dispensa de licitação", "inexigibilidade", "contratação direta",
        "notória especialização"],
    "terceiro setor": [
        "organização social", "OSCIP", "termo de colaboração", "termo de fomento",
        "termo de parceria", "Lei 13.019", "MROSC"],
    "convênio": ["convênio", "instrumento congênere", "termo de execução descentralizada",
                 "acordo de cooperação"],
    "prorrogação contratual": [
        "prorrogação", "serviço contínuo", "vigência do contrato", "aditamento"],
    "sanção administrativa": [
        "impedimento de licitar", "declaração de inidoneidade", "multa contratual",
        "sanção administrativa", "desconsideração da personalidade jurídica"],
    "pregão": ["pregão", "sistema de registro de preços", "ata de registro de preços",
               "carona", "adesão à ata"],
    "projeto e obra": [
        "projeto básico", "termo de referência", "anteprojeto", "estudo técnico preliminar",
        "matriz de riscos", "contratação integrada"],
    "terceirização": ["terceirização", "cessão de mão de obra", "conta vinculada",
                      "responsabilidade subsidiária"],
    "bem público": ["cessão de uso", "permissão de uso", "concessão de uso",
                    "alienação de imóvel", "enfiteuse"],
    "prescrição": ["prescrição", "decadência", "ressarcimento ao erário",
                   "tomada de contas especial"],
    "servidor": ["readaptação", "acumulação de cargos", "estágio probatório",
                 "cessão de servidor", "adicional de insalubridade"],
}


def main() -> None:
    ACERVO.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(BANCO)
    con.executescript(ESQUEMA)

    codigo = 0
    docs: list[tuple] = []
    pag_meta: list[tuple] = []
    pag_texto: list[tuple] = []
    cits: list[tuple] = []
    busca: list[tuple] = []
    sem_arquivo = 0
    sem_camada = 0
    reconhecidos = 0

    conuni = _jsonl("conuni.jsonl")
    # Os .jsonl ficam fora do Git e ao lado destes scripts. Sumindo eles, o
    # indexador rodava até o fim e anunciava sucesso com zero documentos --
    # e como ele apaga o banco antes de reconstruir, o acervo bom ia junto.
    # Aconteceu. Falhar cedo custa uma linha; o silêncio custou uma recoleta.
    if not conuni:
        raise SystemExit(
            f"conuni.jsonl vazio ou ausente em {AQUI}.\n"
            f"Rode `python coletar.py` antes de indexar — sem ele o banco sairia "
            f"vazio, e o anterior já teria sido apagado.")

    # Só agora, com a matéria-prima conferida, o banco antigo pode ir.
    if BANCO.exists():
        BANCO.unlink()

    # Primeiro passe: lê o texto nativo dos PDFs e monta o vocabulário do
    # acervo. Ele é a régua do OCR, e por isso precisa existir ANTES de
    # avaliar qualquer página reconhecida.
    nativo: dict[int, list[str]] = {}
    for r in conuni:
        pdf = PDFS / f"{r['id']}.pdf"
        if pdf.exists():
            paginas = _ler_pdf(pdf)
            if len("".join(paginas).strip()) > 200:
                nativo[r["id"]] = paginas
    vocab = _vocabulario(
        ["\n".join(p) for p in nativo.values()]
        + [r.get("ementa") or "" for r in conuni]
        + [r.get("texto") or "" for r in _jsonl("ons.jsonl") + _jsonl("sumulas.jsonl")])
    print(f"vocabulário do acervo: {len(vocab)} palavras, de {len(nativo)} "
          f"documentos com texto nativo")

    # ------------------------------------------------------------- CONUNI
    for r in conuni:
        codigo += 1
        especie_bruta = (r.get("manifestacao") or "").strip()
        especie = re.match(r"(?i)^([A-ZÇÃÉ ]+?)\s+N", especie_bruta)
        especie = especie.group(1).title().strip() if especie else "Manifestação"
        chave, rotulo, explicacao = autoridade.classificar(None, r.get("natureza"))
        despachos = {k: r.get(k) for k in (
            "despacho_do_coordenador", "despacho_do_diretor", "despacho_cgu",
            "despacho_agu", "despacho_SGU", "despacho_pres_rep") if r.get(k)}

        pdf = PDFS / f"{r['id']}.pdf"
        url = r.get("url_inteiro_teor")
        confianca = None
        paginas_txt = nativo.get(r["id"], [])
        if paginas_txt:
            origem = "pdf"
        elif pdf.exists():
            # o PDF existe mas é imagem: o texto, se houver, veio do OCR
            paginas_txt = _ler_ocr(r["id"])
            if paginas_txt and len("".join(paginas_txt).strip()) > 200:
                origem = "ocr"
                confianca = _confianca_ocr("\n".join(paginas_txt), vocab)
                reconhecidos += 1
            else:
                paginas_txt = _ler_pdf(pdf)  # preserva a contagem de páginas
                origem = "digitalizacao_sem_texto"
                sem_camada += 1
        else:
            origem = "sapiens_exige_autenticacao" if (url and "sapiens" in url) else (
                "arquivo_publico_indisponivel" if url else "sem_arquivo")
            sem_arquivo += 1

        inteiro = "\n".join(paginas_txt)
        tem_texto = 1 if origem in ("pdf", "ocr") else 0
        base = " ".join(x for x in (r.get("assunto"), r.get("ementa"), inteiro) if x)
        regime, alerta = _regime(base)

        docs.append((
            codigo, "conuni", especie, especie_bruta,
            r.get("numero"), r.get("ano"), r.get("orgao"), "CONUNI e Câmaras Nacionais",
            (r.get("assunto") or "").strip(), (r.get("ementa") or "").strip(), None,
            r.get("natureza"), chave, autoridade.ordem(chave), explicacao,
            str(r.get("vigencia")), None,
            r.get("manifestacao_revogadora") or None,
            r.get("manifestacao_reanalise") or None,
            r.get("manifestacoes_relacionadas") or None,
            (r.get("aprovacao") or "").strip() or None,
            json.dumps(despachos, ensure_ascii=False) if despachos else None,
            regime, alerta,
            len(paginas_txt), tem_texto, origem, confianca, None, url, None,
        ))
        busca.append((codigo, especie_bruta, r.get("assunto") or "",
                      r.get("ementa") or "", ""))
        secoes = _secoes(paginas_txt)
        for n, texto in enumerate(paginas_txt, 1):
            pag_meta.append((codigo, n, len(texto), secoes[n - 1], _transcricao(texto)))
            pag_texto.append((codigo, n, texto))
        for (esp, ref), qtd in referencias.extrair(base).items():
            cits.append((codigo, esp, ref, qtd))

    # ------------------------------------------------- ONs e Súmulas da AGU
    for nome, fonte in (("ons.jsonl", "on"), ("sumulas.jsonl", "sumula")):
        for r in _jsonl(nome):
            codigo += 1
            especie = r["especie"]
            chave, rotulo, explicacao = autoridade.classificar(especie, None)
            texto = r.get("texto") or ""
            enunciado = r.get("enunciado") or texto
            regime, alerta = _regime(texto)
            if r.get("regime_declarado"):
                regime = r["regime_declarado"] + (f"; {regime}" if regime else "")
                if "8.666" in r["regime_declarado"] and "14.133" not in r["regime_declarado"]:
                    alerta = ALERTA_8666
            docs.append((
                codigo, fonte, especie, r["citacao"],
                r.get("numero"), r.get("ano"), None, r.get("grupo"),
                None, enunciado[:2000], texto,
                None, chave, autoridade.ordem(chave), explicacao,
                None, r.get("situacao_declarada"),
                None, None, None, None,
                json.dumps(r.get("links"), ensure_ascii=False) if r.get("links") else None,
                regime, alerta,
                0, 1 if texto.strip() else 0,
                "pagina_oficial" if texto.strip() else "enunciado_nao_publicado",
                None, r.get("aviso"), None, r.get("url_publicacao"),
            ))
            busca.append((codigo, r["citacao"], "", enunciado[:2000], texto))
            for (esp, ref), qtd in referencias.extrair(texto).items():
                cits.append((codigo, esp, ref, qtd))

    con.executemany(f"INSERT INTO documentos VALUES ({','.join('?' * 31)})", docs)
    con.executemany("INSERT INTO paginas VALUES (?,?,?,?,?)", pag_meta)
    con.executemany("INSERT INTO paginas_fts VALUES (?,?,?)", pag_texto)
    con.executemany("INSERT INTO busca VALUES (?,?,?,?,?)", busca)
    con.executemany("INSERT INTO citacoes VALUES (?,?,?,?)", cits)

    # --------------------------------------------------------- tesauro medido
    linhas = []
    for conceito, variantes in CONCEITOS.items():
        for v in variantes:
            n = con.execute(
                "SELECT COUNT(*) FROM busca WHERE busca MATCH ?", (f'"{v}"',)).fetchone()[0]
            m = con.execute(
                "SELECT COUNT(DISTINCT codigo) FROM paginas_fts WHERE paginas_fts MATCH ?",
                (f'"{v}"',)).fetchone()[0]
            total = max(n, m)
            if total:
                linhas.append((conceito, v, total))
    con.executemany("INSERT INTO sinonimos VALUES (?,?,?)", linhas)

    # ------------------------------------------------------------- cobertura
    total = len(docs)
    com_texto = con.execute(
        "SELECT COUNT(*) FROM documentos WHERE tem_texto = 1").fetchone()[0]
    paginas = con.execute("SELECT COUNT(*) FROM paginas").fetchone()[0]
    por_vinc = dict(con.execute(
        "SELECT vinculacao_chave, COUNT(*) FROM documentos GROUP BY 1"))
    por_fonte = dict(con.execute("SELECT fonte, COUNT(*) FROM documentos GROUP BY 1"))
    anos = con.execute(
        "SELECT MIN(ano), MAX(ano) FROM documentos WHERE ano IS NOT NULL").fetchone()
    fora = con.execute(
        """SELECT COUNT(*) FROM documentos
           WHERE COALESCE(situacao_declarada,'') <> ''
              OR COALESCE(ato_revogador,'') <> ''
              OR vigencia_declarada NOT IN ('1', 'None')""").fetchone()[0]

    faixas = dict(con.execute(
        """SELECT CASE WHEN ocr_confianca >= 80 THEN 'alta (>= 80)'
                       WHEN ocr_confianca >= 60 THEN 'média (60 a 79)'
                       ELSE 'baixa (< 60)' END, COUNT(*)
           FROM documentos WHERE origem_texto = 'ocr' GROUP BY 1"""))

    dados = {
        "acervo": "Acervo consultivo da Advocacia-Geral da União",
        "documentos": total,
        "por_fonte": por_fonte,
        "com_texto_pesquisavel": com_texto,
        "recuperados_por_ocr": reconhecidos,
        "confianca_do_ocr": faixas,
        "digitalizacao_sem_texto_mesmo_apos_ocr": sem_camada,
        "sem_arquivo_publico": sem_arquivo,
        "paginas_indexadas": paginas,
        "periodo": f"{anos[0]} a {anos[1]}",
        "por_grau_de_vinculacao": {
            autoridade.ESCALA[k][1] if k in autoridade.ESCALA else k: v
            for k, v in sorted(por_vinc.items(), key=lambda x: -autoridade.ordem(x[0]))},
        "documentos_com_alguma_ressalva_de_vigencia": fora,
        "citacoes_mapeadas": len(cits),
        "aviso_ente_federado": autoridade.AVISO_ENTE,
        "limites": [
            f"{reconhecidos} manifestações só existem como digitalização e o texto "
            "veio de OCR — não é transcrição fiel. Cada uma traz `ocr_confianca`, "
            "que mede quanto do reconhecido é palavra que o acervo conhece. A "
            "qualidade é bimodal: a prosa da AGU sai legível, e os blocos de "
            "doutrina e norma transcritos, em fonte degradada, saem ilegíveis. "
            "NUNCA reproduza citação literal a partir de página reconhecida por "
            "OCR sem conferir no PDF.",
            f"{sem_arquivo} manifestações do CONUNI não têm arquivo público: a AGU "
            "as publica no Sapiens, cujo acesso anônimo devolve a tela de login. "
            "Delas só há ementa e assunto — o acervo NÃO permite conferir a "
            "fundamentação, e ausência de um argumento aqui não prova que a AGU "
            "não o enfrentou.",
            "O acervo é o que a AGU publica na consulta pública do CONUNI e nas "
            "páginas de Orientações Normativas e Súmulas. Os pareceres das "
            "Consultorias Jurídicas junto aos Ministérios não são públicos e não "
            "estão aqui.",
            "O grau de vinculação é o declarado pela fonte, não uma qualificação "
            "jurídica própria. O efeito do art. 40, § 1º, da LC 73/93 depende de "
            "aprovação presidencial e publicação, que se confere no ato, não aqui.",
        ],
    }
    con.executemany("INSERT INTO cobertura VALUES (?,?)",
                    [(k, json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v)
                     for k, v in dados.items()])
    con.commit()
    con.execute("VACUUM")
    con.close()

    print(f"banco: {BANCO}  ({BANCO.stat().st_size/1024/1024:.0f} MB)")
    for k in ("documentos", "com_texto_pesquisavel", "recuperados_por_ocr",
              "confianca_do_ocr", "digitalizacao_sem_texto_mesmo_apos_ocr",
              "sem_arquivo_publico", "paginas_indexadas", "periodo"):
        print(f"  {k:28} {dados[k]}")
    print(f"  {'por fonte':28} {por_fonte}")
    print(f"  {'citacoes':28} {len(cits)}")
    print("  grau de vinculação:")
    for rotulo, n in dados["por_grau_de_vinculacao"].items():
        print(f"    {n:>5}  {rotulo}")
    print(f"  tesauro: {len(linhas)} variantes com ocorrência, "
          f"{len(Counter(l[0] for l in linhas))} conceitos")


if __name__ == "__main__":
    main()
