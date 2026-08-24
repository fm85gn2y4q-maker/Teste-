# Pipeline — como o acervo foi construído

Receita para reconstruir `pge_rj_pareceres.db` do zero, na ordem em que as
etapas rodaram. Cada script é executável direto e imprime o que fez.

O banco é artefato de dados e fica fora do repositório, em
`D:\PGE-RJ_Pareceres_Contratacoes\`. Os arquivos intermediários
(`.jsonl`) são gravados **ao lado dos scripts**, nesta pasta.

**O pipeline não roda no `.venv` do servidor.** São dependências diferentes de
propósito: o servidor MCP só precisa do `mcp` e serve o banco pronto; a
construção precisa do PyMuPDF para ler PDF. Instale à parte:

```bash
pip install -r ..\requirements-pipeline.txt
```

Aqui ele roda no Python do sistema, que já tem PyMuPDF 1.28.

## Ordem

| # | Script | O que faz | Custo |
|---|---|---|---|
| 1 | `harvest_all.py` | colhe os metadados dos **49.139** documentos do acervo da PGE-RJ pela API do BNPortal → `catalogo_pgerj_total.jsonl` | ~35 min, 246 requisições |
| 2 | `classificar.py` | seleciona localmente o que é contratação/acordo/parceria → `selecionados.jsonl` (14.420) e `descartados.jsonl` | segundos |
| 3 | `exportar_final.py` | gera os CSVs do núcleo e do acervo integral | segundos |
| 4 | `baixar_pdfs.py` | baixa os inteiros teores, do mais novo para o mais antigo | ~7 h, 12,4 GB |
| 5 | `indexar.py` | cria `documentos`, `busca` (FTS) e a primeira extração de citações | ~30 min |
| 6 | `passada2.py` | indexa **por página**, extrai conclusão classificada por tipo, reextrai citações com o regex corrigido | ~25 min |
| 7 | `passada3.py` | tesauro medido, proveniência (seção + grau de transcrição), regime de vigência, tabela `cobertura` | ~2 min |
| 8 | `aplicar_rodape.py` | corta o rodapé do SEI do fim de `conclusao` e `fecho` | segundos |

Módulos de apoio, importados pelos acima: `api.py` (cliente da API do
BNPortal), `corrigir.py` (regex de citações), `conclusao.py` (fórmulas de
fecho), `rodape.py` (marcadores de rodapé).

`corrigir.py` também tem um `main()` — foi a tentativa de corrigir lendo o
texto de volta do FTS. **Não use:** era ordens de grandeza mais lenta que reler
o PDF, e por isso a etapa 6 existe. Ficou porque o regex dela é a fonte da
verdade das citações.

## O que cada etapa produz no banco

```
documentos    ficha + conclusao/conclusao_tipo/fecho + regime/alerta_vigencia
paginas       codigo, pagina, caracteres, secao, transcricao
paginas_fts   texto de cada página  (busca com citação de folha)
busca         texto do documento inteiro  (busca por documento)
citacoes      norma, súmula, acórdão, precedente interno, tribunal
sinonimos     tesauro medido: conceito → variantes → contagem
cobertura     limites declarados, servidos por cobertura_do_acervo
```

## Três coisas que custaram caro

**1. A busca do BNPortal é literal, e frase sem parênteses vira "E" entre as
palavras.** `(LICITAÇÃO)+(CONVÊNIO)` é OU; `LICITAÇÃO CONVÊNIO` é E. Uma busca
temática ampla pelo portal devolveu 19.830 documentos, dos quais **46% eram
ruído** — pareceres sobre merenda escolar, averbação de tempo de serviço,
regime de recuperação fiscal, que só mencionavam a palavra de passagem. Por
isso a etapa 1 colhe **tudo** e a etapa 2 seleciona localmente: a consulta ao
portal não é confiável como filtro temático.

**2. Ler texto de volta do FTS é ordens de grandeza mais lento que reler o
PDF.** A extração de citações a partir do índice travou; a mesma extração
relendo os PDFs levou 25 minutos. O regex custa 0,03 s por parecer — o gargalo
nunca foi ele.

**3. Alternância de regex é preguiçosa à esquerda.** `(\d{1,3}(?:\.\d{3})*|\d{1,6})`
casava `866` dentro de `8666` e nunca tentava a segunda alternativa: 1.224
documentos ficaram com "Lei 866/1993" em vez de "Lei 8.666/1993". Corrigido
exigindo o grupo de milhar na primeira alternativa. Depois da correção, a
8.666/93 subiu de 4.812 para **5.021 documentos** e de 33.701 para 41.915
citações.

## Limites conhecidos

- O caminho do acervo vive num lugar só, `caminhos.py`. Trocar de disco é
  trocar uma linha, ou exportar `PARECERES_ACERVO`/`PARECERES_BANCO`.
- As etapas 5 a 8 **reconstroem** as tabelas que tocam. Para incorporar só o
  que chegou depois da última coleta há o par `atualizar.py` +
  `incrementar.py`, que roda as mesmas etapas com `--novos`.
  A etapa 4 é retomável (pula o que já está em disco).
- 291 PDFs são digitalização sem camada de texto e ficam invisíveis à busca.
  Precisariam de OCR, que não está instalado nesta máquina.
- 14 documentos têm PDF cadastrado que o portal recusa servir (HTTP 403
  persistente). Estão em `_falhas_download.txt`, junto do acervo.

## Coleta educada

A etapa 1 faz 246 requisições; a etapa 4, cerca de 8.600, com 4 conexões
simultâneas e pausa entre elas. É acervo público, mas o servidor é da
Procuradoria — não varra sem necessidade e não aumente a concorrência.
