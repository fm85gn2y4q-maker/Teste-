export type NomeProvedor = 'mock' | 'pluggy';

export interface Config {
  provedor: NomeProvedor;
  porta: number;
  /** Token exigido no header Authorization quando o servidor sobe em HTTP. */
  tokenHttp?: string;
  pluggy: {
    clientId?: string;
    clientSecret?: string;
    /** Um item Pluggy = uma conexao com um banco. */
    itemIds: string[];
    baseUrl: string;
  };
}

function lista(v: string | undefined): string[] {
  return (v ?? '').split(',').map((s) => s.trim()).filter(Boolean);
}

export function carregarConfig(env: NodeJS.ProcessEnv = process.env): Config {
  const provedor = (env.BANCO_MCP_PROVEDOR ?? env.BANCO_MCP_PROVIDER ?? 'mock').toLowerCase();
  if (provedor !== 'mock' && provedor !== 'pluggy') {
    throw new Error(`Provedor desconhecido: ${provedor}. Use "mock" ou "pluggy".`);
  }
  return {
    provedor,
    porta: Number(env.PORT ?? env.BANCO_MCP_PORTA ?? 8787),
    ...(env.BANCO_MCP_TOKEN ? { tokenHttp: env.BANCO_MCP_TOKEN } : {}),
    pluggy: {
      ...(env.PLUGGY_CLIENT_ID ? { clientId: env.PLUGGY_CLIENT_ID } : {}),
      ...(env.PLUGGY_CLIENT_SECRET ? { clientSecret: env.PLUGGY_CLIENT_SECRET } : {}),
      itemIds: lista(env.PLUGGY_ITEM_IDS),
      baseUrl: env.PLUGGY_BASE_URL ?? 'https://api.pluggy.ai',
    },
  };
}
