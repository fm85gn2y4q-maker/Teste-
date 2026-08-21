import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { registrarContas } from './contas.js';
import { registrarExtrato } from './extrato.js';
import { registrarCartoes } from './cartoes.js';
import { registrarPatrimonio } from './patrimonio.js';
import { registrarPlanejamento } from './planejamento.js';
import type { Contexto } from './base.js';

/** As 13 ferramentas do Banco MCP. Todas somente leitura. */
export const FERRAMENTAS = [
  'listar_conexoes',
  'listar_contas',
  'consultar_saldos',
  'listar_transacoes',
  'resumo_mensal',
  'analisar_gastos',
  'listar_cartoes',
  'consultar_fatura',
  'carteira_investimentos',
  'listar_emprestimos',
  'fluxo_de_caixa',
  'listar_agendamentos',
  'panorama_financeiro',
] as const;

export function registrarFerramentas(server: McpServer, ctx: Contexto): void {
  registrarContas(server, ctx);
  registrarExtrato(server, ctx);
  registrarCartoes(server, ctx);
  registrarPatrimonio(server, ctx);
  registrarPlanejamento(server, ctx);
}

export type { Contexto };
