# Manual de execução na máquina local

Este documento é feito para ser colado no Claude Code rodando no seu
computador, onde há acesso de rede ao site do TCE-RJ. O coletor foi escrito num
ambiente sem esse acesso, então a calibração contra o portal real é a primeira
coisa a fazer — e ela exige julgamento, não só rodar comandos.

O bloco abaixo é o texto a colar. O resto do arquivo explica o que esperar de
cada etapa, para você conferir o que o agente fizer.

---

## Bloco para colar

````
Preciso rodar e calibrar um coletor de jurisprudência do TCE-RJ que já está
escrito, mas nunca foi executado contra o site real.

Repositório: https://github.com/fm85gn2y4q-maker/Teste-
Branch: claude/tce-rj-jurisprudencia-scraping-r2oi6p
Diretório: scraper-tcerj/

CONTEXTO IMPORTANTE
O código foi desenvolvido num ambiente sem acesso de rede ao tcerj.tc.br. Toda
a lógica de extração, armazenamento e paginação está testada (101 testes
passando), mas o endereço e o formato do endpoint interno do portal NUNCA foram
verificados. Por isso o coletor não presume esse endereço: ele o descobre em
tempo de execução, interceptando o tráfego do portal num navegador real.

Sua tarefa é executar essa calibração, confirmar que a coleta funciona de fato
e me relatar o resultado.

ETAPA 0 — Preparar
- Clone o repositório e faça checkout da branch acima (ou use o diretório se eu
  já tiver clonado).
- Em scraper-tcerj/: crie um venv, instale requirements.txt e rode
  `playwright install chromium`.
- Rode `pytest -m "not integracao"` e confirme que passa. Se falhar, pare e me
  diga o que quebrou antes de tocar no site.

ETAPA 1 — Descobrir o endpoint
Rode: python -m tcerj descobrir --termo "licitação"

Isso abre o portal num Chromium, faz uma busca e grava as chamadas de rede em
descoberta.json, escrevendo um config.json com a mais promissora.

Agora JULGUE o resultado, não aceite de olhos fechados:
- Abra descoberta.json e veja as chamadas capturadas com pontuação alta.
- A escolhida faz sentido? A URL parece de jurisprudência e a amostra da
  resposta traz campos como ementa, relator, número de acórdão, processo?
- Confira se caminho_itens aponta mesmo para a lista de resultados e se
  campo_pagina/campo_tamanho batem com o que o portal envia.
- Corrija config.json à mão se a inferência errou algum campo.

Se NENHUM endpoint foi reconhecido:
- Rode de novo com --mostrar-navegador e faça a busca manualmente na janela que
  abrir; o tráfego é capturado do mesmo jeito.
- Se ainda assim não houver chamada JSON útil, o portal pode renderizar no
  servidor. Nesse caso siga pelo backend "navegador" (Etapa 2B) e me avise.

ETAPA 2A — Validar o modo api (se a Etapa 1 deu certo)
Rode uma coleta pequena primeiro:
  python -m tcerj -c config.json coletar --max-documentos 20 -v

Critérios de sucesso — verifique com `python -m tcerj estatisticas` e
`python -m tcerj buscar "licitação"`:
- vieram ~20 documentos, não 0 e não 1;
- os campos numero, ano e tipo estão preenchidos na maioria;
- ementa tem texto de verdade, não fragmento nem HTML solto;
- relator e processo aparecem em boa parte dos registros;
- rodar o MESMO comando de novo não duplica nada (o total não deve dobrar).

Se muitos campos vierem vazios, exporte alguns registros
(`python -m tcerj exportar amostra.jsonl`), olhe o campo "bruto" de um deles e
me mostre: pode ser que os nomes de campo da API real não estejam na lista de
apelidos de extracao.py:documento_de_registro. Ajuste a lista e rode de novo.

ETAPA 2B — Validar o modo navegador (alternativa, não depende de endpoint)
  python -m tcerj coletar --backend navegador --max-documentos 20 -v

Mesmos critérios de sucesso. Se vier pouca coisa ou nada, o problema costuma
ser seletor de CSS: abra o portal, inspecione a listagem e ajuste em
config.json os campos seletores.item_resultado e seletores.proxima_pagina para
o layout real. Depois repita.

ETAPA 3 — Coleta de verdade
Só depois que a Etapa 2 estiver limpa:
  python -m tcerj -c config.json coletar --tipo acordao --max-paginas 50

Repita por espécie: acordao, sumula, enunciado, deliberacao, resolucao,
parecer_previo, resposta_consulta.

REGRAS DE CONDUTA — não negocie estas
- Mantenha intervalo_seg em 1,5 ou mais e concorrencia em 2. É servidor
  público; não acelere para "testar mais rápido".
- Não desligue respeitar_robots. Se o robots.txt bloquear o caminho, me diga em
  vez de contornar.
- Nada de login, captcha ou qualquer forma de burlar controle de acesso. Só
  conteúdo público.
- Se o site começar a devolver 429 ou 403 em série, PARE e me avise. Não fique
  repetindo.

AO FINAL, me relate:
1. Qual endpoint foi descoberto (ou que a descoberta falhou e por quê).
2. Quantos documentos vieram, por espécie.
3. Que campos ficaram frequentemente vazios e por quê.
4. Que ajustes você precisou fazer em config.json ou no código.
5. Qualquer coisa que pareceu errada e você não conseguiu resolver.

Não me diga que funcionou sem ter conferido os critérios da Etapa 2.
````

---

## O que esperar de cada etapa

**Etapa 0.** Os 94 testes que não usam navegador rodam em segundos. Se algum
falhar antes de qualquer contato com o site, o problema é de ambiente
(versão de Python, dependência) — resolver isso primeiro evita confundir erro
local com erro de calibração.

**Etapa 1.** O resultado bom é uma linha dizendo `Endpoint mais provável:` com
uma URL que contenha algo como `jurisprudencia`, `acordao` ou `consulta`, e uma
contagem de itens por página maior que zero. Pontuação alta sozinha não basta:
a heurística pontua qualquer lista de objetos com vocabulário jurídico, e um
endpoint de filtros ou de menu pode passar. Por isso a instrução manda abrir o
`descoberta.json` e conferir a amostra.

Nenhum cookie ou cabeçalho de sessão é gravado nesse arquivo — ele pode ser
inspecionado e compartilhado sem risco.

**Etapa 2.** O teste que mais importa é o da segunda execução: se o total
dobrar, a identidade dos documentos não está estável, e aí vale investigar
antes de coletar em volume. O identificador é derivado de tipo + número + ano,
com queda para hash da URL quando o número não é extraído — então total
dobrado costuma significar que o número não está vindo.

**Etapa 3.** A coleta é retomável. Interromper com Ctrl+C e rodar de novo
continua de onde parou. Um documento que apareça primeiro na listagem e depois
no detalhe é completado, não sobrescrito.

## Ajustes mais prováveis

Se algo precisar de conserto, quase sempre é um destes três pontos:

| Sintoma | Onde mexer |
|---|---|
| API responde, mas campos vêm vazios | `extracao.py`, função `documento_de_registro` — a lista de apelidos de cada campo |
| Modo navegador traz poucos ou nenhum item | `config.json`, `seletores.item_resultado` e `seletores.proxima_pagina` |
| Paginação repete sempre a primeira página | `config.json`, `api.campo_pagina` e `api.primeira_pagina` (algumas APIs começam em 1, outras usam deslocamento em registros) |

Texto com acento corrompido (`ACÃ“RDÃƒO`) já é tratado automaticamente — se
aparecer no resultado final, é bug, vale reportar.
