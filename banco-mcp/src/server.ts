import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { hojeISO } from './util/datas.js';
import { registrarFerramentas } from './tools/index.js';
import type { BankProvider } from './providers/types.js';

export const INSTRUCOES = `Banco MCP — consulta somente leitura de dados bancarios via Open Finance.

Como usar bem estas ferramentas:

- Comece por \`panorama_financeiro\` quando a pergunta for ampla ("como estao minhas
  financas", "posso comprar X"). Ele resolve numa chamada o que exigiria cinco.
- \`listar_conexoes\` diz quais bancos entram na conta. Consentimento expirado
  significa dados ausentes, nao dados zerados — se houver instituicao inativa,
  avise o usuario antes de apresentar qualquer total.
- Compra no cartao NAO aparece no extrato da conta: o extrato mostra o debito da
  fatura, uma vez por mes. Para o que foi comprado, use \`consultar_fatura\`.
  \`analisar_gastos\` ja junta os dois sem contar duas vezes.
- Todo resultado traz a origem e a data da sincronizacao no rodape. Repasse:
  saldo daqui e o da ultima sincronizacao, nao o do momento.
- Nenhuma ferramenta movimenta dinheiro. Nao ha transferencia, Pix, pagamento
  nem alteracao de cadastro — se o usuario pedir isso, diga que precisa ser
  feito no aplicativo do proprio banco.

Ao responder: entregue a analise e os numeros, nao o funcionamento da ferramenta.
Valores em reais, datas em dd/mm/aaaa.`;

export interface OpcoesServidor {
  provider: BankProvider;
  /** Data de referencia; util em teste. */
  hoje?: () => string;
}

export function criarServidor({ provider, hoje }: OpcoesServidor): McpServer {
  const server = new McpServer(
    { name: 'banco-mcp', version: '0.1.0' },
    { capabilities: { tools: {} }, instructions: INSTRUCOES },
  );
  registrarFerramentas(server, { provider, hoje: hoje ?? (() => hojeISO()) });
  return server;
}
