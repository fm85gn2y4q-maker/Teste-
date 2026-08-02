# -*- coding: utf-8 -*-
"""Corta o rodape do SEI e afins do fim da conclusao.

O extrator pega 2.000 caracteres a partir da formula de fecho e nao sabe onde o
texto juridico acaba. No parecer 35/2024 isso arrastou assinatura eletronica,
codigo verificador, endereco da Procuradoria e telefone. Aqui a conclusao passa
a terminar no primeiro marcador de rodape encontrado.
"""
import re
import unicodedata


def _norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


# Cada padrao marca o inicio do lixo: dali para a frente nao ha mais conteudo
# juridico. Casados sobre o texto SEM acento e em minusculas.
RODAPE = re.compile(
    r"sei/erj\b"
    r"|documento assinado eletronicamente"
    r"|a autenticidade deste documento"
    r"|codigo verificador"
    r"|conforme horario oficial de brasilia"
    r"|referencia:\s*processo n"
    r"|\{digite aqui a nota de rodape\}"
    r"|https?://sei\.rj\.gov\.br"
    r"|https?://www\.pge\.rj\.gov\.br"
    r"|\bsei\.rj\.gov\.br/sei/controlador"
    r"|\bcep:?\s*\d{2}\.?\d{3}-?\d{3}"
    r"|\bav(?:enida)?\.?\s+erasmo\s+braga"
    r"|\br\.?\s+do\s+carmo,\s*27"
    r"|\d{2}/\d{2}/\d{4},?\s+\d{1,2}:\d{2}\s+sei"
    r"|acao=documento_imprimir_web"
    r"|infra_sistema=",
)

# Minimo de texto antes de aceitar o corte: sem isto, uma conclusao que comece
# logo antes do rodape seria reduzida a nada.
MINIMO = 80


def limpa_rodape(texto: str) -> str:
    if not texto:
        return texto
    alvo = _norm(texto)
    corte = None
    for m in RODAPE.finditer(alvo):
        if m.start() >= MINIMO:
            corte = m.start()
            break
    if corte is None:
        return texto.strip()
    limpo = texto[:corte].rstrip(" -–—|;,")
    # nao deixa a frase pendurada num fragmento minusculo
    return (limpo if len(limpo) >= MINIMO else texto).strip()
