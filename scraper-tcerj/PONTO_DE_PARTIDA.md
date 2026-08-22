# Ponto de partida

Briefing para uma sessão nova que vá continuar este trabalho. Diz o que já
existe, onde está, o que está publicado e o que **não** refazer.

Leia isto primeiro. Depois, conforme a tarefa: `METODO.md` (como foi feito e
por quê), `README.md` (o coletor), `HOSPEDAGEM.md` (deploy),
`PESQUISA_TEXTUAL_API.md` (a API que trouxe 24 mil acórdãos),
`TESTE_ACEITACAO_v2.md` (como se avalia o comportamento).

---

## O que é

Coletor e servidor MCP de **dois acervos do TCE-RJ**, servidos pelo mesmo
processo:

| | |
|---|---|
| **Jurisprudência** | ementas e súmulas, mais o inteiro teor dos acórdãos e das respostas a consulta |
| **Normas** | deliberações, resoluções, atos normativos, portarias e notas técnicas do Tribunal, inclusive o Regimento Interno |

O usuário é advogado que atua em Direito Administrativo, licitações e
contratos, com foco no Rio de Janeiro, e é Procurador do Município de Mesquita.
O acervo serve para pesquisar e **citar em peça** — daí a insistência em
página, link de conferência, proveniência e vigência.

## Onde está

```
projetos\Teste-\scraper-tcerj    jurisprudência + servidor MCP dos dois acervos
projetos\Teste-\normas-tcerj     coletor das normas
```

Branch: `claude/tce-rj-jurisprudencia-scraping-r2oi6p`
Repositório: `github.com/fm85gn2y4q-maker/Teste-` (público)

Ambiente pronto em `scraper-tcerj\.venv`. O coletor de normas roda com o mesmo
interpretador.

```bash
.\.venv\Scripts\python.exe -m pytest -q
```

**174 testes**, alguns minutos (parte sobe Chromium contra um portal falso).

## O que já foi coletado — NÃO refazer

### Jurisprudência

| | |
|---|---|
| Ementas | **1.671** (1.067 acórdãos, 572 respostas a consulta, 28 súmulas, 4 questões de ordem) |
| Acórdãos com inteiro teor | **25.561** |
| Respostas a Consulta com inteiro teor | **555** de 572 |
| Páginas | **576.741** (1,32 bilhão de caracteres) |
| Período do corpus textual dos acórdãos | **2021–2026**, nas duas origens |

**Resposta a Consulta tem inteiro teor desde 05/08/2026.** O `arquivoId`
sempre esteve no payload guardado; o acervo declarava "só acórdãos têm inteiro
teor" por omissão, não por impedimento. São 4.704 páginas, ~10 por documento.

Das 17 que faltam, **16 são PDF escaneado** — imagem, sem camada de texto,
espalhadas por 2018, 2020 e 2024. Extrair exigiria OCR. Uma não tem arquivo na
listagem.

**Resposta a Consulta pode ser REVOGADA**, e sete estão: 522/2025, 350/2022,
293/2021, 179/2020, 42/2019, 74/2018 e 83/2018. A listagem traz `revogada`,
`revogadaParcialmente` e a justificativa — que às vezes diz revogar uma *tese
do Prejulgado*, numerada. O campo ficou anos sem ser lido.

Banco: `scraper-tcerj\dados\tcerj.sqlite` (**2,8 GB**) — fora do Git.

**Duas origens, e elas não têm o mesmo peso:**

```
 1.043   Jurisprudência Selecionada — curadoria do Serviço de Jurisprudência
24.518   Pesquisa Textual — acórdãos reais, sem ementa oficial nem aval
```

Todo resultado declara `na_jurisprudencia_selecionada`. Antes da expansão o
campo não teria valor informativo — é a ampliação que o cria.

Os 24.518 vieram de **doze expressões exatas** de licitações e contratos:
dispensa de licitação, inexigibilidade, pregão eletrônico, projeto básico,
capacidade técnica, equilíbrio econômico-financeiro, fiscal do contrato, termo
aditivo, sobrepreço, superfaturamento, jogo de planilha, notória
especialização. `"termo aditivo"` bateu o teto de 10.000 — **esse recorte está
incompleto**.

Coleta completa: ~21 h e 25 mil requisições. É incremental; não force.

50 pendências (0,2%): 45 acórdãos do bloco 46.959–46.999/2022 que a origem
recusa com `400 Bad Request` de forma reprodutível, 3 sem publicação, 2 ementas
cujo acórdão ainda não saiu.

### Normas

| espécie | atos | revogados | período |
|---|---|---|---|
| Resolução | 366 | 62 | 1975–2024 |
| Deliberação | 273 | 102 | 1975–2024 |
| Ato Normativo | 270 | 91 | 1980–2024 |
| Súmula | 28 | — | 2018–2026 |
| Portaria | 26 | 2 | 2019–2024 |
| Nota Técnica | 10 | — | 2020–2025 |

**973 atos, 5.042 páginas, 22 MB.** Banco:
`normas-tcerj\dados\normas-tcerj.sqlite`.

