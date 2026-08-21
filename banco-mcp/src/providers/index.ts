import type { Config } from '../config.js';
import type { BankProvider } from './types.js';
import { MockProvider } from './mock/provider.js';
import { PluggyProvider } from './pluggy/provider.js';
import { ClientePluggy } from './pluggy/cliente.js';

export function criarProvider(config: Config): BankProvider {
  if (config.provedor === 'mock') return new MockProvider();

  const { clientId, clientSecret, baseUrl, itemIds } = config.pluggy;
  if (!clientId || !clientSecret) {
    throw new Error(
      'PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET sao obrigatorios com BANCO_MCP_PROVEDOR=pluggy. ' +
      'Para rodar sem credencial, use BANCO_MCP_PROVEDOR=mock.',
    );
  }
  return new PluggyProvider(new ClientePluggy({ clientId, clientSecret, baseUrl }), itemIds);
}

export type { BankProvider };
export { MockProvider, PluggyProvider, ClientePluggy };
