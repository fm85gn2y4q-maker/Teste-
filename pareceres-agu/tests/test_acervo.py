from __future__ import annotations

from agu.acervo import montar_consulta_fts


# ------------------------------------------------------- tradução da consulta

def test_aspas_viram_busca_literal():
    assert montar_consulta_fts('"registro de preços"') == '"registro de preços"'


def test_apostrofo_e_hifen_nao_quebram_a_sintaxe():
    """Sem sanear, um hífen vira operador do FTS5 e a consulta falha inteira em
    vez de simplesmente achar menos."""
    saida = montar_consulta_fts("contrato guarda-chuva d'água")
    assert "-" not in saida.replace('"', "")
    assert "AND" in saida


def test_operador_ou_liga_os_termos():
    assert montar_consulta_fts("dispensa inexigibilidade", "OR") == "dispensa OR inexigibilidade"


def test_consulta_vazia_devolve_vazio():
    assert montar_consulta_fts("   ") == ""


# --------------------------------------------------------------- sobre o banco

def test_todo_documento_tem_grau_de_vinculacao(acervo):
    faltando = acervo.con.execute(
        "SELECT COUNT(*) FROM documentos WHERE vinculacao_chave IS NULL").fetchone()[0]
    assert faltando == 0


def test_nenhum_documento_e_federal_por_acidente(acervo):
    """Alcance federal só pode vir de declaração da fonte ou de espécie
    normativa. Se aparecer um parecer 'federal' sem natureza declarada, a régua
    quebrou."""
    linhas = acervo.con.execute(
        """SELECT COUNT(*) FROM documentos
           WHERE vinculacao_chave = 'administracao_federal'
             AND fonte = 'conuni'
             AND COALESCE(vinculacao,'') <> 'Toda a Administração Pública Federal'"""
    ).fetchone()[0]
    assert linhas == 0


def test_ons_e_sumulas_estao_no_acervo(acervo):
    por_fonte = dict(acervo.con.execute(
        "SELECT fonte, COUNT(*) FROM documentos GROUP BY 1"))
    assert por_fonte.get("on", 0) >= 100
    assert por_fonte.get("sumula", 0) >= 80
    assert por_fonte.get("conuni", 0) >= 1700


def test_sumulas_vao_de_1_a_86_sem_buraco(acervo):
    """A página traz variações de cabeçalho; um regex estrito perdia a 50 e a 51
    em silêncio."""
    numeros = [n for (n,) in acervo.con.execute(
        "SELECT numero FROM documentos WHERE fonte = 'sumula' ORDER BY numero")]
    assert numeros == list(range(1, max(numeros) + 1))


def test_on_revogada_traz_ressalva(acervo):
    """O caso que a busca literal esconde: a ON revogada não tem enunciado, e
    sem a ressalva ela aparece como qualquer outra."""
    linha = acervo.con.execute(
        """SELECT codigo FROM documentos
           WHERE fonte = 'on' AND lower(situacao_declarada) LIKE '%revogad%'
           LIMIT 1""").fetchone()
    assert linha, "nenhuma ON marcada como revogada — o parser de situação regrediu"
    ficha = acervo.obter(linha[0]).para_dict()
    assert "ressalvas_de_vigencia" in ficha
    assert "aviso_vigencia" in ficha


def test_manifestacao_sem_inteiro_teor_avisa(acervo):
    linha = acervo.con.execute(
        "SELECT codigo FROM documentos WHERE origem_texto = 'sapiens_exige_autenticacao' "
        "LIMIT 1").fetchone()
    assert linha
    ficha = acervo.obter(linha[0]).para_dict()
    assert "aviso" in ficha and "login" in ficha["aviso"]


def test_on_sem_numero_na_fonte_nao_ganha_ano_inventado(acervo):
    """A página da AGU tem um cartão cujo título perdeu número e ano. Copiar o
    ano da ON anterior parecia inofensivo e estava errado: a vizinha de cima é
    de 2024 e a de baixo, de 2025. Ano inventado numa citação é erro que o
    cliente paga."""
    linha = acervo.con.execute(
        """SELECT codigo, ano, citacao FROM documentos
           WHERE fonte = 'on' AND citacao LIKE '%ano não identificado%'""").fetchone()
    assert linha, "o cartão sem número sumiu do parser — confira a página da AGU"
    assert linha["ano"] is None
    ficha = acervo.obter(linha["codigo"]).para_dict()
    assert "ano não identificado" in ficha["citacao"]
    assert "não pôde ser determinado" in ficha["aviso_da_fonte"]
    assert "conferir número e ano" in ficha["aviso_da_fonte"]


