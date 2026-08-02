"""As ferramentas, exercitadas pelo próprio servidor MCP."""

import asyncio
import json

import pytest


def chamar(servidor, ferramenta, argumentos=None):
    resultado = asyncio.run(servidor.call_tool(ferramenta, argumentos or {}))
    conteudo = resultado[1] if isinstance(resultado, tuple) else resultado
    if isinstance(conteudo, dict):
        return conteudo
    return json.loads(conteudo[0].text)


FERRAMENTAS = {
    "pesquisar_pareceres", "pesquisar_inteiro_teor", "ler_paginas",
    "expandir_consulta", "obter_documento", "conclusoes_sobre",
    "quem_citou", "listar_documentos", "cobertura_do_acervo",
}


def test_todas_as_ferramentas_registradas(servidor):
    nomes = {t.name for t in asyncio.run(servidor.list_tools())}
    assert nomes == FERRAMENTAS


def test_as_instrucoes_carregam_as_tres_regras(servidor):
    texto = servidor.instructions or ""
    assert "REGRA 1" in texto and "REGRA 2" in texto and "REGRA 3" in texto
    assert "PERSUASIVO" in texto


def test_cobertura(servidor):
    d = chamar(servidor, "cobertura_do_acervo")
    assert d["documentos"] == "14420" and d["paginas"] == "177156"


def test_busca_estreita_demais_cai_para_qualquer_termo(servidor):
    """Consulta longa com todos os termos exigidos devolvia zero por motivo
    lexical. O servidor refaz com OU — e declara que refez."""
    d = chamar(servidor, "pesquisar_pareceres",
               {"consulta": "organização social chamamento público dispensa", "limite": 2})
    assert d["total_encontrado"] > 0
    assert "qualquer termo" in d["criterio"]


def test_expressao_exata_nao_e_afrouxada(servidor):
    d = chamar(servidor, "pesquisar_pareceres",
               {"consulta": '"contrato de gestão"', "limite": 2})
    assert d["total_encontrado"] > 0
    assert d["criterio"].startswith("todos")


def test_inteiro_teor_devolve_pagina_e_proveniencia(servidor):
    d = chamar(servidor, "pesquisar_inteiro_teor",
               {"consulta": "adesão à ata de registro de preços", "limite": 3,
                "paginas_por_documento": 1})
    assert d["documentos_com_ocorrencia"] > 0
    for r in d["resultados"]:
        for p in r["paginas_encontradas"]:
            assert "pagina" in p and "secao" in p and "transcricao_percent" in p
    assert "lembrete" in d


def test_excluir_relatorio(servidor):
    d = chamar(servidor, "pesquisar_inteiro_teor",
               {"consulta": "licitação", "limite": 5, "paginas_por_documento": 1,
                "excluir_relatorio": True})
    secoes = {p["secao"] for r in d["resultados"] for p in r["paginas_encontradas"]}
    assert not any("relatório" in s for s in secoes)


def test_expandir_consulta(servidor):
    d = chamar(servidor, "expandir_consulta", {"termo": "organização social"})
    assert d["conceitos"] and d["conceitos"][0]["conceito"] == "terceiro setor"


def test_expandir_consulta_termo_desconhecido(servidor):
    d = chamar(servidor, "expandir_consulta", {"termo": "zzzz inexistente"})
    assert d["conceitos"] == []
    assert "sinônimos" in d["nota"]


def test_conclusoes_sobre_so_traz_quem_tem_conclusao(servidor):
    """Buscava por relevância e filtrava depois: quando documentos sem inteiro
    teor ocupavam as primeiras posições, a lista vinha vazia."""
    d = chamar(servidor, "conclusoes_sobre",
               {"consulta": "adesão ata registro de preços", "limite": 3})
    assert d["conclusoes"]
    assert all(c["conclusao"] for c in d["conclusoes"])


def test_quem_citou(servidor):
    d = chamar(servidor, "quem_citou", {"referencia": "Lei 14.133", "limite": 2})
    assert d["encontrado"] and d["documentos_que_citam"] > 500


def test_listar_por_eixo(servidor):
    d = chamar(servidor, "listar_documentos", {"eixo": "Terceiro setor", "limite": 3})
    assert d["resultados"]


def test_obter_documento_inexistente(servidor):
    assert "erro" in chamar(servidor, "obter_documento", {"id": 99999999})


def test_ler_paginas_documento_inexistente(servidor):
    assert "erro" in chamar(servidor, "ler_paginas",
                            {"id": 99999999, "pagina_inicial": 1})


def test_parecer_de_terceiro_setor_nao_vem_como_8666(servidor):
    """Todo parecer de organização social vinha rotulado "Lei 8.666/1993 —
    revogada", sugerindo descarte de tese que continua válida."""
    d = chamar(servidor, "obter_documento", {"id": 8510})  # PARECER GUB 03/2013
    assert "9.637" in d["regime"]
    assert "lateral" in d["alerta_vigencia"]
