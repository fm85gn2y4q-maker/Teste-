# -*- coding: utf-8 -*-
"""Onde o acervo mora. Um lugar so.

O caminho estava escrito a mao em doze scripts. Mudar de disco seria mudar doze
linhas, e esquecer uma delas nao da erro: da metade do pipeline gravando num
banco e metade lendo de outro, que foi exatamente a familia de defeitos que
custou tres correcoes na indexacao anterior.

O acervo esta partido em dois discos DE PROPOSITO:

  PDFs  -> HD externo. Sao 26 GB e material frio: so sao relidos numa
           reindexacao completa, que ja e operacao de horas. No disco do
           sistema sobravam 34 GB, e o proprio coletor para sozinho quando
           restam menos de 3.

  banco -> NVMe. Sao 1,4 GB e e o que responde a cada pergunta. Medido nesta
           maquina: leitura sequencial de 485 MB/s no NVMe contra 42 MB/s no
           HD externo, e -- o que decide -- 0,3 MB/s de leitura aleatoria no
           externo durante consulta FTS5. A suite de testes roda em 80 s com o
           banco no NVMe e nao terminou em 13 min com ele no HD.

Juntar os dois de volta e mudar UMA linha aqui (ou exportar as variaveis).

  PARECERES_ACERVO  troca a raiz dos PDFs
  PARECERES_BANCO   troca o banco
"""
import os

# Os PDFs: massa fria, no HD externo.
BASE = os.environ.get("PARECERES_ACERVO", r"D:\PGE-RJ_Pareceres_Contratacoes")
PDFS = os.path.join(BASE, "PDFs")

# O banco: quente, no disco rapido. O HD externo guarda uma copia identica,
# como backup -- nao como o arquivo de trabalho.
BANCO_RAIZ = os.path.expanduser("~/Documents/PGE-RJ_Pareceres_Contratacoes")
DB = os.environ.get("PARECERES_BANCO", os.path.join(BANCO_RAIZ, "pge_rj_pareceres.db"))

# Os exports (CSV e JSONL do catalogo) sao registros que a pessoa abre e le.
# Ficam com o banco, nao com os PDFs: o HD externo e arquivo morto, e abrir
# planilha de 36 MB de la e sofrimento sem motivo.
REGISTROS = BANCO_RAIZ
