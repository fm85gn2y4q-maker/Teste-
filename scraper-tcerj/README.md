# Coletor e servidor MCP do TCE-RJ

Baixa e organiza dois acervos do Tribunal de Contas do Estado do Rio de
Janeiro, e os serve a assistentes de IA pelo protocolo MCP:

| | |
|---|---|
| **Jurisprudência** | 1.671 ementas e o inteiro teor de **25.561 acórdãos** e **555 respostas a consulta** — 576.741 páginas |
| **Normas** | **973 atos** — deliberações, resoluções, atos normativos, portarias, notas técnicas e o Regimento Interno |

Bancos SQLite com busca textual, exportáveis para JSONL e CSV. O coletor das
normas fica em **`../normas-tcerj/`**; o servidor, aqui, serve os dois.

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
- **Deliberações e Resoluções ficam no mesmo domínio**, no Portal de Normas e
  Publicações — não em `atosoficiais.com.br`, para onde um menu redireciona.
  São 973 atos numa API REST limpa (`/cadastro-publicacoes-webapi/api/{Especie}`),
  coletados por `normas-tcerj/` e servidos pelo mesmo servidor MCP. Ver a seção
  **Acervo normativo**, adiante.

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

São 174. Os testes de integração sobem um portal falso em `localhost` e o
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

São **17 ferramentas**, e elas se dividem por acervo porque as duas perguntas
perigosas são diferentes — na jurisprudência, *de quem é este trecho*; nas
normas, *isto ainda vale*:

```
JURISPRUDÊNCIA
  pesquisar_jurisprudencia   busca nas ementas
  pesquisar_inteiro_teor     busca nos votos, devolve a página
  panorama_do_tema           quantos acórdãos existem, por ano, quanto ficou por ler
  sumulas_sobre              súmula antes de acórdão; sem casamento, devolve as 28
  ler_paginas                páginas contíguas, com expansão adiante
  obter_documento / listar_documentos

NORMAS
  pesquisar_normas           busca nas ementas dos atos
  pesquisar_dispositivos     busca no texto, devolve a página
  notas_tecnicas_sobre       orientação do TCE; sem casamento, devolve as 10
  situacao_do_ato            vigente | revogado | revogado_tacitamente
  historico_do_ato           o que revogou e o que o alterou
  ler_norma / listar_normas

COMUNS
  cobertura_do_acervo        volumes, período e limites dos dois
  search / fetch             formato que a pesquisa profunda do ChatGPT exige
```

O acervo normativo é **opcional**: sem o banco dele, o servidor sobe com as dez
ferramentas de jurisprudência e registra o motivo no log. Um acervo acessório
ausente não derruba o principal.

### A Nota Técnica atravessa os dois acervos

Ela é coletada com as normas, porque é ali que o portal a publica. Mas
funcionalmente está mais perto do precedente: é **orientação** do Tribunal aos
jurisdicionados, sem força normativa própria — não obriga por si, e revela o
entendimento com que a fiscalização vai medir.

Deixá-la só do lado das normas a escondia de quem pergunta pela via da
jurisprudência, e o caso que mostrou isso é exemplar — inclusive no que ele
**não** prova. As Respostas a Consulta 74/2018 (uniformes escolares) e 83/2018
(metodologia de aferição do MDE) foram ambas revogadas pelo item III do voto no
Processo 100.614-0/22, sessão de 13/04/2022. A Nota Técnica nº 5/2022 é da mesma
sessão e trata da metodologia de apuração do art. 212 com o FUNDEB.

Que a nota substituiu a orientação sobre **metodologia** é inferência forte: o
tema casa quase literalmente com a 83/2018. Que ela responda sobre **uniforme**
não está provado — a nota não menciona a palavra, e o voto que revogou não está
no acervo. Escrevi as duas coisas como se fossem uma só na primeira versão
deste texto; o campo entrega a coincidência de data e tema, e quem lê decide se
ela se sustenta.

Por isso toda busca de jurisprudência traz `notas_tecnicas_sobre_a_materia`, e
há `notas_tecnicas_sobre` para consulta direta.

**O campo é lembrete, não filtro** — e vale saber disso. As ementas das notas
falam em "metodologia", "repercussão", "capitalização"; ninguém pergunta assim.
Na prática a busca literal quase nunca casa, e o campo cai no aviso de que há
dez notas por conferir. A ferramenta dedicada então **devolve as dez**: com
universo desse tamanho, ler vence ranquear.


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

Nenhum dos quatro endpoints devolve `url`, `url_pdf` ou órgão julgador: os
campos não existem no payload. Os endereços de conferência que o servidor
apresenta são **montados** a partir do número e do ano, contra endpoints
levantados à mão no portal — não vêm da listagem.

