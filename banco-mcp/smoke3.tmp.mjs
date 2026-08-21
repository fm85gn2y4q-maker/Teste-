import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
const env = { ...process.env, BANCO_MCP_PROVEDOR: 'pluggy', PLUGGY_CLIENT_ID: 'id',
  PLUGGY_CLIENT_SECRET: 'seg', PLUGGY_BASE_URL: 'http://127.0.0.1:8899', PLUGGY_ITEM_IDS: 'item-1',
  BANCO_MCP_INSTITUICOES: '{"acc-1":"Itau","acc-2":"Itau","card-1":"Nubank"}' };
const t = new StdioClientTransport({ command: 'node', args: ['/home/user/Teste-/banco-mcp/dist/index.js'], env });
const c = new Client({ name: 'smoke', version: '0' }); await c.connect(t);
const r = await c.callTool({ name: 'panorama_financeiro', arguments: {} });
console.log(r.content.map(x=>x.text).join('').slice(0, 900));
const g = await c.callTool({ name: 'analisar_gastos', arguments: { comparar: false } });
console.log('\n=====\n' + g.content.map(x=>x.text).join('').slice(0, 900));
await c.close();
