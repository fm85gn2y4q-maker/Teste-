# Banco MCP

Servidor MCP **somente leitura** que entrega dados bancarios de Open Finance
brasileiro para Claude, Cursor ou qualquer cliente que fale MCP. Treze
ferramentas cobrem saldo, extrato, cartao, fatura, investimento, divida,
fluxo de caixa e o panorama consolidado.

Roda **sem credencial nenhuma** no modo de demonstracao, com um acervo sintetico
de 14 meses — quatro instituicoes, dois cartoes, carteira e dois financiamentos.

```bash
npm install && npm run build
node dist/index.js              # stdio, provedor mock
node dist/index.js --http       # HTTP em 127.0.0.1:8787/mcp
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

### Modo HTTP

```bash
BANCO_MCP_TOKEN=um-token-longo node dist/index.js --http
```

Sobe em `127.0.0.1:8787/mcp`, sem estado (um servidor por requisicao) e com
`GET /health` para monitoramento. Sem `BANCO_MCP_TOKEN` o servidor avisa no log:
qualquer processo que alcance a porta le os dados. Exponha na rede so atras de
TLS e autenticacao de verdade.

## Ligando em banco de verdade (Pluggy)

1. Crie a aplicacao no painel da Pluggy e pegue `clientId` e `clientSecret`.
2. Conecte os bancos pelo Pluggy Connect. Cada conexao vira um **item**; anote
   os ids.
3. Preencha o `.env` (veja `.env.example`):

```bash
BANCO_MCP_PROVEDOR=pluggy
PLUGGY_CLIENT_ID=...
PLUGGY_CLIENT_SECRET=...
PLUGGY_ITEM_IDS=item-um,item-dois
```

O mapeamento de campos segue a documentacao publica da Pluggy, mas **conector de
banco varia**: confira os primeiros resultados contra o extrato oficial antes de
confiar em qualquer total agregado. Dois pontos ja tratados no codigo, porque
mordem: o sinal do valor (`type: DEBIT/CREDIT` prevalece sobre o sinal de
`amount`) e o ciclo da fatura, montado a partir do `dueDate` do `/bills` com os
lancamentos do periodo.

O Open Finance de consulta nao expoe agendamento futuro — isso vive na iniciacao
de pagamento, que este servidor nao toca. Por isso `listarAgendamentos` devolve
vazio no adaptador Pluggy, e `listar_agendamentos` cai nas recorrencias
detectadas no proprio extrato. Preferimos o vazio honesto a um numero inventado.

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

36 testes cobrindo formatacao monetaria, aritmetica de datas, invariantes do
acervo sintetico (o saldo de cada conta fecha com o extrato; nenhuma compra
entra em duas faturas), a regra de nao contar gasto duas vezes, as 13
ferramentas de ponta a ponta por um cliente MCP em memoria, e o adaptador Pluggy
com `fetch` de mentira — inclusive a trava de escrita.

## O que falta para virar produto

Isto e o motor, nao o servico. Para chegar onde o produto original esta:

- Cadastro, login e 2FA (TOTP ou passkey), com um consentimento por usuario.
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
