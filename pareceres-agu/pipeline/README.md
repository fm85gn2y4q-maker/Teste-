# Pipeline — como o acervo foi construído

Receita para reconstruir `agu_consultivo.db` do zero, na ordem em que as etapas
rodaram. Cada script é executável direto e imprime o que fez.

O banco é artefato de dados e fica fora do repositório, em
`~/Documents/AGU_Acervo_Consultivo/`. Os arquivos intermediários (`.jsonl`) são
gravados **ao lado dos scripts**, nesta pasta.

**O pipeline não roda no `.venv` do servidor.** São dependências diferentes de
propósito: o servidor MCP só precisa do `mcp` e serve o banco pronto; a
construção precisa do PyMuPDF para ler PDF. Aqui ele roda no Python do sistema,
que já tem PyMuPDF 1.28.

## Ordem

| # | Script | O que faz | Custo |
|---|---|---|---|
| 1 | `coletar.py` | colhe as três fontes → `conuni.jsonl` (1.724), `ons.jsonl` (110), `sumulas.jsonl` (86) | ~20 s |
| 2 | `baixar.py` | baixa os 609 inteiros teores públicos | ~9 min, 484 MB |
| 3 | `indexar.py` | monta o banco: documentos, páginas, FTS, citações, tesauro e cobertura | ~2 min |

Módulos de apoio, importados pelos acima: `fontes.py` (os três clientes),
`autoridade.py` (a régua de vinculação), `referencias.py` (extração de citações).

## As três fontes, e por que três

Não há uma base única da AGU. O acervo consultivo público está em três lugares
com três formatos:

**CONUNI** — a consulta pública das manifestações de uniformização. O catálogo
inteiro vem numa requisição (`script=53, base=1`), sem paginação: 1.724
registros, 3,7 MB. Traz o que mais importa e o que nenhuma outra fonte dá: a
`natureza`, que é o alcance declarado da manifestação.

**Orientações Normativas** — uma página só, com um cartão por ON.

**Súmulas** — uma página só, texto corrido, 86 verbetes desde 1997.

## Quatro coisas que custaram caro

**1. A situação do ato está no título, não no enunciado.** As ONs canceladas,
revogadas e com nova redação vêm com o corpo VAZIO e a informação entre
parênteses no título: "(cancelada)", "(revogada)", "(nova redação na ON
77/2023)". Um parser que lesse só o corpo produziria sete ONs sem texto e sem
explicação — e, pior, sem a ressalva que impede citá-las.

**2. O cabeçalho das súmulas não é uniforme.** "SÚMULA Nº 49, DE 20 DE ABRIL DE
2010" convive com "SÚMULA Nº 50, 13 DE AGOSTO DE 2010", sem o "DE". Exigir o
"DE" perdia as súmulas 50 e 51 **em silêncio** — 84 em vez de 86, e nada no
resultado avisava. Por isso o teste verifica que a numeração vai de 1 ao máximo
sem buraco.

**3. As ONs da extinta CNU estão todas dentro de um único cartão**, sob o
título "Possuem a mesma eficácia das ONs acima". São sete atos normativos, com
revogações próprias, que um parser ingênuo trata como um documento só.

**4. Um cartão da página da AGU perdeu o número.** Entre a ON 94/2024 e a
96/2025 há um cartão cujo título é apenas "Fundamentação". O número foi
inferido pela posição e o registro vai marcado com `numero_inferido` e um aviso
explícito — não se inventa número de ato normativo em silêncio.

## O que não foi possível

**1.115 manifestações do CONUNI não têm arquivo público.** Apontam para
`sapiens.agu.gov.br/valida_publico?id=…`, que redireciona para o SuperSapiens e
cai na tela de login. Foram testadas as rotas de API prováveis e o proxy do
próprio site da CGU: não há caminho anônimo. Não se tentou contornar
autenticação; o número entra na cobertura.

**369 dos 609 PDFs baixados são digitalização sem camada de texto**, entre 2010
e 2014. Precisariam de OCR em português. Há Tesseract 5.4 nesta máquina, em
`C:\Program Files\Tesseract-OCR`, mas só com `eng` e `osd` — falta
`por.traineddata`.

## Coleta educada

A etapa 1 faz 3 requisições; a etapa 2, 609, com 4 conexões simultâneas e pausa
entre elas. É acervo público, mas o servidor é da AGU — não varra sem
necessidade e não aumente a concorrência.
