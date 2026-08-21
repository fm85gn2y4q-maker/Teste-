import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { criarServidor } from '../src/server.js';
import { MockProvider } from '../src/providers/mock/provider.js';
import { FERRAMENTAS } from '../src/tools/index.js';

const HOJE = '2026-08-21';

async function conectar() {
  const server = criarServidor({
    provider: new MockProvider({ hoje: HOJE, semente: 42 }),
    hoje: () => HOJE,
  });
  const [aCliente, aServidor] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: 'teste', version: '0' });
  await Promise.all([server.connect(aServidor), client.connect(aCliente)]);
  return { client, server };
}

async function chamar(client: Client, nome: string, args: Record<string, unknown> = {}): Promise<string> {
  const r = await client.callTool({ name: nome, arguments: args }) as {
    isError?: boolean;
    content: Array<{ type: string; text?: string }>;
  };
  const texto = r.content.map((c) => c.text ?? '').join('\n');
  assert.ok(!r.isError, `${nome} devolveu erro: ${texto}`);
  return texto;
}

test('o servidor expoe exatamente as 13 ferramentas, todas somente leitura', async () => {
  const { client } = await conectar();
  const { tools } = await client.listTools();
  assert.equal(tools.length, 13);
  assert.deepEqual(tools.map((t) => t.name).sort(), [...FERRAMENTAS].sort());
  for (const t of tools) {
    assert.equal(t.annotations?.readOnlyHint, true, `${t.name} sem readOnlyHint`);
    assert.ok((t.description ?? '').length > 60, `${t.name} com descricao curta demais`);
  }
});

test('nao ha ferramenta de escrita: nenhum nome sugere movimentacao', async () => {
  const { client } = await conectar();
  const { tools } = await client.listTools();
  const proibidos = /transfer|pagar|pix|pagamento|criar|excluir|atualizar|enviar/i;
  const suspeitos = tools.filter((t) => proibidos.test(t.name));
  assert.deepEqual(suspeitos.map((t) => t.name), []);
});

test('cada ferramenta responde sem erro com os argumentos padrao', async () => {
  const { client } = await conectar();
  for (const nome of FERRAMENTAS) {
    const texto = await chamar(client, nome);
    assert.ok(texto.length > 50, `${nome} devolveu resposta curta demais`);
    assert.match(texto, /Fonte:/, `${nome} nao declarou a procedencia`);
  }
});

test('listar_conexoes avisa sobre consentimento expirado', async () => {
  const { client } = await conectar();
  const texto = await chamar(client, 'listar_conexoes');
  assert.match(texto, /Banco do Brasil/);
  assert.match(texto, /expirada/);
  assert.match(texto, /NAO entram em nenhuma/);
});

test('listar_transacoes filtra por texto e periodo', async () => {
  const { client } = await conectar();
  const texto = await chamar(client, 'listar_transacoes', { mes: '2026-06', texto: 'aluguel' });
  assert.match(texto, /ALUGUEL RESIDENCIAL/);
  assert.match(texto, /junho\/2026/);

  const vazio = await chamar(client, 'listar_transacoes', { mes: '2026-06', texto: 'zzzznaoexiste' });
  assert.match(vazio, /Nenhum lancamento/);
  assert.match(vazio, /cartao de credito nao aparecem no extrato/);
});

test('analisar_gastos compara com o periodo anterior', async () => {
  const { client } = await conectar();
  const texto = await chamar(client, 'analisar_gastos', { mes: '2026-06' });
  assert.match(texto, /Gastos em junho\/2026/);
  assert.match(texto, /Contra /);
  assert.match(texto, /Como esse numero foi montado/);
  assert.match(texto, /Compras de cartao de credito somadas pela data da compra/);
});

test('consultar_fatura traz uma fatura por cartao quando nao se pede mes', async () => {
  const { client } = await conectar();
  const texto = await chamar(client, 'consultar_fatura');
  assert.match(texto, /Nubank Ultravioleta/);
  assert.match(texto, /Itau Visa Infinite/);
  assert.match(texto, /rotativo/);
});

test('panorama_financeiro fecha a conta do patrimonio', async () => {
  const { client } = await conectar();
  const texto = await chamar(client, 'panorama_financeiro');
  assert.match(texto, /Patrimonio liquido/);
  assert.match(texto, /Faturas em aberto/);
  assert.match(texto, /Banco do Brasil/, 'deveria avisar que um banco ficou de fora');
});

test('argumento invalido vira erro legivel, nao stack trace', async () => {
  const { client } = await conectar();
  const r = await client.callTool({ name: 'listar_transacoes', arguments: { mes: 'junho' } }) as {
    isError?: boolean; content: Array<{ text?: string }>;
  };
  assert.ok(r.isError);
  const texto = r.content.map((c) => c.text ?? '').join(' ');
  assert.doesNotMatch(texto, /at Object\.|node:internal/);
});

test('fluxo_de_caixa projeta e explica de onde veio a projecao', async () => {
  const { client } = await conectar();
  const texto = await chamar(client, 'fluxo_de_caixa', { dias: 45 });
  assert.match(texto, /proximos 45 dias/);
  assert.match(texto, /Projecao, nao promessa/);
});
