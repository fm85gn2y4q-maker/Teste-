# Pesquisa Textual do TCE-RJ — formato da API

Nota técnica. O `PONTO_DE_PARTIDA.md` registrava a Pesquisa Textual como
"mapeada mas não coletada — vive num iframe, exige termo de busca e devolve
`quantidadeTotal: 10000` fixo". Duas dessas três afirmações não se sustentaram
quando fui medir. Este documento registra o formato da requisição, o que foi
verificado e o que não foi.

Levantado em 01/08/2026 a partir do bundle da **Consulta de Acórdãos**
(`/consulta-acordaos/`, chunk `330-es2015.*.js`, onde está o DTO), com cada
afirmação confirmada contra o servidor.

---

## 1. O endpoint

```
POST https://www.tcerj.tc.br/liana-pesquisa-externo/api/pesquisatextual/acordao/pagina/{pagina}/tamanhoPagina/{tamanho}
Content-Type: application/json
```

Corpo — é a classe `x` do bundle, com todos os campos presentes mesmo vazios:

```json
{
  "comTodasAsPalavras": "",
  "interessado": "",
  "dataCadIni": "", "dataCadFim": "",
  "dataSessaoIni": "", "dataSessaoFim": "",
  "naturezas": [], "naturezasExcluidas": [],
  "retornaTextoDocumento": false,
  "pagina": 1, "quantidadePorPagina": 20
}
```

O formulário acrescenta, quando preenchidos: `enteFederativoId`,
`orgaoOrigemId`, `relatorId`, `esferaId`, `idTipoGrupoNatureza`.

A página e o tamanho aparecem **duas vezes** — no caminho da URL e no corpo.
Mandei os dois iguais e funcionou; não testei divergentes.

Enviei `Origin` e `Referer` de `www.tcerj.tc.br`. Não testei sem eles.

### Operadores

Vão dentro de `comTodasAsPalavras`. Extraídos dos handlers dos botões da
interface (`onClickBotaoE`, `onClickBotaoOu`, `onClickBotaoNao`,
`onClickBotaoExpressaoExata`):

| Operador | Efeito |
|---|---|
| ` E ` | conjunção |
| ` OU ` | disjunção |
| ` -- ` | exclusão |
| `"..."` | expressão exata |

## 2. A resposta

```
{ quantidadeTotal, quantidadePaginas, paginaAtual, mensagemRetorno, resultados[] }
```

Cada item de `resultados`:

| Campo | Conteúdo |
|---|---|
| `numero`, `dv`, `ano` | processo (ex.: 247443-5/2025) |
| `numeroAcordao`, `anoAcordao` | **a chave para baixar o inteiro teor** |
| `titulo` | processo + natureza, com os termos em `<mark class="highlight">` |
| `interessado`, `orgao`, `observacao` | partes e objeto |
| `idRelatorSessao` | relator da sessão |
| `natureza` | veio `null` em todos os casos que vi — a natureza está no `titulo` e no PDF |
| `resultados[]` (aninhado) | trecho com destaque, `guidDocumento`, `dataDocumento`, `categoria`, `sigiloso` |

## 3. Duas medições que mudam o que dá para fazer

**O `quantidadeTotal: 10000` é teto, não valor fixo.** Consultas estreitas
devolvem o número verdadeiro:

| Consulta | `quantidadeTotal` |
|---|---|
| `licitação`, sem outro filtro | 10000 — no teto |
| `"pregão eletrônico"` (exata) | 4.247 |
| `enteFederativoId=93` (Mesquita) | 545 |
| Mesquita + `licitação` | 61 |
| Mesquita + `licitação` + sessões de 2024 | 22 |

Consequência: o teto se contorna **fatiando** — por município, por natureza,
por intervalo de sessão. A coleta seletiva por tema, que a API de acórdãos por
número/ano não permite (o metadado dela não tem ementa nem natureza), é viável
por aqui.

**O `quantidadePaginas` mente — devolve sempre `1`.** Não use para saber
quando parar; calcule a partir de `quantidadeTotal`. A paginação real funciona:
pedi as páginas 1, 2 e 6 do conjunto de Mesquita (545 registros) e vieram
acórdãos distintos, sem sobreposição entre elas.

> Nos dois casos o campo existia e trazia um número plausível. Foi preciso
> pedir de novo, com filtro mais estreito e em outra página, para descobrir
> que um era limite e o outro era constante.

## 4. Catálogos para montar os filtros

Base `https://www.tcerj.tc.br/scap-webapi-externo/api/`:

