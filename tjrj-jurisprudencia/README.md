# Acervo de jurisprudência do TJRJ

Coletor, base e servidor MCP para a jurisprudência do Tribunal de Justiça do
Estado do Rio de Janeiro — ementa, **inteiro teor paginado**, órgão julgador,
número do processo, relator e **os demais desembargadores que participaram do
julgamento**, com quem ficou vencido.

## O que descobri antes de escrever qualquer linha

**O TJRJ não tem API de jurisprudência.** Não há endpoint, não há dados
abertos de acórdãos, não há dump. O que existe:

| Fonte | Entrega | Serve para |
|---|---|---|
| **eJURIS** (`www3.tjrj.jus.br/ejuris`) | ementa + inteiro teor, ASP.NET WebForms | acervo histórico, até 04/02/2026 |
| **eproc** (`eproc1g-cp` / `eproc2g-cp`) | ementa + inteiro teor + partes | decisões a partir de 05/02/2026 |
| **DataJud/CNJ** (API pública) | metadados de capa e movimentos | censo e auditoria de cobertura |
| **DJERJ** (diário eletrônico) | publicações com partes e advogados | reconciliação, 2ª fase |

Três consequências que moldam o projeto inteiro:

1. **São dois coletores, não um.** Desde 05/02/2026 a jurisprudência do TJRJ
   vive em dois ambientes que o próprio tribunal não unifica. A fronteira é
   configuração (`TJRJ_CORTE_EPROC`), não constante.
2. **O DataJud não tem jurisprudência** — só metadados, sem ementa, sem teor,
   sem partes. Quase toda promessa de "API de jurisprudência do TJRJ" na
   internet vive desse mal-entendido. Aqui ele tem outro papel, mais útil: é
   o censo contra o qual se **mede** a completude da base.
3. **Ninguém entrega a composição do colegiado.** Quem mais votou, quem
   presidiu, quem ficou vencido — isso está em prosa, no corpo do acórdão. É
   o dado que o projeto existe para ter, e ele é extraído (`parse/composicao.py`).

Detalhes e fontes em [`docs/FONTES.md`](docs/FONTES.md).

## O problema difícil (e a solução)

Não é fazer a requisição. É que **nenhum buscador judicial devolve mais que N
resultados por consulta.** Peça um mês com 40.000 acórdãos num sistema que
pagina até 1.000 e você recebe 1.000 — sem erro, sem aviso, sem indicação de
que faltam 39.000. É assim que quase toda base "completa" de jurisprudência
nasce incompleta sem que o dono perceba.

`crawl/planner.py` resolve por bisseção: nunca confia numa consulta cujo
total encoste no teto, parte a janela ao meio até caber, e se um único dia
ainda estourar, faceta por órgão julgador e depois por classe. Quando nem
isso resolve, **registra a lacuna explicitamente** — porque uma lacuna
anotada é um problema, e uma lacuna silenciosa é uma base mentirosa. Essas
lacunas saem depois na ferramenta `cobertura_do_acervo` do MCP, para que a IA
do outro lado nunca confunda "o TJRJ não decidiu isso" com "esse período não
está na base".

## Como está organizado

```
src/tjrj/
  config.py            parâmetros; tudo que muda de máquina
  http.py              cliente educado + cache do conteúdo CRU
  db.py                esquema SQLite + FTS5 (ementa e teor separados)
  models.py            identidade estável e deduplicação
  crawl/
    planner.py         ← bisseção de janelas; o núcleo
    base.py            contrato comum dos coletores
    ejuris.py          coletor legado (postback ASP.NET)
    eproc.py           coletor novo (1º e 2º graus)
    datajud.py         censo do CNJ + auditoria de cobertura
  parse/
    composicao.py      ← relator, vogais, presidente, vencidos
    texto.py           PDF/HTML/RTF → páginas, com OCR sob demanda
    normalize.py       nomes, órgãos, número CNJ
  pipeline/ingest.py   orquestração retomável e idempotente
  mcp/server.py        as ferramentas expostas à IA
  tools/calibrar.py    fotografa as páginas reais para calibrar seletores
```

Duas decisões que carregam o projeto:

**Guardar o cru.** Todo byte recebido vai para o cache antes de ser
interpretado. O parser vai melhorar depois que você vir os acórdãos reais, e
melhorar o parser não pode custar outra varredura de semanas —
`tjrj reprocessar` reextrai tudo a partir do que já está em disco.

**Coleta retomável e idempotente.** Cada fatia concluída vira uma linha no
banco. Interrompa quando quiser; o reinício pula o que já terminou e rodar
duas vezes não duplica nada.

## Estado atual: honesto

O ambiente onde este código foi escrito **bloqueia o acesso a `tjrj.jus.br` e
ao DataJud** por política de rede. Então:

✅ **Pronto e testado sem rede** (24 testes passando) — planejador de
varredura, esquema e índices, deduplicação, extração de composição do
julgamento, normalização, pipeline de ingestão, servidor MCP inteiro,
auditoria contra o DataJud.

⚠️ **Falta calibrar** — os nomes dos campos do formulário do eJURIS e os
seletores das linhas de resultado. Estão como `None`, e o coletor **falha
alto** (`NaoCalibrado`) em vez de devolver lista vazia. Eu poderia ter
chutado; chutar aqui produz o pior resultado possível — um coletor que
"funciona", devolve zero e enche a base de nada sem um único erro na tela.

`python -m tjrj.tools.calibrar ejuris` fotografa a página real e imprime os
campos, os selects e os blocos repetidos. É uma tarde de trabalho, e é a
tarefa ideal para o Claude Code na sua máquina, com o HTML na frente. Passo a
passo em [`docs/CALIBRACAO.md`](docs/CALIBRACAO.md).

## Uso

```bash
pip install -e ".[dev]"
export TJRJ_CONTATO="seu-email@exemplo.com"
pytest -q

python -m tjrj.tools.calibrar ejuris          # 1. calibrar
tjrj coletar ejuris --de 2024-03-01 --ate 2024-03-01 -v   # 2. validar 1 dia
tjrj coletar ejuris --de 1998-01-01 --ate 2026-02-04 --sem-teor  # 3. ementas
tjrj coletar ejuris --de 1998-01-01 --ate 2026-02-04             # 4. teor
tjrj coletar eproc  --de 2026-02-05 --ate 2026-07-29 --grau 2

tjrj auditar --de 2024-01-01 --ate 2024-12-31 # cobertura vs. DataJud
tjrj cobertura                                 # lacunas, erros, PDFs sem texto
```

## O MCP

`mcp/server.py` expõe, no mesmo padrão dos seus outros acervos (TCE-RJ,
Legis Mesquita), para que nada precise ser reaprendido:

| Ferramenta | O que faz |
|---|---|
| `pesquisar_jurisprudencia` | busca nas **ementas** — a tese destilada pelo tribunal |
| `pesquisar_inteiro_teor` | busca dentro dos **votos**, devolve a **página** |
| `obter_documento` | ficha completa + composição do julgamento |
| `ler_paginas` | inteiro teor, página a página |
| `entendimento_do_relator` | como um desembargador vem decidindo um tema |
| `cobertura_do_acervo` | o que está e o que **não** está na base |
| `search` / `fetch` | compatibilidade com conectores |

A separação entre ementa e inteiro teor é proposital: "consta da ementa" e
"consta do voto, à p. 27" têm pesos diferentes numa peça, e ferramentas
separadas obrigam a resposta a dizer de qual das duas se trata.

Ligar no Claude Code: `.mcp.json` já está na raiz. Como plugin distribuível:
`plugin/.claude-plugin/plugin.json`.

## Antes de raspar qualquer coisa

Peça a base. Um pedido via LAI (Lei 12.527/2011) ao e-SIC do TJRJ, invocando
a política de dados abertos do Judiciário (Res. CNJ 215/2015), custa um
formulário e pode resolver o projeto inteiro numa transferência de arquivos.
Se o dump completo for negado, peça só **o índice** — lista de processos com
acórdão publicado por período. Índice não é conteúdo, encontra menos
resistência, e resolve o problema mais difícil da coleta: saber o que falta.

Limites jurídicos do acervo, incluindo o tratamento das partes e o que este
projeto deliberadamente **não** faz para contornar bloqueios, em
[`docs/JURIDICO.md`](docs/JURIDICO.md).
