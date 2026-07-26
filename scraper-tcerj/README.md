# Coletor de jurisprudência do TCE-RJ

Ferramenta para baixar e organizar os documentos de jurisprudência do Tribunal
de Contas do Estado do Rio de Janeiro — acórdãos, súmulas, enunciados,
deliberações, resoluções, pareceres prévios e respostas a consulta — num banco
SQLite consultável, exportável para JSONL e CSV.

## Estado atual — leia antes de usar

**Calibrado contra o site real em 25/07/2026.** Até então o código nunca havia
sido executado contra `tcerj.tc.br`, e o endereço do endpoint era só hipótese.

A descoberta revelou que **não existe um endpoint, e sim quatro bases
distintas**, cada uma com formato próprio. Todas foram percorridas de ponta a
ponta:

| Base | Endpoint | Registros |
|---|---|---|
| Jurisprudência Selecionada (ementas de acórdãos) | `POST /liana-processo-webapi/consulta/pagina/{pagina}/tamanhoPagina/{tamanho}` | 1.067 |
| Respostas às Consultas | `POST /cadastro-publicacoes-webapi/api/Consulta/listar` | 572 |
| Súmulas | `GET /cadastro-publicacoes-webapi/api/Sumula` | 28 |
| Questões de Ordem | `POST /liana-processo-webapi/questaoordem/consulta/pagina/{pagina}/tamanhoPagina/{tamanho}` | 4 |

Duas ressalvas que mudam a expectativa sobre o acervo:

- A Jurisprudência Selecionada é **curadoria**, não o acervo integral: são as
  ementas escolhidas pelo Serviço de Jurisprudência, não todos os acórdãos do
  Tribunal.
- **Deliberações e Resoluções não ficam neste portal.** O menu redireciona para
  `atosoficiais.com.br`, um serviço de terceiro. Não há coleta delas aqui.

Não existe base própria de "enunciado" (o enunciado é o conteúdo da súmula) nem
de "parecer prévio".

O comando `descobrir` continua sendo o caminho quando o portal mudar: abre as
telas de consulta num navegador de verdade, executa uma busca, grava as
chamadas de rede e deduz a configuração — inclusive quando a paginação vem
embutida na rota, como é o caso aqui. Se ele não achar nada, o modo `navegador`
funciona sem endpoint algum, lendo o que a aplicação renderiza na tela.

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

Cada base tem sua configuração; as quatro já vêm calibradas no repositório. O
`--tipo` **não filtra no servidor**, apenas rotula o que veio — por isso a
config e o tipo andam sempre juntos:

```bash
python -m tcerj -c config.json               coletar --tipo acordao           --max-paginas 50
python -m tcerj -c config-consultas.json     coletar --tipo resposta_consulta --max-paginas 50
python -m tcerj -c config-sumulas.json       coletar --tipo sumula            --max-paginas 1
python -m tcerj -c config-questao-ordem.json coletar --max-paginas 5
```

`config.json` não é versionado — é o arquivo que `descobrir` sobrescreve. Se
não existir, rode `descobrir` ou copie `config.exemplo.json` ajustando a URL
conforme a tabela acima. As súmulas vêm num único array, sem paginação: daí o
`--max-paginas 1`.

Sem endpoint algum, lendo a tela, também funciona:

```bash
python -m tcerj coletar --backend navegador --termo "dispensa de licitação"
```

A coleta é **retomável**: cada URL lida fica registrada, então interromper com
`Ctrl+C` e rodar de novo continua de onde parou, sem duplicar. Um documento que
apareça primeiro na listagem e depois no detalhe é completado, não sobrescrito.
Como estes endpoints não devolvem URL por item, a deduplicação se apoia no
identificador do documento — inclusive o `id_fonte`, sem o qual duas ementas do
mesmo acórdão colapsariam numa só.

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

São 113. Os testes de integração sobem um portal falso em `localhost` e o
percorrem com Chromium de verdade — foi assim que apareceram dois defeitos
reais: números de quatro dígitos truncados ("1234" lido como "123") e páginas
servidas sem charset, que chegavam como `ACÃ“RDÃƒO` e quebravam toda a extração.

A primeira execução contra o site real rendeu outros cinco, todos hoje cobertos
por teste — vale como aviso de que portal simulado não substitui portal de
verdade:

