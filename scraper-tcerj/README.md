# Coletor de jurisprudência do TCE-RJ

Ferramenta para baixar e organizar os documentos de jurisprudência do Tribunal
de Contas do Estado do Rio de Janeiro — acórdãos, súmulas, enunciados,
deliberações, resoluções, pareceres prévios e respostas a consulta — num banco
SQLite consultável, exportável para JSONL e CSV.

## Estado atual — leia antes de usar

O código foi escrito e testado **sem acesso de rede ao site do TCE-RJ**: o
ambiente onde ele foi desenvolvido bloqueia o domínio `tcerj.tc.br`. Em termos
práticos:

| Parte | Situação |
|---|---|
| Extração de metadados (número, processo, relator, ementa, datas, assuntos) | Testada, 101 testes |
| Armazenamento, deduplicação, retomada, exportação, busca textual | Testados |
| Paginação da API (índice, deslocamento, POST com corpo) | Testada com servidor simulado |
| Navegação, busca, paginação e leitura de detalhe no navegador | Testadas contra um portal falso local, com Chromium real |
| **Endereço e formato do endpoint real do TCE-RJ** | **Não verificado — descoberto em tempo de execução** |

Por isso a ferramenta **não chuta** o endereço da API. O comando `descobrir`
abre o portal num navegador de verdade, executa uma busca, grava as chamadas de
rede que a aplicação dispara e deduz a configuração a partir delas. É um passo
único, e depois a coleta roda direto contra o endpoint.

Se a descoberta não achar nada, o modo `navegador` funciona sem endpoint algum:
ele lê o que a aplicação renderiza na tela.

## Instalação

```bash
cd scraper-tcerj
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Se você já tem um Chrome/Chromium na máquina e não quer o download do
Playwright, aponte o executável:

```bash
export TCERJ_CHROMIUM=/usr/bin/chromium
```

## Uso

### 1. Descobrir como o portal busca os dados

```bash
python -m tcerj descobrir --termo "licitação"
```

Grava `descoberta.json` com todas as chamadas JSON capturadas e escreve um
`config.json` já apontando para a mais promissora. A saída indica o endpoint
escolhido, quantos itens ele devolveu por página e onde fica a lista dentro da
resposta.

Se a busca automática não disparar (portal com fluxo diferente), rode com o
navegador visível e faça a busca com as próprias mãos — o tráfego é capturado
do mesmo jeito:

```bash
python -m tcerj descobrir --mostrar-navegador
```

Vale abrir o `descoberta.json` e conferir a escolha antes de coletar. Nenhum
cookie ou cabeçalho de sessão é gravado no relatório.

### 2. Coletar

```bash
# usando o endpoint descoberto
python -m tcerj -c config.json coletar --tipo acordao --max-paginas 20

# sem endpoint: lendo a tela, funciona de qualquer forma
python -m tcerj coletar --backend navegador --termo "dispensa de licitação"
```

A coleta é **retomável**: cada URL lida fica registrada, então interromper com
`Ctrl+C` e rodar de novo continua de onde parou, sem duplicar. Um documento que
apareça primeiro na listagem e depois no detalhe é completado, não sobrescrito.

Opções úteis: `--tipo` (acordao, sumula, enunciado, deliberacao, resolucao,
decisao, parecer_previo, resposta_consulta, voto), `--max-documentos`,
`--intervalo` (segundos entre requisições), `--banco`.

### 3. Consultar e exportar

```bash
python -m tcerj estatisticas
python -m tcerj buscar "dispensa de licitação" --limite 10
python -m tcerj exportar acordaos.jsonl --tipo acordao
python -m tcerj exportar acordaos.csv --formato csv --ano 2023
```

A busca usa índice FTS5 com remoção de acentos: `licitacao` acha `licitação`.

## Como está organizado

```
tcerj/
  modelos.py        Documento, TipoDocumento, identidade estável, citação
  extracao.py       texto/JSON -> metadados (regex de domínio, mojibake)
  descoberta.py     interceptação de rede e inferência do endpoint
  navegador.py      coleta via Playwright (não depende de endpoint)
  pipeline.py       paginação da API e orquestração
  http.py           controle de taxa, repetição, robots.txt
  armazenamento.py  SQLite, retomada, exportação JSONL/CSV
  cli.py            linha de comando
```

Decisão central: os metadados são extraídos do **texto**, não da estrutura da
página. O layout do portal muda; a forma como o Tribunal escreve "Acórdão nº
1.234/2020" ou "Relator: Conselheiro Fulano" não. Quando o seletor de CSS
falha, a extração por texto ainda entrega o registro.

## Postura de coleta

- Intervalo padrão de 1,5 s entre requisições e no máximo 2 em paralelo.
- `robots.txt` é respeitado por padrão (`respeitar_robots`).
- `Retry-After` é obedecido; erros transitórios repetem com espera crescente.
- Só há leitura de conteúdo público; não há login, contorno de captcha nem
  qualquer forma de burlar controle de acesso.

Antes de uma coleta ampla, vale conferir os termos de uso do portal. Para
volumes grandes e recorrentes, o caminho mais correto é um pedido via LAI ou o
contato com a ouvidoria do Tribunal.

## Testes

```bash
pytest                      # tudo
pytest -m "not integracao"  # sem navegador, roda em segundos
```

Os testes de integração sobem um portal falso em `localhost` e o percorrem com
Chromium de verdade — foi assim que apareceram dois defeitos reais: números de
quatro dígitos truncados ("1234" lido como "123") e páginas servidas sem
charset, que chegavam como `ACÃ“RDÃƒO` e quebravam toda a extração.

## Limitações conhecidas

- O endpoint real ainda não foi visto; a primeira execução de `descobrir` é o
  que valida (ou não) essa parte.
- Os seletores padrão de `config.json` são genéricos. Se o modo `navegador`
  trouxer pouca coisa, ajuste `item_resultado` e `proxima_pagina` para o layout
  real.
- Documentos que só existem em PDF são registrados com a URL do arquivo
  (`url_pdf`), sem extração do texto — falta um passo de OCR/parse de PDF.
- Não há agendamento embutido para coleta incremental periódica.
