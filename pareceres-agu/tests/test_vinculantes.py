"""Os 215 pareceres do art. 40, § 1º — o grau máximo do sistema.

São a única camada do acervo em que a fonte documenta os dois requisitos da
vinculação: o Presidente que aprovou e a publicação no DOU. Confundir esta
camada com as outras é o erro mais caro que o acervo pode induzir.
"""

from __future__ import annotations

import json

import autoridade


def test_parecer_vinculante_e_o_grau_maximo():
    chave, _, explicacao = autoridade.classificar(
        "Parecer Vinculante do Advogado-Geral da União", None)
    assert chave == "administracao_federal"
    assert autoridade.ordem(chave) == max(
        autoridade.ordem(k) for k in autoridade.ESCALA)
    assert "40" in explicacao and "fiel cumprimento" in explicacao


def test_os_215_estao_no_acervo(acervo):
    n = acervo.con.execute(
        "SELECT COUNT(*) FROM documentos WHERE fonte = 'vinculante'").fetchone()[0]
    assert n >= 200, n


def test_todo_vinculante_declara_presidente_e_publicacao(acervo):
    """É o que separa esta camada das outras: sem os dois requisitos do art. 40,
    § 1º, o parecer não vincula, e a fonte os declara para todos."""
    linhas = acervo.con.execute(
        "SELECT codigo, despachos FROM documentos WHERE fonte = 'vinculante'")
    sem = []
    for codigo, bruto in linhas:
        dados = json.loads(bruto) if bruto else {}
        if not dados.get("presidente") or not dados.get("data_publicacao_dou"):
            sem.append(codigo)
    assert not sem, f"{len(sem)} vinculantes sem Presidente ou data de publicação"


def test_a_prova_da_vinculacao_chega_ao_advogado(acervo):
    """O teste anterior lia a coluna do banco e passava enquanto a ferramenta
    entregava o dado sob o rótulo errado — `links_do_ato`, como se Presidente e
    publicação no DOU fossem links. É o dado que separa o parecer vinculante de
    todos os outros; sob rótulo errado, ele some."""
    codigo = acervo.con.execute(
        "SELECT codigo FROM documentos WHERE fonte = 'vinculante' LIMIT 1").fetchone()[0]
    ficha = acervo.obter(codigo).para_dict()
    assert "aprovacao" in ficha, list(ficha)
    assert "links_do_ato" not in ficha
    assert ficha["aprovacao"]["presidente"]
    assert ficha["aprovacao"]["data_publicacao_dou"]


def test_cada_fonte_rotula_a_coluna_conforme_o_que_ela_guarda(acervo):
    esperado = {"conuni": "despachos", "vinculante": "aprovacao",
                "on": "links_do_ato", "sumula": "links_do_ato"}
    for fonte, rotulo in esperado.items():
        linha = acervo.con.execute(
            "SELECT codigo FROM documentos WHERE fonte = ? "
            "AND COALESCE(despachos,'') <> '' LIMIT 1", (fonte,)).fetchone()
        if not linha:
            continue
        assert rotulo in acervo.obter(linha[0]).para_dict(), fonte


def test_vinculante_e_citado_pelo_codigo(acervo):
    """JM-10, GQ-..., AC-... é como o parecer é conhecido e conferido."""
    citacoes = [c for (c,) in acervo.con.execute(
        "SELECT citacao FROM documentos WHERE fonte = 'vinculante' LIMIT 20")]
    assert all(c.startswith("Parecer ") for c in citacoes), citacoes[:3]
    assert any("-" in c for c in citacoes), citacoes[:3]


def test_comprimento_do_texto_nao_vira_relevancia(acervo):
    """O falso positivo que a consulta real do advogado expôs: perguntando por
    aditivo de prazo em contrato de obra, o servidor devolvia como ÚNICO
    precedente vinculante o GQ-134/1997, sobre programa BEFIEX de exportação de
    câmeras fotográficas. Casava porque a fonte entrega ementa e inteiro teor no
    mesmo campo, e num texto de 40 mil caracteres qualquer termo aparece."""
    achados, _, _ = acervo.pesquisar("prorrogação prazo vigência contrato aditivo",
                                     limite=10, fonte="vinculante")
    assert not any("GQ-134" in d.citacao for d in achados), \
        [d.citacao for d in achados]


def test_o_documento_longo_continua_achavel_pelo_tema_dele(acervo):
    """O conserto não pode ter sido esconder o documento: ele some da busca por
    termo genérico e continua aparecendo no assunto que é o dele."""
    for consulta in ("BEFIEX", "programa especial de exportação"):
        achados, _, total = acervo.pesquisar(consulta, limite=5)
        assert any("GQ-134" in d.citacao for d in achados), (consulta, total)


def test_ementa_do_vinculante_e_curta_e_o_teor_esta_paginado(acervo):
    linha = acervo.con.execute(
        """SELECT codigo, LENGTH(ementa) AS n, paginas FROM documentos
           WHERE fonte = 'vinculante' AND paginas > 3 LIMIT 1""").fetchone()
    assert linha["n"] <= 1900, linha["n"]
    assert linha["paginas"] > 3
    paginas = acervo.paginas_do_documento(linha["codigo"], 1, 2)
    assert len(paginas) == 2 and paginas[0]["texto"]


def test_documento_cortado_pela_fonte_avisa(acervo):
    """59 vinculantes param no teto de ~32.700 caracteres, e 58 terminam no meio
    de uma frase. Sem o aviso, o silêncio parece ausência de argumento."""
    linha = acervo.con.execute(
        """SELECT codigo FROM documentos WHERE fonte = 'vinculante'
           AND COALESCE(aviso_fonte,'') LIKE '%32.700%' LIMIT 1""").fetchone()
    assert linha, "nenhum vinculante marcado como cortado — o aviso regrediu"
    ficha = acervo.obter(linha[0]).para_dict()
    assert "meio do texto" in ficha["aviso_da_fonte"]


def test_a_camada_federal_cresceu_com_os_vinculantes(acervo):
    por_chave = dict(acervo.con.execute(
        "SELECT vinculacao_chave, COUNT(*) FROM documentos GROUP BY 1"))
    assert por_chave["administracao_federal"] >= 300


def test_conuni_continua_com_apenas_12_de_alcance_federal(acervo):
    """O número que abre as instruções. Se ele mudar sem que a fonte mude, a
    classificação regrediu."""
    n = acervo.con.execute(
        """SELECT COUNT(*) FROM documentos WHERE fonte = 'conuni'
           AND vinculacao_chave = 'administracao_federal'""").fetchone()[0]
    assert n == 12, n


def test_o_que_vincula_poe_o_vinculante_na_frente(acervo):
    from agu.servidor import construir
    import asyncio
    servidor = construir(str(acervo.caminho))
    r = asyncio.run(servidor.call_tool(
        "o_que_vincula", {"consulta": "licença maternidade servidor"}))
    d = r[1] if isinstance(r, tuple) else r
    assert "pareceres_vinculantes" in d
    assert list(d).index("pareceres_vinculantes") < list(d).index("orientacoes_normativas")