- Carimbo de data ISO com `T` (`2026-05-25T00:00:00`) não casava o regex, e
  `data_sessao` vinha vazia em **todos** os registros.
- A quebra de linha da ementa é a sequência literal `\n`, que aparecia crua.
- `tipo+número+ano` **não é chave única**: um mesmo acórdão rende várias
  ementas selecionadas, uma por macro-tema, e a segunda sobrescrevia a primeira
  em silêncio. Daí o `id_fonte`.
- O `re.IGNORECASE` global anulava a exigência de maiúscula no nome do relator,
  que passava a capturar prosa corrente ("relator antes de iniciada a").
- `numeroAcordao`/`anoAcordao` iguais a zero viravam "Acórdão 0/2000".

## Ementário — o acervo como ferramenta de IA (MCP)

`ementario/` expõe o acervo coletado a assistentes de IA pelo protocolo MCP,
para consultar a jurisprudência do TCE-RJ de dentro do Claude ou do ChatGPT.

```bash
python -m ementario            # stdio — é o que o Claude consome
python -m ementario --http     # HTTP em 127.0.0.1:8765
python -m ementario.publicar   # HTTP + túnel HTTPS público — para o ChatGPT
```

Ferramentas: `pesquisar_jurisprudencia`, `obter_documento`, `listar_documentos`,
`cobertura_do_acervo`, mais `search`/`fetch` no formato que a pesquisa profunda
do ChatGPT exige.

A busca é pensada para pergunta de gente, não para sintaxe: ignora acento,
descarta palavras vazias ("posso", "qual", "em") e, se exigir todos os termos
não achar nada, repete aceitando qualquer um — avisando que a correspondência
foi parcial. O banco é aberto **somente para leitura**.

### Ligar ao Claude

**O bloco `mcpServers` do `claude_desktop_config.json` não funciona nas versões
recentes do Claude Desktop.** Comprovado na build 1.24012.9 (Microsoft Store,
com Cowork): a chave é lida e ignorada — nenhum `mcp-*.log` é gerado e o
`main.log` não menciona o servidor. As sessões dessa build rodam em VM na
nuvem, que não alcança um processo `stdio` na máquina; os plugins nativos são
todos `{"type": "http"}` apontando para endereços remotos.

Restam dois caminhos:

1. **Conector HTTP** — o mesmo do ChatGPT (abaixo). Um endereço serve aos dois.
2. **Extensão `.mcpb`** — `python empacotar_mcpb.py` gera
   `dist/ementario.mcpb`, que se instala arrastando para Configurações →
   Extensões. Roda por stdio, sem túnel e sem depender de a máquina estar
   publicando nada.

O pacote leva o acervo e as dependências dentro, porque o Claude Desktop não
instala nada — só executa o que está lá. As dependências vão **separadas por
versão de Python** (`lib/py312`, `lib/py313`, …): `pydantic_core` é binário
compilado e o `.pyd` de uma versão não carrega em outra. O `pywin32` também
precisa de ajuda, porque instalado com `pip --target` não roda seu
pós-instalação e deixa `pywintypes` em `win32/lib` e as DLLs em
`pywin32_system32`, fora do `sys.path` — o `main.py` gerado acrescenta os dois.

O Claude Desktop resolve `python` pelo **PATH dele**, que pode não ser o seu. Se
o primeiro que ele achar não servir, fixe um no manifesto:

```bash
python empacotar_mcpb.py --python "C:\caminho\para\python.exe"
```

O empacotador recusa um interpretador que não consiga importar o que o servidor
usa. Vale a checagem: um Python com a biblioteca padrão incompleta responde
`--version` sem reclamar e só falha quando o servidor sobe, dentro do Claude,
onde o erro fica escondido num log.

### Ligar ao ChatGPT (remoto, HTTPS)

O ChatGPT não enxerga `localhost`: só conversa com servidor remoto. E o SDK
bloqueia por padrão qualquer Host que não seja local — proteção contra DNS
rebinding, sem a qual um site malicioso poderia falar com o servidor pelo
navegador de quem o executa. Servir para fora exige **declarar o domínio**:

```bash
python -m ementario --http --dominio meu-endereco.exemplo.com
```

