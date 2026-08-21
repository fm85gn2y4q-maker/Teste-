import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { BankProvider } from '../providers/types.js';

export interface Contexto {
  provider: BankProvider;
  /** Data civil de referencia, injetavel para teste. */
  hoje: () => string;
}

export type Registrador = (server: McpServer, ctx: Contexto) => void;

export const LEITURA = {
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: true,
} as const;

export function texto(markdown: string) {
  return { content: [{ type: 'text' as const, text: markdown }] };
}

export function falha(mensagem: string) {
  return { isError: true, content: [{ type: 'text' as const, text: mensagem }] };
}

/** Envolve o handler para que erro de rede ou de argumento vire resposta legivel. */
export function protegido<A>(fn: (args: A) => Promise<{ content: Array<{ type: 'text'; text: string }>; isError?: boolean }>) {
  return async (args: A) => {
    try {
      return await fn(args);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      return falha(`Nao consegui completar a consulta: ${msg}`);
    }
  };
}
