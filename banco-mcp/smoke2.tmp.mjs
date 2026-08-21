import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
const env = { ...process.env, BANCO_MCP_PROVEDOR: 'pluggy', PLUGGY_CLIENT_ID: 'id',
  PLUGGY_CLIENT_SECRET: 'seg', PLUGGY_BASE_URL: 'http://127.0.0.1:8899', PLUGGY_ITEM_IDS: 'item-1',
  BANCO_MCP_INSTITUICOES: '{"acc-1":"Itau","acc-2":"Itau","card-1":"Nubank"}' };
const transport = new StdioClientTransport({ command: 'node', args: ['/home/user/Teste-/banco-mcp/dist/index.js'], env });
const client = new Client({ name: 'smoke', version: '0' });
await client.connect(transport);
const { tools } = await client.listTools();
let falhas = 0;
for (const t of tools) {
  const r = await client.callTool({ name: t.name, arguments: {} });
  const txt = r.content.map(c => c.text).join('');
  const estado = r.isError ? 'ERRO' : 'ok  ';
  if (r.isError) { falhas++; console.log(`${estado} ${t.name}: ${txt.slice(0,140)}`); }
  else console.log(`${estado} ${t.name}  (${txt.length} chars)`);
}
console.log(`\n${tools.length - falhas}/${tools.length} ferramentas responderam contra a API HTTP.`);
const p = await client.callTool({ name: 'panorama_financeiro', arguments: {} });
console.log('\n===== panorama =====\n' + p.content.map(c=>c.text).join('').slice(0, 1400));
await client.close();
