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

## Render — sem cartão, publicando a partir do GitHub

O Render tem uma vantagem sobre o Cloud Run aqui: **o endereço é previsível**
(`https://NOME.onrender.com`). Dá para declarar o domínio antes de publicar, e
o vai-e-volta descrito acima desaparece.

Em troca, duas limitações reais do plano gratuito:

- **O serviço dorme.** Depois de ~15 minutos sem uso ele desliga, e a primeira
  consulta seguinte demora perto de um minuto para responder — tempo de subir o
  contêiner de novo. As consultas seguintes são imediatas. Para pesquisa
  pontual, incomoda; para uso contínuo numa mesma sessão, não.
- **Publica a partir de um repositório Git.** Não há envio de pasta local, o
  que traz a decisão abaixo.

### O acervo não vai no Git

O banco é **artefato de dados**, não código-fonte: é gerado por programa, muda
em ritmo próprio e cresce a cada coleta. Versioná-lo faria o histórico carregar
uma cópia binária inteira por atualização — e o GitHub avisa acima de 50 MiB e
recusa objetos acima de 100 MiB.

Ele vai comprimido como **asset de release**, e a imagem o baixa na construção
com a versão fixada. Assim o deploy é reproduzível, o rollback é trocar uma
linha, e uma coleta ruim não altera produção em silêncio.

```
coletar → testar → VACUUM → comprimir → asset de release
        → apontar a versão no render.yaml → Render reconstrói
```

### 1. Gerar e publicar o acervo

Depois de coletar, gere o arquivo comprimido e anote o `sha256`. Publique-o em
**Releases → Draft a new release**, com uma tag por versão do acervo
(`acervo-v2.0.0`), arrastando o `.db.gz` para os assets.

Não use `latest` em produção: versão fixa é o que torna o deploy reproduzível
e o rollback trivial.

### 2. Apontar a versão e enviar o código

No `render.yaml`, `ACERVO_URL` recebe o endereço do asset e `ACERVO_SHA256` a
soma conferida na construção — se o arquivo mudar, o build falha em vez de
subir um acervo diferente do esperado.

```bash
git add render.yaml scraper-tcerj && git commit -m "Publica acervo v2.0.0" && git push
```

### 2. Criar o serviço

Em <https://render.com>, entre com a conta do GitHub e autorize o acesso ao
repositório. Então **New → Blueprint**, aponte para o repositório e confirme: o
`render.yaml` já traz nome, região, plano e variável de ambiente.

Se o nome `ementario-tcerj` estiver ocupado, o Render avisa. Escolha outro e
**troque nos dois lugares** do `render.yaml` — o `name` e o `EMENTARIO_DOMINIOS`
— antes de confirmar. Eles têm de bater.

Preferindo configurar na mão: **New → Web Service**, repositório, *Root
Directory* `scraper-tcerj`, *Runtime* Docker, plano Free, e a variável
`EMENTARIO_DOMINIOS` com `NOME.onrender.com` (sem `https://`, sem barra final).

### 3. Conferir

A primeira construção leva alguns minutos. Quando o painel mostrar *Live*:

```bash
curl -s -X POST https://SEU-NOME.onrender.com/mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"teste\",\"version\":\"1\"}}}"
```

Tem que voltar `"serverInfo":{"name":"ementario"...}`.

**421** significa que `EMENTARIO_DOMINIOS` não bate com o endereço — quase
sempre por ter ficado o nome antigo depois de trocar o do serviço.

### 4. Ligar ao Claude

**Configurações → Conectores → Adicionar conector personalizado**, com
`https://SEU-NOME.onrender.com/mcp` e autenticação **Nenhuma**.

### Atualizar o acervo depois

Nova coleta muda o `dados/tcerj.sqlite`. Basta versionar e enviar: o Render
reconstrói sozinho a cada envio para o repositório.

```bash
git add scraper-tcerj/dados/tcerj.sqlite && git commit -m "Atualiza o acervo" && git push
```

## Google Cloud Run — quando o cartão não for problema

Tecnicamente é o melhor dos dois: escala a zero, nível gratuito permanente,
região em São Paulo e sem o sono de 15 minutos do Render — o tempo de partida
a frio é de segundos, não de um minuto.

O preço é **exigir conta de faturamento com cartão**, mesmo sem cobrar nada
dentro do nível gratuito.

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

## Outras opções

**Hugging Face Spaces** com SDK Docker e **Fly.io** também rodam este mesmo
contêiner. Não descrevo os passos porque os termos dos níveis gratuitos mudam
com frequência e eu não os verifiquei; confira as condições atuais antes de
escolher. O que está pronto aqui — imagem, configuração por ambiente,
verificação — vale para qualquer um deles.

## O que eu não verifiquei

Não construí a imagem nem publiquei em nenhum destes serviços: não há Docker
nesta máquina, e criar contas e inserir dados de pagamento é coisa sua. O que
foi testado é o comportamento do servidor sob as variáveis de ambiente que a
hospedagem define — porta lida de `PORT`, domínios de `EMENTARIO_DOMINIOS`,
domínio não declarado recusado com 421.

Os termos dos planos gratuitos (cartão, tempo de sono, regiões) mudam e valem
pelo que estavam quando isto foi escrito. Confirme no serviço.

## Atualizar o acervo depois

Uma nova coleta muda o `dados/tcerj.sqlite`, que vai dentro da imagem. Para
publicar a base atualizada, repita o `gcloud run deploy` da etapa 2. O
`EMENTARIO_DOMINIOS` já configurado permanece.