Os acórdãos não trazem data de publicação (só a data do voto); as súmulas não
têm processo nem relator, o que é correto.

## Pesquisa Textual — coletada

É a base do **inteiro teor**, e era a mais valiosa que faltava. Hoje responde
por **24.518 dos 25.561 acórdãos** com texto no acervo.

O formulário vive num *iframe* (`/pesquisa-textual/app`), razão pela qual
`descobrir` não o enxergava: ele inspeciona apenas o quadro principal. O
formato do POST, os operadores e os catálogos estão em
**`PESQUISA_TEXTUAL_API.md`**.

Três coisas que a coleta precisou resolver, e que o pipeline comum não fazia:

1. **A lista é aninhada.** O item externo é o *processo*; os documentos ficam um
   nível abaixo.
2. **O servidor injeta marcação de destaque** em torno de cada ocorrência do
   termo, inclusive dentro de palavras (`DECISÃO` volta como
   `<mark>DE</mark>CISÃO`).
3. **O `numero` do registro é o do processo**, não o do documento. Usar a lista
   de apelidos comum produziria citações falsas.

E duas armadilhas que só aparecem no uso:

- **As aspas da expressão exata precisam chegar intactas ao servidor.** Passadas
  pela linha de comando, o shell as come, a busca vira palavras soltas e
  "contratação de pessoal por prazo determinado" entra como se fosse licitação.
  Foram 5.143 acórdãos do tema errado, descartados antes de qualquer download.
  Por isso as expressões ficam em Python.
- **O teto de 10.000 por consulta é real.** `"termo aditivo"` bateu nele, e esse
  recorte permanece incompleto. Contorna-se fatiando por ano ou município.

## Respostas a Consulta — inteiro teor e vigência

A espécie tem peso próprio: é o que o Tribunal responde a quem pergunta **em
tese**, e vale como orientação, não como precedente de caso concreto.

```bash
python -m tcerj -c config.json inteiro-teor-consultas
```

**555 das 572** com texto, 4.704 páginas. O `arquivoId` já vinha no payload da
listagem desde a coleta original — o PDF sempre esteve a uma requisição de
distância, pelo mesmo endpoint `api/file/{id}` que o acervo normativo usa.

Duas coisas que a listagem guardava e ninguém lia:

- **A resposta a consulta pode ser REVOGADA.** Sete estão, e a justificativa às
  vezes declara revogar uma *tese do Prejulgado*, numerada. O servidor devolve
  `revogacao` e `aviso_vigencia` em cada resultado atingido.
- **16 são PDF escaneado**, sem camada de texto — imagem pura, de 2018, 2020 e
  2024. Não é falha da coleta; extrair exigiria OCR.

## Acervo normativo — deliberações, resoluções e o Regimento

Coletor em **`../normas-tcerj/`**, banco próprio, servido pelo mesmo processo
MCP. **973 atos, 1975–2026, 5.042 páginas.**

```bash
python -m normas coletar    # metadados e o grafo de revogação
python -m normas textos     # os PDFs, um por vez
python -m normas relacoes   # alterações e revogações tácitas da prosa da ementa
```

A fonte entrega o **grafo de revogação pronto**: cada ato declara por quem foi
revogado e o que revogou. Num acervo de normas a vigência é o risco central, e
aqui ela é metadado oficial — não inferência sobre o texto.

Duas coisas que a coleta descobriu e que mudam o desenho:

- **Número de ato não é chave.** A numeração recicla a cada ano: as 26 portarias
  usam 11 números. O portal oferece download em lote por espécie, mas nomeia os
  arquivos só pelo número — casar por ele pendura o texto no ato do ano errado,
  sem erro e sem aviso. A coleta baixa um arquivo por vez, por `arquivoId`.
- **Não existe texto consolidado.** Todo PDF é a redação original; alteração
  posterior é ato autônomo. Vale para o Regimento Interno: o que o portal serve
  é a Deliberação 338/2023, alterada pelas 341/2023 e 347/2024.

A **Lei Orgânica** (Lei Complementar estadual nº 63/1990) não está aqui: é lei
da ALERJ, não ato do Tribunal.

## Limitações conhecidas

- A pontuação de `descobrir` premia vocabulário jurídico e tamanho da lista,
  então pode eleger uma base menor: as quatro legítimas aparecem no topo, mas a
  escolha ainda merece revisão humana, como a saída do comando avisa.
- Os seletores padrão são genéricos. Se o modo `navegador` trouxer pouca coisa,
  ajuste `item_resultado` e `proxima_pagina` para o layout real.
- O texto dos PDFs é extraído por PyMuPDF, página a página, e há remoção de
  moldura repetida. Não há OCR: PDF sem camada de texto entra como
  `sem_texto` — no acervo atual isso não ocorreu.
- Não há agendamento embutido para coleta incremental periódica.
