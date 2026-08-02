# Ponto de partida

Briefing para uma sessão nova que vá continuar este trabalho. Diz o que já
existe, onde está, o que está publicado e o que **não** refazer.

Leia isto primeiro. Depois, conforme a tarefa: `METODO.md` (como foi feito e
por quê), `README.md` (o coletor), `HOSPEDAGEM.md` (deploy),
`TESTE_ACEITACAO_v2.md` (como se avalia o comportamento).

---

## O que é

Coletor e servidor MCP da jurisprudência do **TCE-RJ**. O usuário é advogado
que atua em Direito Administrativo, licitações e contratos, com foco no Rio de
Janeiro. O acervo serve para pesquisar precedente e **citar em peça** — daí a
insistência em página, link de conferência e proveniência.

## Onde está

```
C:\Users\Matheus Menegatti\projetos\Teste-\scraper-tcerj
```

Branch: `claude/tce-rj-jurisprudencia-scraping-r2oi6p`
Repositório: `github.com/fm85gn2y4q-maker/Teste-` (público)

Ambiente pronto em `.venv` (Python 3.12, Playwright com Chromium, PyMuPDF, MCP).

```bash
.\.venv\Scripts\python.exe -m pytest -q
```

150 testes. Rodam em ~1 min (7 sobem Chromium contra um portal falso local).

## O que já foi coletado — NÃO refazer

| | |
|---|---|
| Ementas | **1.671** (1.067 acórdãos, 572 respostas a consulta, 28 súmulas, 4 questões de ordem) |
| Acórdãos com inteiro teor | **1.042** |
| Páginas de voto | **16.343** (35,4 milhões de caracteres) |

Banco: `dados\tcerj.sqlite` (81,3 MB) — **fora do Git**, é artefato de dados.

Coletar tudo de novo leva ~1h e bate 1.064 vezes no servidor do Tribunal. A
coleta é incremental: `inteiro-teor` só busca o que falta. Não force.

Três pendências, registradas como estado e não como erro: 1 acórdão cujo PDF o
Tribunal não publica (404) e 2 ementas sem número de acórdão. A rotina
incremental as reteta sozinha.

## O que está publicado

**Serviço em produção (Render, plano gratuito):**

```
https://ementario-tcerj.onrender.com/mcp
```

Conectado como conector personalizado no Claude e no ChatGPT, sem
autenticação. Dorme após ~15 min parado; a primeira consulta seguinte demora
perto de um minuto.

**Acervo como asset de release:**

```
tag acervo-v2.0.0 → ementario-tcerj-v2.0.0.db.gz (24,0 MB)
sha256 513fd3146272d98a71dfa8b98aba5ce27b6262ce2f260360cbd0e2d135bab395
```

O `Dockerfile` baixa esse arquivo na construção e confere o hash. Publicar
acervo novo = gerar `.gz`, criar release nova, trocar duas linhas no
`Dockerfile` (ARG `ACERVO_URL` e `ACERVO_SHA256`), enviar.

**Extensão local** (`.mcpb`) instalada no Claude Desktop, gerada por
`empacotar_mcpb.py`. Contém uma cópia do acervo e roda por stdio.

## Ferramentas que o servidor expõe

```
pesquisar_jurisprudencia   busca nas ementas
pesquisar_inteiro_teor     busca dentro dos votos, devolve a página
ler_paginas                lê páginas contíguas, com expansão adiante
obter_documento            ementa completa
listar_documentos          varredura por espécie/ano/relator
cobertura_do_acervo        volumes, período, limites
search / fetch             fachadas para a pesquisa profunda do ChatGPT
```

## Três coisas que custaram caro e não devem se perder

**1. Proveniência.** O PDF do acórdão reúne, no mesmo texto, a decisão
colegiada, o relatório, as **alegações de defesa**, a instrução técnica, o
parecer do MPC, precedentes transcritos e o voto. Para a busca são caracteres
iguais. Um trecho de defesa apresentado como entendimento do Tribunal **inverte
o precedente**. As instruções do servidor obrigam a verificar de onde vem o
trecho antes de atribuí-lo à Corte.

**2. Identidade.** Um acórdão rende mais de uma ementa selecionada — teses
distintas do mesmo julgamento. Espécie + número + ano **não** é chave única. As
páginas pertencem ao documento oficial (`acordao-58739-2023`), não ao registro
de ementa.

**3. Curadoria.** A base de acórdãos é a *Jurisprudência Selecionada*, não
todos os acórdãos do Tribunal. Ausência aqui não prova que a tese não existe.

## Armadilhas conhecidas

**Cache do conector.** Ao mudar ferramentas ou instruções, o Claude e o ChatGPT
continuam com a versão antiga. Desligar e religar não basta — é preciso
**remover e recriar** o conector. Confirme com `cobertura_do_acervo`: tem de
vir **1.042 documentos com inteiro teor**.

**Python 3.13 quebrado nesta máquina.** Falta `html/entities.py`, `difflib` e
`_curses`. A extensão `.mcpb` foi fixada no Python 3.12 por causa disso. Se for
mexer nisso, o conserto é reparar a instalação do 3.13.

**Espaços no caminho.** O Claude Desktop parte o `command` do manifesto no
primeiro espaço. O empacotador converte para o nome curto 8.3 automaticamente.

**Erro de processamento não se conserta rebaixando.** Se a extração ou a
limpeza tiver defeito, use `reparar-inteiro-teor`, que refaz sobre o material
guardado.

## O que estava em aberto

**Base de doutrina e pareceres.** Levantamento já feito: ~8.000 documentos e
28 GB no perfil do usuário; a biblioteca fica em
`~\OneDrive\Documentos\Livros`. Das 11 obras de licitações medidas, 8 têm texto
aproveitável e 3 são digitalização sem OCR. **O Marçal Justen Filho sobre a
14.133 (1.825 páginas) tem OCR degradado — 58% contra 71–87% das demais.**
Transcrever dali produziria citação falsa.

Requisito do usuário: transcrever o trecho literal, com **página**, e citar em
**ABNT**. Isso exige ficha bibliográfica por obra, que não se extrai do PDF de
forma confiável.

**Pareceres da PGE/PGM:** estão em algum lugar do perfil do usuário; a busca
foi interrompida antes de localizá-los.

**Pesquisa Textual do TCE-RJ** (inteiro teor de decisões monocráticas e outras
peças) foi mapeada mas não coletada — vive num iframe, exige termo de busca e
devolve `quantidadeTotal: 10000` fixo. Ver `README.md`.

**Segunda rodada de testes de aceitação** deixou duas pendências: a leitura
além da página ainda não é reflexo, e os casos-armadilha (Acórdãos 54691/2025 e
6930/2025) não apareceram no ranqueamento.

## Como o usuário trabalha

Delega execução, mas julga desenho — e julga bem. Rejeitou embeddings três
vezes com razão técnica, e cada rejeição se confirmou. Quer saber o que **não**
foi verificado, e trata hipótese reprovada como resultado.

Verifique antes de afirmar. Meça antes de otimizar. E quando ele ler material
bruto, escute: a descoberta mais importante deste projeto veio daí.