`python -m ementario.publicar` faz isso sozinho: levanta um túnel do
Cloudflare, lê o endereço sorteado, sobe o servidor já autorizando aquele
domínio e imprime a URL (`…/mcp`) para colar em Configurações → Conectores.
Não pede conta, mas o endereço dura enquanto o processo estiver no ar e muda a
cada execução — para URL fixa, é caso de hospedar o servidor e o SQLite.

A liberação é por domínio exato, não curinga: publicar não abre o servidor para
o resto do mundo, e o acesso local continua valendo.

### Link de conferência

Cada resultado traz o endereço para conferir a fonte — uma ementa é resumo
oficial, não o acórdão:

| Campo | O que abre | Cobertura |
|---|---|---|
| `url_inteiro_teor` | PDF do acórdão, com o voto integral | 1.065 acórdãos |
| `url_processo` | Consulta processual no portal | 1.642 de 1.671 |
| `url_portal` | Tela pública da espécie | todos |

Os endpoints de listagem não devolvem esses links; eles são montados a partir
do número e do ano, que já vêm na coleta:

```
https://www.tcerj.tc.br/documento-webapi-externo/api/documento/acordao/{numero}/{ano}?votoInteiro=true
https://www.tcerj.tc.br/consulta-processo/Processo/List?numeroProcesso={numero}-{dv}/{ano}
```

Súmulas não têm processo nem acórdão — para elas só resta a tela pública, o que
é suficiente, já que o enunciado coletado é o texto integral. As respostas a
consulta têm `arquivoId` no payload, mas o endpoint de download correspondente
não foi identificado; elas ficam com o link do processo.

## O que estas bases não entregam

Nenhum dos quatro endpoints devolve `url`, `url_pdf` ou órgão julgador — os
campos ficam vazios porque não existem no payload, não por falha de extração.
Os acórdãos não trazem data de publicação (só a data do voto); as súmulas não
têm processo nem relator, o que é correto.

## Pesquisa Textual — mapeada, ainda não coletada

É a base do **inteiro teor dos votos e acórdãos**, e a mais valiosa que ficou
de fora. O formulário vive num *iframe* (`/pesquisa-textual/app`), razão pela
qual `descobrir` não o enxerga: ele inspeciona apenas o quadro principal.

```
POST /liana-pesquisa-externo/api/pesquisatextual/pagina/{pagina}/tamanhoPagina/{tamanho}
corpo: {"comTodasAsPalavras": "...", "bases": {"votos": true, "acordaos": false, ...},
        "retornaTextoDocumento": true, "pagina": 1, "quantidadePorPagina": 20}
```

O texto integral vem em `resultados[].resultados[].texto`, junto de `categoria`
("VOTO") e `idDocumento`. Coletá-la exige três coisas que o pipeline ainda não
faz:

1. **Achatar a lista aninhada.** O item externo é o *processo*; os documentos
   ficam um nível abaixo, e `caminho_itens` só percorre um nível.
2. **Remover a marcação de destaque.** O servidor injeta `<mark
   class="highlight">` em torno de cada ocorrência do termo, inclusive dentro
   de palavras (`DECISÃO` volta como `<mark>DE</mark>CISÃO`).
3. **Mapear os campos de outro jeito.** O `numero` do registro é o número do
   *processo*, não do documento; usar a lista de apelidos atual produziria
   citações falsas como "Acórdão 228647/2026".

Some-se a isso que a base **não é enumerável**: exige termo de busca e devolve
sempre `quantidadeTotal: 10000`, um teto fixo, não a contagem real.

## Limitações conhecidas

- A pontuação de `descobrir` premia vocabulário jurídico e tamanho da lista,
  então pode eleger uma base menor: as quatro legítimas aparecem no topo, mas a
  escolha ainda merece revisão humana, como a saída do comando avisa.
- Os seletores padrão são genéricos. Se o modo `navegador` trouxer pouca coisa,
  ajuste `item_resultado` e `proxima_pagina` para o layout real.
- Documentos que só existem em PDF são registrados com a URL do arquivo
  (`url_pdf`), sem extração do texto — falta um passo de OCR/parse de PDF.
- Não há agendamento embutido para coleta incremental periódica.
