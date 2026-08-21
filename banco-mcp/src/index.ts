#!/usr/bin/env node
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { carregarConfig } from './config.js';
import { criarProvider } from './providers/index.js';
import { criarServidor } from './server.js';
import { FERRAMENTAS } from './tools/index.js';

const config = carregarConfig();
const httpMode = process.argv.includes('--http');

function log(msg: string): void {
  // stdout e do protocolo no modo stdio: todo diagnostico vai para stderr.
  process.stderr.write(`[banco-mcp] ${msg}\n`);
}

async function stdio(): Promise<void> {
  const provider = criarProvider(config);
  const server = criarServidor({ provider });
  await server.connect(new StdioServerTransport());
  log(`pronto via stdio · provedor "${provider.nome}" · ${FERRAMENTAS.length} ferramentas somente leitura`);
}

async function http(): Promise<void> {
  const host = process.env.BANCO_MCP_HOST ?? '127.0.0.1';

  const servidor = createServer((req, res) => {
    void tratar(req, res).catch((e) => {
      log(`erro nao tratado: ${e instanceof Error ? e.message : String(e)}`);
      if (!res.headersSent) responder(res, 500, { error: 'internal_error' });
    });
  });

  servidor.listen(config.porta, host, () => {
    log(`ouvindo em http://${host}:${config.porta}/mcp · provedor "${config.provedor}"`);
    if (!config.tokenHttp) {
      log('AVISO: sem BANCO_MCP_TOKEN. Qualquer processo que alcance esta porta le seus dados bancarios.');
    }
  });
}

async function tratar(req: IncomingMessage, res: ServerResponse): Promise<void> {
  const url = new URL(req.url ?? '/', `http://${req.headers.host ?? 'localhost'}`);

  if (url.pathname === '/health') {
    return responder(res, 200, { status: 'ok', provedor: config.provedor, ferramentas: FERRAMENTAS.length });
  }

  if (url.pathname !== '/mcp') {
    return responder(res, 404, { error: 'not_found' });
  }

  if (config.tokenHttp) {
    const enviado = (req.headers.authorization ?? '').replace(/^Bearer\s+/i, '');
    if (enviado !== config.tokenHttp) {
      res.setHeader('WWW-Authenticate', 'Bearer');
      return responder(res, 401, { error: 'unauthorized' });
    }
  }

  // Sem estado: um servidor e um transporte por requisicao. Evita vazar sessao
  // de um cliente para outro, que num servidor de dados bancarios nao e detalhe.
  const provider = criarProvider(config);
  const server = criarServidor({ provider });
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });

  res.on('close', () => {
    void transport.close();
    void server.close();
  });

  await server.connect(transport);
  await transport.handleRequest(req, res);
}

function responder(res: ServerResponse, status: number, corpo: unknown): void {
  res.writeHead(status, { 'content-type': 'application/json' });
  res.end(JSON.stringify(corpo));
}

const iniciar = httpMode ? http : stdio;
iniciar().catch((e) => {
  log(`falha ao iniciar: ${e instanceof Error ? e.message : String(e)}`);
  process.exit(1);
});
