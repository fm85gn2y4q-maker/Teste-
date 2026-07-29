# Calibração — o passo que só roda na sua máquina

## Por que este documento existe

Este projeto foi escrito num ambiente cuja política de rede **bloqueia
`tjrj.jus.br` e `api-publica.datajud.cnj.jus.br`**. Tudo que independe de ver
as páginas reais está pronto e coberto por testes: o planejador de varredura,
o esquema, a deduplicação, a extração de composição do julgamento, o
pipeline, o servidor MCP — 24 testes passando, sem rede.

O que não dá para escrever sem ver a página é o nome dos campos do formulário
do eJURIS e os seletores das linhas de resultado. Eu poderia ter chutado.
Chutar aqui é o pior resultado possível: o coletor "funciona", devolve zero
resultados, nenhum erro aparece, e a base nasce vazia. Por isso os campos não
confirmados estão como `None` e o coletor **falha alto** com `NaoCalibrado`
em vez de devolver lista vazia.

Calibrar leva uma tarde. Depois disso, o resto do sistema já está de pé.

## Passo 1 — instalar

```bash
cd tjrj-jurisprudencia
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export TJRJ_CONTATO="seu-email@exemplo.com"   # entra no User-Agent
pytest -q                                      # 24 passando, sem rede
```

## Passo 2 — fotografar as páginas reais

```bash
python -m tjrj.tools.calibrar ejuris
python -m tjrj.tools.calibrar eproc
python -m tjrj.tools.calibrar datajud
```

Cada comando salva o HTML cru em `dados/calibracao/` e imprime:

- os campos do formulário (incluindo os `__VIEWSTATE` e afins);
- todos os `<select>` com seus valores — é daqui que sai a lista de órgãos
  julgadores usada para facetar;
- os botões e seus `__EVENTTARGET`;
- os blocos HTML que mais se repetem, que são os candidatos a "linha de
  resultado".

## Passo 3 — preencher os seletores

Abra `src/tjrj/crawl/ejuris.py` e preencha `CAMPOS` e `SELETORES` com os
nomes que o passo 2 imprimiu. Idem para `PARAMS`/`SELETORES` em
`src/tjrj/crawl/eproc.py`.

Esta é, aliás, a tarefa ideal para o Claude Code na sua máquina: aponte-o
para o HTML salvo em `dados/calibracao/` e peça para preencher os
dicionários. Ele tem a página na frente; eu não tinha.

## Passo 4 — descobrir o teto de resultados

O número mais importante do projeto. Faça, pela interface web mesmo, uma
busca larga (um mês inteiro, sem filtro) e veja quantos resultados o sistema
deixa realmente paginar. Esse é o teto.

```bash
export TJRJ_TETO=<o número que você viu>
```

Se o buscador não declarar o total, use `planner.total_por_sondagem`, que
descobre o teto pedindo a última página teórica.

Errar este número para mais é o erro caro: o planejador vai achar que uma
janela cabe, o buscador vai truncar em silêncio, e a base perde acórdãos sem
nenhum sinal. Na dúvida, subestime.

## Passo 5 — validar uma janela pequena contra a tela

```bash
tjrj coletar ejuris --de 2024-03-01 --ate 2024-03-01 -v
```

Compare o número de acórdãos coletados com o que a interface web mostra para
o mesmo dia. Só depois que baterem, solte a varredura histórica.

## Passo 6 — a varredura longa

```bash
# Passe 1: só ementas. Rápido, e já dá uma base pesquisável.
tjrj coletar ejuris --de 1998-01-01 --ate 2026-02-04 --sem-teor

# Passe 2: inteiro teor. Lento, retomável, pode rodar por semanas.
tjrj coletar ejuris --de 1998-01-01 --ate 2026-02-04

# A base viva.
tjrj coletar eproc --de 2026-02-05 --ate hoje --grau 2
```

Pode interromper à vontade: cada fatia concluída fica registrada e o
reinício pula o que já terminou.

## Passo 7 — medir a cobertura, não presumir

```bash
tjrj auditar --de 2024-01-01 --ate 2024-12-31   # compara com o DataJud/CNJ
tjrj cobertura                                   # lacunas, erros, PDFs sem texto
```

Se `auditar` acusar 60% de cobertura, você tem 60% — e sabe disso, que é
melhor que ter 60% achando que tem 100%.

## Quando o parser de composição errar

Ele vai errar, em acórdãos com formatação incomum. O caminho é:

1. acrescente o texto real que falhou em `tests/test_composicao.py`;
2. ajuste a regex até o teste passar;
3. rode `tjrj reprocessar` — reextrai a composição de **todo** o acervo a
   partir do texto já baixado, sem tocar de novo no tribunal.

É para isso que serve o cache do conteúdo cru. Melhorar o parser nunca deve
custar uma recoleta.
