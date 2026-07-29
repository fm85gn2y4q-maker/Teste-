# Arquitetura: as decisões e por quê

O `README.md` diz o que o projeto é. Este documento registra as escolhas que
não são óbvias, para que daqui a seis meses ninguém as desfaça sem saber o
que estava resolvendo.

## Escala: com o que estamos lidando

O TJRJ é um dos maiores tribunais estaduais do país. Uma estimativa de ordem
de grandeza, útil para dimensionar antes de coletar:

| | |
|---|---|
| Acórdãos e monocráticas publicados por ano | centenas de milhares |
| Acervo histórico desde ~1998 | ordem de milhões de documentos |
| Inteiro teor médio | 8–20 páginas, 20–60 KB de texto |
| Texto total, comprimido | **dezenas a poucas centenas de GB** |

Duas conclusões práticas. Primeira: cabe num disco comum, o que descarta a
tentação de montar infraestrutura distribuída antes de ter dado. Segunda:
**não cabe em nenhuma janela de contexto**, o que significa que o valor não
está em "dar o acervo à IA" e sim em dar a ela uma *busca boa* sobre o
acervo — que é o que o MCP faz.

## Por que SQLite

Porque o gargalo deste projeto é a coleta, não a consulta. Semanas de
varredura educada contra o tribunal versus milissegundos de FTS5. Trocar
SQLite por Postgres ou Elasticsearch antes de ter o primeiro milhão de
documentos coletados é otimizar a única parte que não está apertada.

FTS5 com `unicode61 remove_diacritics 2` resolve o essencial: busca em
português sem acento, BM25 para ranqueamento, `snippet()` para o trecho. E o
arquivo único faz o backup ser `cp`.

Quando trocar: se a busca semântica virar requisito. Aí o caminho é somar um
índice vetorial ao lado (embeddings por parágrafo, não por documento — um
acórdão de 20 páginas vira um vetor inútil), mantendo o BM25 como primeira
etapa e reordenando os candidatos. Híbrido, não substituição.

## Duas buscas, dois índices

`ementa_fts` e `teor_fts` são separados porque respondem perguntas
diferentes. A ementa é a tese que o tribunal já destilou; o voto é onde está
a fundamentação, com o contraditório, o distinguishing e as ressalvas. Uma
busca única sobre os dois faz o teor — muito maior — afogar a ementa no
ranqueamento, e faz a resposta perder a informação de onde a proposição veio.

O `teor_fts` indexa **por página**, não por documento. É isso que permite
devolver "consta do voto, à p. 27" em vez de "consta em algum lugar deste
PDF de 40 páginas".

## Identidade por conteúdo, não por id do tribunal

O mesmo acórdão chega várias vezes: em duas fatias que se tocam, na
republicação por erro material, no eJURIS e depois no eproc quando o processo
migra. Ids do tribunal não sobrevivem à migração entre sistemas.

Então a identidade é derivada: `sha1(numero_cnj | data | órgão | tipo)`, com
`hash_teor` do texto normalizado para pegar o caso residual — metadados
levemente diferentes, texto idêntico. Ver `models.py`.

## Julgadores como tabela

"Des. João da Silva", "JOÃO DA SILVA" e "Joao Silva" são a mesma pessoa. Sem
normalização e uma tabela `julgador` com aliases, nenhuma pergunta agregada
tem resposta confiável — nem "qual o entendimento deste relator", nem "como
esta câmara vem decidindo".

`participacao` liga julgador e acórdão com papel, `vencido`, `confianca` e
`fonte`. A confiança importa: extração por regex sobre texto de OCR não é o
mesmo fato que um campo vindo do sistema, e quem for citar precisa saber a
diferença.

## Composição por regex, LLM só na exceção

A fórmula do acórdão é padronizada em mais de 90% dos casos — "ACORDAM os
Desembargadores...", "Votaram os Desembargadores...", "vencido o
Desembargador...". Regex resolve isso a custo zero, em milhões de documentos.

Rodar um LLM sobre o acervo inteiro para extrair três nomes seria caro e
lento sem ganho proporcional. O desenho é: regex primeiro,
`precisa_revisao()` sinaliza os casos em que claramente falhou (sem relator,
ou relator sozinho num colegiado que por definição tem três votantes), e só
esses vão para o `Desambiguador` — um protocolo, não uma dependência, para
que o projeto rode sem chave de API nenhuma.

## OCR sob demanda

Acórdãos antigos, principalmente pré-2010, são digitalizações sem camada de
texto. Sem OCR eles entram na base como acórdãos vazios e somem de toda busca
por inteiro teor, silenciosamente — é a segunda maior fonte de lacuna
invisível do projeto, depois do teto de resultados.

`parse/texto.py` detecta o caso (páginas com menos de 40 caracteres),
tenta OCR se as ferramentas estiverem instaladas, e marca a origem do texto
(`pdf` / `ocr` / `pdf_sem_texto`) no banco. `cobertura_do_acervo` conta os
`pdf_sem_texto` — o problema fica visível em vez de ficar escondido.

## Ordem de construção sugerida

1. **Calibrar** o eJURIS e validar contra um dia real (`docs/CALIBRACAO.md`).
2. **Varredura só de ementas** do histórico. Rápida, e já entrega uma base
   pesquisável — valor útil antes de qualquer coisa estar completa.
3. **Inteiro teor** por cima, do mais recente para o mais antigo: os acórdãos
   dos últimos anos são os que você vai citar.
4. **eproc** e o incremento diário (uma tarefa agendada, janela dos últimos
   sete dias, que a idempotência torna segura de repetir).
5. **Auditar contra o DataJud** e tratar as lacunas encontradas.
6. **DJERJ** para partes e advogados, se e quando fizer falta.
7. **Busca semântica** por cima do BM25, se e quando fizer falta.

Os passos 6 e 7 são os que mais parecem urgentes no começo e menos são. Uma
base de ementas completa e honesta vale mais que uma base pela metade com
embeddings.