| Rota | Conteúdo |
|---|---|
| `municipio` | 92 municípios — **Mesquita = 93** |
| `grupoNatureza` | 375 grupos, com `idTipoGrupoNatureza` (1 DOCUMENTO, 2 EXTERNO, 3 INTERNO, 4 EXTINTO, 5 DOCUMENTO INTERNO) |
| `natureza/tipo/{idTipoGrupoNatureza}` | naturezas do tipo (298 no tipo 2) |
| `orgao/ativos?idMunicipio={id}` | órgãos do município |
| `usuario/conselheiro/ativos` | relatores |

Grupos de natureza que interessam a licitações e contratos: `ATO DE DISPENSA
DE LICITAÇÃO` (2), `ATO DE INEXIGIBILIDADE DE LICITAÇÃO` (3), `EDITAL DE
LICITAÇÃO` (11), `EDITAL DE PREGÃO` (314), `CONTRATO` (8), `CONVÊNIO` (9),
`OBRAS / INSTALAÇÕES` (120).

## 5. Do resultado ao inteiro teor

```
resultado.numeroAcordao / .anoAcordao
  → GET documento-webapi-externo/api/documento/acordao/{numero}/{ano}?votoInteiro=true
  → PDF
```

É o **mesmo padrão de URL já gravado** na coluna `url` de
`documentos_oficiais`. O coletor já sabe baixar; o que faltava era uma fonte de
números além da lista curada.

Verificado ponta a ponta: primeiro resultado de Mesquita → acórdão
**20698/2026**, processo 247443-5/2025, MesquitaPrev, PDF de 3 páginas que abre
e extrai texto.

## 6. O teto da curadoria, medido

Complemento à lição 3 (a base é *Jurisprudência Selecionada*, não o Tribunal
inteiro). A rota `atos-plenario-webapi-externo/api/acordaos/{numero}/{ano}`
alcança acórdãos fora da curadoria: de 25 números de 2023 ausentes de
`documentos_oficiais`, **22 existem**, todos com `documentoDisponivel: true`, e
16 deles são MUNICIPAL. Densidade da numeração medida em três faixas de 2023:
29 de 36 sorteios. Com teto de numeração em 128.583, isso põe 2023 na ordem de
**100 mil acórdãos** — cerca de 400× os 250 curados daquele ano.

Duas limitações dessa rota, que é por isso que a Pesquisa Textual é o caminho
e não ela:

- o metadado é cego ao tema — devolve só `numeroAcordaoCompleto`,
  `dataAcordao`, `numeroProcessoCompleto`, `relator`, `relatorSigla`,
  `tipoProcesso`, `documentoDisponivel`. Sem ementa, sem natureza;
- a listagem paginada (`acordaos?RelatorSigla=&TipoProcesso=&DataSessaoInicial=
  &DataSessaoFinal=&PaginaAtual=&RegistrosPorPagina=`), que o bundle monta,
  devolve **404** em todas as combinações testadas, com e sem filtros, com
  `Referer`. Respondem apenas as rotas por número/ano, `relatores` e
  `tipos-processo`.

## 7. O que NÃO foi verificado

- **`retornaTextoDocumento: true`.** Se devolver o texto do documento na
  própria resposta, dispensa baixar PDF para triagem. É hipótese.
- **Se `esferaId` e `idTipoGrupoNatureza` filtram de fato.** Apareceram no DTO
  do formulário; testei apenas `enteFederativoId`, `comTodasAsPalavras` e o
  intervalo de sessão.
- **Comportamento sem `Origin`/`Referer`.**
- **Se o teto de 10.000 é por consulta ou por sessão.**
- **A que universo a Pesquisa Textual responde** — se ao acervo integral do
  Tribunal ou a um subconjunto próprio. Os 545 de Mesquita não foram
  confrontados com nenhuma contagem oficial independente.

## 8. Se esta coleta for adiante

**A lição 1 fica mais crítica, não menos.** Hoje a curadoria do Serviço de
Jurisprudência funciona como filtro de qualidade: o que entra já foi
selecionado como tese. Sem ela, entram no acervo acórdãos de matéria puramente
formal e milhares de páginas de alegações de defesa, instrução técnica e
parecer do MPC — que a busca não distingue do voto, e que atribuídos à Corte
invertem o precedente.

**O recorte municipal é o ganho real.** `enteFederativoId` isola o controle
externo sobre um município determinado. Para quem atua em procuradoria
municipal, isso não é precedente persuasivo de outra jurisdição — é o Tribunal
julgando o próprio jurisdicionado.

**Coleta educada.** Todas as medições acima couberam em menos de 150
requisições, com pausa entre elas. Uma coleta ampla precisa do mesmo cuidado: o
universo é de centenas de milhares de documentos, e varrê-lo sem filtro não é
uma opção defensável.