```bash
python -m normas coletar && python -m normas textos && python -m normas relacoes
```

~25 min. O grafo de revogação vem pronto da fonte — 257 relações declaradas
pelo próprio Tribunal, mais 16 revogações tácitas mineradas da prosa da ementa.

## O que está publicado

```
https://ementario-tcerj.onrender.com/mcp
```

Render, plano gratuito, sem autenticação. Conectado no Claude e no ChatGPT.
Hiberna após ~15 min; a consulta seguinte demora perto de um minuto.

**O plano gratuito aguenta os 2,7 GB.** Isso foi testado, não deduzido. Houve
uma recomendação errada de migrar para VPS ou plano pago, e ela vinha de
confundir **disco persistente** — vedado no gratuito — com **dado dentro da
imagem**, que é o que este projeto usa. O filesystem efêmero basta porque nada
é escrito.

**Acervos como assets de release:**

```
acervo-v3.0.0 → ementario-tcerj-v3.0.0.db.gz (641 MB)
  sha256 1e1c287b378285b45e79d1ea1d8f9e0eeafd788b8fcfe47b12d58657295814db

normas-v1.0.0 → normas-tcerj-v1.0.0.db.gz (6,8 MB)
  sha256 d88998db7d8d7fe2f9304900c16f9847a5897705639b4429448bfdf61a3538c4
```

O `Dockerfile` baixa os dois na construção e confere os hashes. Publicar acervo
novo = gerar `.gz`, criar release, trocar as linhas `ARG` correspondentes.

## Ferramentas que o servidor expõe

```
JURISPRUDÊNCIA
  pesquisar_jurisprudencia   busca nas ementas
  pesquisar_inteiro_teor     busca nos votos, devolve a página
  panorama_do_tema           quantos acórdãos existem, por ano, quanto ficou por ler
  sumulas_sobre              súmula antes de acórdão; sem casamento, devolve as 28
  ler_paginas                páginas contíguas, com expansão adiante
  obter_documento            ementa completa
  listar_documentos          varredura por espécie/ano/relator

NORMAS
  pesquisar_normas           busca nas ementas dos atos
  pesquisar_dispositivos     busca no texto, devolve a página
  notas_tecnicas_sobre       orientação do TCE; sem casamento, devolve as 10
  situacao_do_ato            vigente | revogado | revogado_tacitamente
  historico_do_ato           o que revogou e o que o alterou
  ler_norma                  páginas contíguas
  listar_normas              por espécie, ano ou vigência

COMUNS
  cobertura_do_acervo        volumes, período e limites dos dois
  search / fetch             fachadas para a pesquisa profunda do ChatGPT
```

**A Nota Técnica atravessa os dois acervos.** É coletada com as normas, porque
é ali que o portal a publica, mas funcionalmente está mais perto do precedente:
é orientação, sem força normativa própria. Por isso toda busca de jurisprudência
traz `notas_tecnicas_sobre_a_materia`. O caso que exigiu isso: a Resposta a
Consulta 74/2018 foi revogada na sessão de 13/04/2022 e a **Nota Técnica nº
5/2022**, publicada na MESMA sessão, é o que ficou no lugar.

O campo é lembrete, não filtro — as ementas das notas usam vocabulário que
ninguém digita ("metodologia", "repercussão"), e a busca literal quase nunca
casa. Nesse caso ele aponta para `notas_tecnicas_sobre`, que devolve as dez:
com universo desse tamanho, ler vence ranquear.

## As réguas — e são duas, diferentes

**Jurisprudência erra por PROVENIÊNCIA.** O PDF do acórdão reúne decisão
colegiada, relatório, **alegações de defesa**, instrução técnica, parecer do
MPC, precedentes transcritos e voto. Para a busca são caracteres iguais. Um
trecho de defesa apresentado como entendimento do Tribunal **inverte o
precedente**.

**Norma erra por VIGÊNCIA.** Um quarto dos atos está revogado, e o PDF do
revogado é idêntico, em aparência, ao do vigente. Nenhum resultado sai sem
`situacao`.

Confundi-las é o erro que o servidor mais teme, e as instruções abrem
declarando as duas.

**Nenhum ato normativo tem texto consolidado.** Todo PDF é a redação original;
alteração posterior é ato autônomo. Vale inclusive para o Regimento Interno: o
que o portal serve é a Deliberação 338/2023, alterada pelas 341/2023 e
347/2024. As outras 58 deliberações que mencionam o Regimento são anteriores e
alteravam o regimento **anterior** — citá-las como se alcançassem o texto atual
seria erro.

## Seis coisas que custaram caro

**1. Identidade.** Um acórdão rende mais de uma ementa selecionada — teses
distintas do mesmo julgamento. Espécie + número + ano **não** é chave única; as
páginas pertencem ao documento oficial (`acordao-58739-2023`).

**2. Número de ato não é chave.** A numeração das normas recicla a cada ano —
as 26 portarias usam 11 números; o Ato Normativo nº 2 aparece em quatro
arquivos. Coletar pelo número sobrescreve e pendura o texto no ato do ano
errado, sem erro e sem aviso. A coleta usa `arquivoId`, que é único.