def test_pagina_de_ocr_nunca_passa_por_transcricao_fiel(acervo):
    """O risco do OCR aqui não é errar — é ser citado como se fosse fiel. O
    reconhecimento acerta a prosa da AGU e estraga os blocos transcritos, que é
    exatamente o que se copia para uma peça."""
    linha = acervo.con.execute(
        "SELECT codigo FROM documentos WHERE origem_texto = 'ocr' LIMIT 1").fetchone()
    if not linha:
        return  # OCR ainda não rodou nesta máquina
    ficha = acervo.obter(linha[0]).para_dict()
    assert ficha["texto_veio_de_ocr"] is True
    assert isinstance(ficha["ocr_confianca"], int)
    assert "NÃO é transcrição fiel" in ficha["aviso"]
    assert "Confira no PDF" in ficha["aviso"]


def test_confianca_do_ocr_esta_entre_0_e_100(acervo):
    fora = acervo.con.execute(
        """SELECT COUNT(*) FROM documentos WHERE origem_texto = 'ocr'
           AND (ocr_confianca IS NULL OR ocr_confianca < 0 OR ocr_confianca > 100)"""
    ).fetchone()[0]
    assert fora == 0


def test_so_o_que_veio_de_ocr_tem_confianca(acervo):
    """Confiança em documento de texto nativo seria ruído: sugeriria dúvida
    onde não há."""
    fora = acervo.con.execute(
        "SELECT COUNT(*) FROM documentos WHERE origem_texto <> 'ocr' "
        "AND ocr_confianca IS NOT NULL").fetchone()[0]
    assert fora == 0


def test_busca_por_ementa_encontra_tema_conhecido(acervo):
    achados, _, total = acervo.pesquisar("engenharia consultiva", limite=5)
    assert total >= 1
    assert any("engenharia" in (d.assunto or d.ementa or "").lower() for d in achados)


def test_pagina_carrega_secao_e_transcricao(acervo):
    achados, _, total = acervo.pesquisar_paginas("licitação", limite=3)
    if not total:
        return
    trecho = achados[0].trechos[0].para_dict()
    assert "secao" in trecho and "transcricao_percent" in trecho


def test_cobertura_declara_o_que_falta(acervo):
    cob = acervo.cobertura()
    assert cob["documentos"] >= 1900
    assert int(cob["sem_arquivo_publico"]) > 1000
    limites = " ".join(cob["limites"])
    assert "Sapiens" in limites
    assert "Consultorias Jurídicas" in limites


def test_cobertura_declara_o_limite_do_filtro_por_camara(acervo):
    """O filtro usa o campo da fonte, e 5 documentos nomeiam a propria camara
    sem estarem marcados nela. Pouco, mas quem varre um tema precisa saber."""
    limites = " ".join(acervo.cobertura()["limites"])
    assert "filtro por câmara" in limites
    assert "agrupamento residual" in limites
    assert "1.416 são do DECOR" in limites


def test_o_balde_residual_nao_tem_autor_unico(acervo):
    """A afirmacao que a conferencia do advogado derrubou: nenhuma contagem
    deste acervo autoriza atribuir os 1.471 a um orgao so."""
    total = acervo.con.execute(
        "SELECT COUNT(*) FROM documentos WHERE fonte='conuni' AND orgao='CONUNI'").fetchone()[0]
    conuni = acervo.con.execute(
        "SELECT COUNT(*) FROM documentos WHERE fonte='conuni' "
        "AND upper(citacao) LIKE '%/CONUNI/%'").fetchone()[0]
    assert total > 1000
    assert conuni < 100, "o balde residual deixou de ser residual — reveja o rótulo"
    anos = [a for (a,) in acervo.con.execute(
        "SELECT DISTINCT ano FROM documentos WHERE fonte='conuni' "
        "AND upper(citacao) LIKE '%/CONUNI/%'")]
    assert min(anos) >= 2025, "a CONUNI e recente; documento antigo com a sigla e suspeito"


def test_aviso_de_ente_esta_na_cobertura(acervo):
    assert "Município" in acervo.cobertura()["aviso_ente_federado"]
