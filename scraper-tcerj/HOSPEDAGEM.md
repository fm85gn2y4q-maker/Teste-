# Hospedar o Ementário

Enquanto o servidor roda na sua máquina, ele morre com ela: extensão, túnel e
conector, todos. Para consultar do celular ou com o computador desligado, o
Ementário precisa estar num lugar que não desliga.

São ~10 MB de SQLite e um processo Python que só lê. Cabe no nível gratuito de
qualquer serviço sério.

## Antes de começar, três coisas

**O serviço fica público.** Clientes MCP não se autenticam sozinhos, então o
endereço aceita quem tiver a URL. Para jurisprudência do TCE-RJ — ato público,
já disponível no portal do Tribunal — isso é aceitável. **Não repita isso com o
repositório de doutrina**: livros são obra protegida, e um endereço aberto
deixa de ser cópia privada.

**Você precisa criar a conta.** Não posso criar contas nem inserir dados de
pagamento por você. Os passos de console e os comandos são seus; a preparação
(imagem, configuração, verificação) já está feita.

**O endereço só existe depois do primeiro deploy.** O servidor recusa Host que
não conheça — proteção contra DNS rebinding. Então são dois passos: publicar,
descobrir a URL, declarar a URL, republicar. Não dá para inverter a ordem.

## Google Cloud Run — o caminho recomendado

Foi o que você perguntou, e é de fato o que melhor serve aqui: escala a zero
(não paga por ficar parado), nível gratuito permanente e região em São Paulo.

O nível gratuito cobre folgadamente um uso pessoal, mas **exige conta de
faturamento com cartão** — mesmo sem cobrar. Se isso for impeditivo, veja as
alternativas mais abaixo.

### 1. Projeto e ferramenta

Crie um projeto em <https://console.cloud.google.com> e instale o `gcloud`:

```bash
winget install --id Google.CloudSDK
```

Feche e reabra o terminal, então autentique:

```bash
gcloud auth login
```

```bash
gcloud config set project SEU_PROJETO
```

### 2. Publicar

Da pasta `scraper-tcerj`:

```bash
gcloud run deploy ementario --source . --region southamerica-east1 --allow-unauthenticated
```

Ele pergunta se pode habilitar as APIs necessárias — aceite. A primeira
publicação demora alguns minutos: manda o código, constrói a imagem e sobe.

No fim ele imprime a URL, algo como
`https://ementario-123456789.southamerica-east1.run.app`.

### 3. Declarar o endereço e republicar

Com a URL em mãos, sem o `https://`:

```bash
gcloud run services update ementario --region southamerica-east1 --set-env-vars EMENTARIO_DOMINIOS=ementario-123456789.southamerica-east1.run.app
```

### 4. Conferir

```bash
curl -s -X POST https://SUA-URL/mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"teste\",\"version\":\"1\"}}}"
```

Tem que voltar `"serverInfo":{"name":"ementario"...}`. Se vier **421**, o
`EMENTARIO_DOMINIOS` não bateu com o endereço — confira se copiou sem o
`https://` e sem barra no fim.

### 5. Ligar ao Claude

**Configurações → Conectores → Adicionar conector personalizado**, com
`https://SUA-URL/mcp` e autenticação **Nenhuma**. Agora vale no celular, no
navegador e com o computador desligado.

## O que esperar no dia a dia

Escalando a zero, a primeira consulta depois de um tempo parado leva alguns
segundos a mais — o contêiner precisa subir. As seguintes são imediatas. Dá
para eliminar isso mantendo uma instância mínima ligada, mas aí sai do
gratuito.

## Alternativas

Se o cartão for impeditivo, há serviços que publicam contêiner sem exigir
faturamento — o **Hugging Face Spaces** com SDK Docker é o mais direto deles, e
o mesmo `Dockerfile` serve. **Render** e **Fly.io** também rodam este contêiner.

Não descrevo os passos de cada um porque os termos dos níveis gratuitos mudam
com frequência e eu não os verifiquei agora; confira as condições atuais antes
de escolher. O que está pronto aqui — imagem, configuração por ambiente,
verificação — vale para qualquer um deles.

## Atualizar o acervo depois

Uma nova coleta muda o `dados/tcerj.sqlite`, que vai dentro da imagem. Para
publicar a base atualizada, repita o `gcloud run deploy` da etapa 2. O
`EMENTARIO_DOMINIOS` já configurado permanece.
