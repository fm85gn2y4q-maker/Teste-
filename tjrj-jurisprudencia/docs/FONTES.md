# Mapa das fontes: o que cada uma entrega, e o que ela não entrega

Levantamento de julho de 2026. O ponto de partida é uma constatação: **o TJRJ
não publica API de jurisprudência.** Não há endpoint documentado, não há
dados abertos de acórdãos, não há dump. O que existe são sistemas web feitos
para consulta humana, mais uma API nacional de metadados que não contém
jurisprudência. Qualquer projeto que prometa "puxar tudo" tem que se apoiar
nessas peças e ser honesto sobre as costuras.

## 1. eJURIS — a base histórica

<https://www3.tjrj.jus.br/ejuris/ConsultarJurisprudencia.aspx>

Reúne acórdãos e decisões monocráticas oriundas do eJUD, o sistema que o
tribunal usou até a migração. É a única fonte do acervo histórico.

| | |
|---|---|
| Entrega | ementa, inteiro teor, órgão julgador, número do processo, relator, data |
| Não entrega | partes (via de regra suprimidas), composição estruturada do colegiado |
| Tecnologia | ASP.NET WebForms — `__VIEWSTATE`, `__EVENTVALIDATION`, postback |
| Busca | por ementa **e**, desde a atualização noticiada pelo tribunal, por inteiro teor |

Duas observações que mudam o desenho do coletor: a paginação exige postar o
formulário inteiro com o estado da página anterior (não é um parâmetro na
URL), e o próprio tribunal informa que a inserção retroativa de decisões
antigas no eJURIS **ainda é gradual** — ou seja, o acervo-fonte cresce para
trás, e uma varredura única de 1998 até hoje fica desatualizada no passado.
Daí a necessidade de revarredura periódica das janelas antigas, e não só do
incremento diário.

## 2. eproc — a base viva

<https://eproc1g-cp.tjrj.jus.br/eproc/> e a instalação de 2º grau

Com a implantação do eproc, a jurisprudência passou a ter **dois ambientes
separados**. A base de jurisprudência do eproc reúne as decisões incorporadas
**a partir de 05/02/2026**; o anterior permanece no eJURIS. Não há visão
unificada — o próprio tribunal oferece apenas uma página intermediária que
manda o usuário escolher entre os dois.

Consequência direta para o projeto: **são dois coletores, não um**, e a
fronteira entre eles (05/02/2026) é um parâmetro de configuração, não uma
constante enterrada no código. Processos que migraram podem aparecer nos dois
lados — daí a deduplicação por conteúdo em `models.py`.

O eproc é também a via para as **partes**, pela consulta pública processual
(`externo_controlador.php?acao=processo_consulta_publica`), que devolve
partes, assuntos, eventos e órgão julgador. Leia `JURIDICO.md` antes.

## 3. DataJud (CNJ) — metadados nacionais

<https://api-publica.datajud.cnj.jus.br/api_publica_tjrj/_search> · [wiki](https://datajud-wiki.cnj.jus.br/api-publica/)

Esta é a única API pública real, e é preciso ser claro sobre ela porque quase
toda promessa de "API de jurisprudência do TJRJ" na internet se apoia num
mal-entendido a seu respeito:

> **O DataJud não tem jurisprudência.** Ele expõe *metadados de capas
> processuais e movimentações* — classe, assuntos, órgão julgador, grau,
> datas, movimentos da Tabela Processual Unificada. Sem ementa, sem inteiro
> teor, sem nome de parte (resguardados por força da Portaria CNJ 160/2020),
> sem composição do julgamento.

O que não o torna inútil — torna-o outra coisa. Ele é o **censo**: a lista de
tudo que existe. É o que permite responder "minha base está completa?" sem
depender do próprio coletor que pode estar falhando. `tjrj auditar` usa
exatamente isso (`crawl/datajud.py`).

Detalhes técnicos que importam: autenticação por chave pública (que o CNJ
rotaciona sem aviso — trate o 401 como "vá buscar a chave nova", não como
bug), Elasticsearch com corte em 10.000 documentos por paginação comum, o
que obriga a usar `search_after`.

## 4. DJERJ — Diário da Justiça Eletrônico

<https://www3.tjrj.jus.br/consultadje/>

Publicado de segunda a sexta, com download em PDF por caderno. Contém as
publicações de acórdãos — com **partes e advogados**, que a jurisprudência
não traz — e serve como fonte de reconciliação: se um acórdão foi publicado e
não está na sua base, a lacuna é sua.

É a fonte mais chata de processar (PDF diagramado em colunas) e a mais útil
para o dado que falta. Deixe para a segunda fase.

## 5. O que foi descartado, e por quê

- **MNI (Modelo Nacional de Interoperabilidade)** — exige credencial que
  você não tem. Fora de escopo por premissa sua, e corretamente: o MNI serve
  processo, não jurisprudência.
- **Agregadores comerciais** (Jusbrasil e afins) — os termos de uso proíbem
  raspagem, e a base seria de segunda mão, sem inteiro teor confiável.
- **Google/Bing como índice** — cobertura imprevisível e proibida por ToS.

## 6. O atalho que vale tentar antes de raspar qualquer coisa

Antes de gastar semanas de coleta: **peça a base.** Um pedido pela Lei de
Acesso à Informação (Lei 12.527/2011) à Ouvidoria/e-SIC do TJRJ, invocando a
política de dados abertos do Judiciário (Resolução CNJ 215/2015), pedindo o
acervo de acórdãos em formato estruturado.

O custo é um formulário e o prazo legal de resposta. O retorno possível é o
projeto inteiro resolvido numa transferência de arquivos. Mesmo uma recusa é
útil: ela documenta que a via administrativa foi tentada, o que sustenta a
coleta pública como último recurso. Nunca vi ninguém perder por perguntar.

Um caminho intermediário, se a resposta for negativa para o dump completo:
pedir apenas **o índice** (lista de números de processo com acórdão
publicado por período). Índice não é conteúdo, tende a encontrar menos
resistência, e resolve o problema mais difícil da coleta — saber o que falta.
