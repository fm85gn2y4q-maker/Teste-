# Banco MCP

Servidor MCP **somente leitura** que entrega dados bancarios de Open Finance
brasileiro para Claude, Cursor ou qualquer cliente que fale MCP. Treze
ferramentas cobrem saldo, extrato, cartao, fatura, investimento, divida,
fluxo de caixa e o panorama consolidado.

Roda **sem credencial nenhuma** no modo de demonstracao, com um acervo sintetico
de 14 meses — quatro instituicoes, dois cartoes, carteira e dois financiamentos.

```bash
npm install && npm run build
node dist/index.js              # stdio, modo demonstracao
node dist/index.js --http       # HTTP em 127.0.0.1:8787/mcp
```

Para ligar nos seus bancos de verdade, sao tres comandos — o passo a passo esta
em [Ligando em banco de verdade](#ligando-em-banco-de-verdade).

```bash
npm run conectar      # abre a pagina local, voce autoriza cada banco
npm run diagnostico   # confere se os dados chegam certos
claude mcp add banco -- node $PWD/dist/index.js
```

## Antes de tudo: o que aqui e codigo e o que e licenca

A parte dificil de "conectar em 30 bancos" nao e software.

Ler dados de Open Finance direto das instituicoes exige ser **participante
autorizado pelo Banco Central**, com registro no Diretorio de Participantes,
certificados ICP-Brasil e mTLS, conformidade FAPI e gestao de consentimento nos
moldes da Resolucao Conjunta nº 1/2020 e da Resolucao BCB nº 32/2020. Nao ha
atalho de codigo para isso.

Para quem nao e instituicao autorizada, sobram dois caminhos legitimos:

1. **Agregador autorizado** — Pluggy, Belvo, Klavi. Eles ja tem a licenca; voce
   consome a API deles. E o que o adaptador `pluggy` deste repositorio faz.
   Para uso pessoal, o *Meu Pluggy* e gratuito por tempo indeterminado: e o
   caminho mais curto para ver isto funcionando com dinheiro de verdade.
2. **API direta de um banco** — o Banco Inter, por exemplo, publica API para
   titulares de conta PJ, com certificado proprio. Cobre um banco so.

Este projeto entrega tudo que fica *acima* dessa camada, e a deixa plugavel.

## As 13 ferramentas

| Ferramenta | Para que serve |
| --- | --- |
| `listar_conexoes` | Bancos conectados, status do consentimento, o que ficou de fora |
| `listar_contas` | Contas de todas as instituicoes, com saldo e cheque especial |
| `consultar_saldos` | "Quanto eu tenho hoje?" — consolidado por instituicao |
| `listar_transacoes` | Extrato com filtro de periodo, conta, categoria, valor e busca livre |
| `resumo_mensal` | Entradas, saidas e resultado mes a mes, com taxa de poupanca |
| `analisar_gastos` | Gastos por categoria, estabelecimento, instituicao ou meio de pagamento |
| `listar_cartoes` | Limite total, disponivel, uso e ciclo de cada cartao |
| `consultar_fatura` | Fatura aberta ou de um mes: total, minimo, composicao, maiores lancamentos |
| `carteira_investimentos` | Posicao por ativo e por classe, rentabilidade, liquidez, concentracao |
| `listar_emprestimos` | Saldo devedor, parcela, juros, CET e juros ainda embutidos |
| `fluxo_de_caixa` | Projecao de saldo a partir do que ja esta contratado |
| `listar_agendamentos` | Agendamentos dos bancos + recorrencias detectadas no extrato |
| `panorama_financeiro` | Tudo em uma resposta: patrimonio liquido, mes, alertas |

### O detalhe que quase toda analise de extrato erra

Uma compra no cartao aparece **duas vezes** nos dados: como lancamento na fatura
e, um mes depois, como debito da fatura na conta. Somar os dois infla o gasto.
Somar so o extrato joga a despesa para o mes errado.

`analisar_gastos` e `panorama_financeiro` resolvem isso: entram as compras pela
data da compra, sai o debito da fatura, e transferencia entre contas do proprio
titular nao conta como gasto. Toda resposta declara essa montagem em "Como esse
numero foi montado" — o numero tem que ser conferivel.

## Somente leitura, por construcao

- A interface `BankProvider` (`src/providers/types.ts`) **nao tem um metodo de
  escrita**. Um adaptador novo so consegue ler.
- O cliente HTTP da Pluggy recusa, dentro do processo, qualquer metodo que nao
  seja `GET`, com uma unica excecao: o `POST /auth` da autenticacao. Um teste
  exercita o adaptador inteiro e falha se qualquer escrita escapar.
- Nao existe transferencia, Pix, pagamento nem alteracao de cadastro. As
  instrucoes do servidor mandam o assistente dizer isso ao usuario quando ele
  pedir.

## Ligando no seu cliente MCP

### Claude Code

```bash
claude mcp add banco -- node /caminho/para/banco-mcp/dist/index.js
```

### Claude Desktop / Cursor (`claude_desktop_config.json`, `mcp.json`)

```json
{
  "mcpServers": {
    "banco": {
      "command": "node",
      "args": ["/caminho/para/banco-mcp/dist/index.js"],
      "env": { "BANCO_MCP_PROVEDOR": "mock" }
    }
  }
}
```

### Claude Code na web

O repositorio ja vem configurado: `.mcp.json` registra o servidor e um hook de
inicio de sessao instala as dependencias e compila. Toda sessao nova sobe com as
13 ferramentas prontas, em **modo demonstracao**, sem passo manual.

Para alcancar a Pluggy de dentro de uma sessao, o ambiente precisa liberar o
dominio. No seletor de ambiente em `claude.ai/code` (o icone de nuvem acima da
caixa de mensagem), engrenagem do ambiente > **Network access** > **Custom** >
**Allowed domains**:

```text
api.pluggy.ai
```

Marque **Also include default list of common package managers** — sem isso o
`npm install` do hook para de funcionar, porque o registro do npm sai da lista.

> **Nao coloque `PLUGGY_CLIENT_SECRET` no campo de variaveis de ambiente.**
> A propria documentacao do Claude Code avisa que ambientes de nuvem nao tem
> cofre de segredos e que os valores sao legiveis por quem usa o ambiente. Uma
> credencial que le todas as suas contas bancarias nao pertence a um campo de
> configuracao compartilhavel.
>
> Para dados bancarios reais, o lugar certo e a **sua maquina**: `.env` com
> permissao 600, servidor rodando localmente, dados nao saindo dali. A sessao da
> web fica com o modo demonstracao, que existe justamente para isso.

### Modo HTTP

```bash
BANCO_MCP_TOKEN=um-token-longo node dist/index.js --http
```

Sobe em `127.0.0.1:8787/mcp`, sem estado (um servidor por requisicao) e com
`GET /health` para monitoramento. Sem `BANCO_MCP_TOKEN` o servidor avisa no log:
qualquer processo que alcance a porta le os dados. Exponha na rede so atras de
TLS e autenticacao de verdade.

## Ligando em banco de verdade

### Custa quanto

Para **uso pessoal**, nada: a Pluggy mantem o *Meu Pluggy*, gratuito por tempo
indeterminado, para pessoa fisica conectar as proprias contas e consumir a API
em ferramenta propria. A condicao e que as contas sejam suas, nominais. Uso
comercial cai no plano pago (a partir de R$ 2.500/mes), que e outra conversa.

### Passo a passo

São **dois cadastros distintos**, e confundi-los e o tropeco mais comum:

| Onde | Para que |
| --- | --- |
| `meu.pluggy.ai` | Conectar seus bancos. E onde voce autoriza cada instituicao. |
| `dashboard.pluggy.ai` | Pegar `clientId` e `clientSecret`. E o que este servidor usa. |

1. **Cadastre-se em `meu.pluggy.ai`** e, em *Conectar Minha Conta*, adicione cada
   banco que quiser acompanhar. Cada um pede uma autorizacao propria, feita no
   ambiente do proprio banco — sua senha nunca passa por este servidor, nem pela
   Pluggy.
2. **Cadastre-se em `dashboard.pluggy.ai`**, crie uma aplicacao e rode:

   ```bash
   npm run configurar
   ```

   Ele pede `clientId` e `clientSecret`, **confere com a Pluggy antes de gravar**
   e escreve no `.env` com permissao 600. O secret nao e ecoado enquanto voce
   digita, entao nao fica no scrollback do terminal.

   > O par `clientId` + `clientSecret` da acesso de leitura a **todas** as suas
   > contas conectadas. Ele mora no `.env`, que o `.gitignore` ja bloqueia.
   > Nunca cole esse par em chat, ticket, issue ou commit — inclusive numa
   > conversa com um assistente. Se acontecer, regenere as credenciais no
   > Dashboard: revogar leva segundos, e a chave antiga morre na hora.
3. **Traga as conexoes.** Se voce ja conectou seus bancos no passo 1, nao
   precisa de navegador nenhum:

   ```bash
   npm run conexoes    # lista as conexoes da sua conta e grava os ids
   ```

   Se preferir conectar bancos novos na hora, ou se sua conta nao expuser a
   lista pela API:

   ```bash
   npm run conectar
   ```

   Abre `http://127.0.0.1:8788`. Clique em *Abrir o Pluggy Connect* e escolha o
   conector **Meu Pluggy**, entrando com a conta do passo 1: e ele que traz as
   contas que voce ja conectou. Os ids das conexoes caem no `.env` sozinhos — o
   provedor tambem troca para `pluggy` automaticamente. Se o widget nao carregar,
   a mesma pagina tem um campo para colar o id manualmente, copiado do Dashboard.

4. **Confira antes de confiar:**

   ```bash
   npm run diagnostico
   ```

   Autentica, lista conexoes, contas, cartoes, faturas e carteira, e aponta o que
   costuma dar errado: consentimento vencido, conta que nao sincronizou, sinal de
   valor invertido, ciclo de fatura deslocado, lancamento sem categoria. **Todo
   digito sai mascarado** (`R$ ##.###,##`), entao da para colar a saida num chat
   pedindo ajuda sem expor saldo, numero de conta ou CPF.

### Quando todos os bancos aparecem com o mesmo nome

Conectores agregadores — o Meu Pluggy entre eles — podem entregar contas de
varios bancos sob uma conexao so, sem dizer de qual banco e cada conta. Nesse
caso o servidor **nao inventa**: mantem o rotulo generico e o diagnostico avisa,
ja imprimindo a linha pronta para voce corrigir:

```bash
BANCO_MCP_INSTITUICOES={"acc-123":"Nubank","acc-456":"Itau"}
```

Rotulo manual vence tudo; depois dele o servidor tenta o campo de instituicao que
o proprio conector mandou; so entao cai no nome do conector.

### O que conferir na primeira semana

O mapeamento segue a documentacao publica da Pluggy, mas **conector de banco
varia**. Confira uma compra conhecida contra o extrato oficial antes de confiar
em total agregado. Dois pontos ja tratados no codigo, porque mordem: o sinal do
valor (`type: DEBIT/CREDIT` prevalece sobre o sinal de `amount`) e o ciclo da
fatura, montado a partir do `dueDate` do `/bills` com os lancamentos do periodo.

O Open Finance de consulta nao expoe agendamento futuro — isso vive na iniciacao
de pagamento, que este servidor nao toca. Por isso `listarAgendamentos` devolve
vazio no adaptador Pluggy, e `listar_agendamentos` cai nas recorrencias
detectadas no proprio extrato. Preferimos o vazio honesto a um numero inventado.

### Seus dados vao para dentro da conversa

Quando voce pergunta "com o que gastei esse mes", o extrato entra no contexto do
modelo — e assim que ele consegue responder. O servidor roda na sua maquina e nao
persiste nada, mas a resposta trafega. Isso vale para qualquer servidor MCP
bancario, nao e particularidade deste. Pese contra a politica de retencao do
cliente que voce usa.

## Arquitetura

```
src/
  providers/        contrato read-only + adaptadores (mock, pluggy)
  analise/          gastos, fluxo de caixa, patrimonio — funcoes puras
  tools/            as 13 ferramentas MCP, agrupadas por assunto
  util/             centavos (inteiro, sempre) e datas civis de Brasilia
  server.ts         montagem do McpServer e as instrucoes ao assistente
  index.ts          entrada: stdio ou HTTP
```

Duas decisoes que sustentam o resto:

- **Dinheiro em centavos inteiros.** Nenhum float atravessa um somatorio de
  extrato.
- **Data como string civil `YYYY-MM-DD`.** Nada de `Date` com fuso: o lancamento
  de 31/01 nao pode virar 30/01 porque o processo roda em UTC.

Toda analise vive sobre o modelo de dominio, entao vale igual para o mock e para
qualquer adaptador futuro.

## Testes

```bash
npm test
```

46 testes cobrindo formatacao monetaria, aritmetica de datas, invariantes do
acervo sintetico (o saldo de cada conta fecha com o extrato; nenhuma compra
entra em duas faturas), a regra de nao contar gasto duas vezes, as 13
ferramentas de ponta a ponta por um cliente MCP em memoria, e o adaptador Pluggy
com `fetch` de mentira — inclusive a trava de escrita, a edicao cirurgica do
`.env` e a resolucao de nome de instituicao.

Alem dos testes, o pipeline inteiro ja foi exercitado contra um servidor HTTP
que imita a Pluggy: autenticacao, listagem de conexoes, contas, extrato, fatura,
carteira, credito, o diagnostico e as 13 ferramentas por um cliente MCP real.
Foi esse exercicio que pegou o credito de cartao entrando como gasto.

## O que falta para virar produto

Isto e o motor, nao o servico. Para chegar onde o produto original esta:

- Cadastro, login e 2FA (TOTP ou passkey), com um consentimento por usuario.
  Hoje a conexao e local: `npm run conectar` grava no seu `.env`.
- Multi-tenant: hoje o processo serve um conjunto de conexoes, definido por
  variavel de ambiente.
- Cofre de tokens com chave gerenciada, rotacao e revogacao em ate 30 dias apos
  o cancelamento.
- Trilha de auditoria de cada consulta, exigida por qualquer tratamento serio de
  dado financeiro sob a LGPD.
- Cobranca e limites de uso.

## Licenca e responsabilidade

Uso pessoal e educacional. Nao e recomendacao de investimento nem consultoria
financeira. Os numeros valem pela data da ultima sincronizacao informada em cada
resposta — para valor de quitacao, saldo do momento ou qualquer ato com efeito
juridico, o canal do proprio banco continua sendo a fonte.