**3. Ausência num grafo de revogação lê-se como vigência.** Resolver o vínculo
durante a inserção falhava para todo revogador que chegasse antes do revogado —
82 relações gravadas das 257 reais. Corrigido com segundo passe.

**4. Voz verbal.** A extração de relações lia só a passiva ("Alterada
pela..."). A alteração do Regimento é declarada na **ativa**, na ementa de quem
altera. O caso mais importante do acervo escapava pela conjugação do verbo.

**5. As espécies não caminham juntas no tempo.** A resposta a consulta entra
ao ser publicada; o acórdão só depois de selecionado e ementado. Em 05/08/2026
a diferença era de quase dois meses — 22/07 contra 27/05. Dizer "o julgado mais
recente é de maio" sem qualificar a espécie é dar a data de uma camada e
atribuí-la ao todo. `cobertura_do_acervo` declara o corte por espécie.

**6. `SUAS` colide com `suas`.** A sigla devolve 17.256 acórdãos — o mesmo que
o pronome possessivo, porque o índice não distingue maiúsculas. Use
`"Sistema Único de Assistência Social"`, que devolve 2.956.

## Armadilhas conhecidas

**Intervalo de versão aberto à direita.** `mcp>=1.28` sem teto quebrou três
deploys quando a 2.0.0 saiu e removeu `mcp.server.fastmcp`. Funcionou num dia e
quebrou no seguinte sem ninguém mexer em nada relevante — **o que muda no
código não é o mesmo que o que muda no mundo**. Todos os requisitos declaram
`<2`.

**Cache do conector.** Ao mudar ferramentas ou instruções, Claude e ChatGPT
continuam com a versão antiga. Desligar e religar não basta — é preciso
**remover e recriar** o conector. Confirme com `cobertura_do_acervo`: têm de
vir **25.561** acórdãos com inteiro teor e **17 ferramentas**.

**Serviços órfãos no Render.** Serviço removido do `render.yaml` não é apagado:
fica no painel e continua tentando construir a cada push. O Render também
sufixa o nome quando ele já existe (`-kip3`), e aí a variável de domínio fica
errada e o serviço responde **421 Invalid Host header** a tudo.

**O painel do Render não é automatizável.** A extensão de navegador espera o
`document_idle`, que aquela aplicação nunca atinge; toda leitura expira em 45 s.
Apagar serviço e forçar deploy são cliques do usuário.

**Python 3.13 quebrado nesta máquina.** Falta `html/entities.py`, `difflib` e
`_curses`. A extensão `.mcpb` foi fixada no 3.12 por causa disso.

**Espaços no caminho.** O Claude Desktop parte o `command` do manifesto no
primeiro espaço. O empacotador converte para o nome curto 8.3.

**Erro de processamento não se conserta rebaixando.** Use
`reparar-inteiro-teor`, que refaz sobre o material já guardado.

## O que está em aberto

**Lei Orgânica do TCE-RJ** (Lei Complementar estadual nº 63/1990) não está em
nenhum dos dois acervos: é lei da ALERJ, não ato do Tribunal. Conferir se está
no MCP `legis-rj` antes de coletar em duplicidade.

**`"termo aditivo"` incompleto.** Bateu o teto de 10.000 na descoberta.
Completa-se fatiando por ano ou município.

**Ato Normativo nº 1/1980** traz, no portal, o texto do de 1982 — erro da
fonte, não da coleta. O texto verdadeiro não está disponível, e o ato é
substantivo: a ementa registra oito alterações e a revogação pelo 160.

**Base de doutrina.** Levantamento feito: ~8.000 documentos, 28 GB, em
`~\OneDrive\Documentos\Livros`. Das 11 obras de licitações medidas, 8 têm texto
aproveitável e 3 são digitalização sem OCR. O **Marçal Justen Filho sobre a
14.133 (1.825 páginas) tem OCR degradado — 58% contra 71–87% das demais**.
Transcrever dali produziria citação falsa. O requisito é trecho literal com
página e citação ABNT, o que exige ficha bibliográfica por obra.

**Relatório da PGM sobre o ETP da Rede SUAS** entregue em duas versões `.docx`.
Pendências registradas nele: CNPJ do Instituto AVANTE, Prejulgado nº 30/2023,
texto integral das Súmulas 17 e 18/2023, e repetir as cinco conclusões
negativas agora que o acervo está completo.

## Como o usuário trabalha

Delega execução, mas julga desenho — e julga bem. Rejeitou embeddings três
vezes com razão técnica, e cada rejeição se confirmou. Cobrou *"você tentou
pelo menos?"* sobre o plano gratuito do Render, e tinha razão: a recomendação
de migrar era dedução não testada, e o teste levou minutos.

Quer saber o que **não** foi verificado, e trata hipótese reprovada como
resultado. Verifique antes de afirmar. Meça antes de otimizar. E quando ele ler
material bruto, escute: a descoberta mais importante deste projeto veio daí.
