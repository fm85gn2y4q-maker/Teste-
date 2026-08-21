import { test } from 'node:test';
import assert from 'node:assert/strict';
import { definirChave, lerChave, mesclarItemIds } from '../src/util/envArquivo.js';
import { resolverInstituicao, rotulosManuais } from '../src/providers/pluggy/instituicao.js';
import type { ContaPluggy, ItemPluggy } from '../src/providers/pluggy/mapear.js';

const conta = (extra: Record<string, unknown> = {}): ContaPluggy =>
  ({ id: 'acc-1', itemId: 'item-1', subtype: 'CHECKING_ACCOUNT', ...extra }) as ContaPluggy;

test('definirChave preserva comentario e ordem do .env', () => {
  const antes = '# comentario\nBANCO_MCP_PROVEDOR=mock\nPORT=8787\n';
  const depois = definirChave(antes, 'BANCO_MCP_PROVEDOR', 'pluggy');
  assert.equal(depois, '# comentario\nBANCO_MCP_PROVEDOR=pluggy\nPORT=8787\n');
  assert.equal(lerChave(depois, 'PORT'), '8787');
});

test('definirChave acrescenta chave que ainda nao existe', () => {
  assert.equal(definirChave('A=1\n', 'B', '2'), 'A=1\nB=2\n');
  assert.equal(definirChave('', 'A', '1'), 'A=1\n');
});

test('mesclarItemIds acumula conexoes sem repetir', () => {
  let conteudo = '';
  ({ conteudo } = mesclarItemIds(conteudo, ['item-a']));
  const segundo = mesclarItemIds(conteudo, ['item-b', 'item-a']);
  assert.deepEqual(segundo.itens, ['item-a', 'item-b']);
  assert.equal(lerChave(segundo.conteudo, 'PLUGGY_ITEM_IDS'), 'item-a,item-b');
  assert.equal(lerChave(segundo.conteudo, 'BANCO_MCP_PROVEDOR'), 'pluggy');
});

test('mesclarItemIds troca o provedor para pluggy sem apagar o resto', () => {
  const antes = 'BANCO_MCP_PROVEDOR=mock\nPLUGGY_CLIENT_ID=abc\n';
  const { conteudo } = mesclarItemIds(antes, ['item-a']);
  assert.equal(lerChave(conteudo, 'PLUGGY_CLIENT_ID'), 'abc');
  assert.equal(lerChave(conteudo, 'BANCO_MCP_PROVEDOR'), 'pluggy');
});

test('conexao de um banco so leva o nome do conector', () => {
  const item = { id: 'item-1', connector: { name: 'Itau' } } as ItemPluggy;
  assert.deepEqual(resolverInstituicao(item, conta()), { nome: 'Itau', agregado: false });
});

test('conector agregador e sinalizado em vez de fingir que identificou o banco', () => {
  const item = { id: 'item-1', connector: { name: 'Meu Pluggy' } } as ItemPluggy;
  const r = resolverInstituicao(item, conta());
  assert.equal(r.nome, 'Meu Pluggy');
  assert.equal(r.agregado, true, 'deveria sinalizar que o rotulo e generico');
});

test('campo de instituicao vindo do conector vence o nome generico', () => {
  const item = { id: 'item-1', connector: { name: 'Meu Pluggy' } } as ItemPluggy;
  assert.deepEqual(
    resolverInstituicao(item, conta({ institutionName: 'Nubank' })),
    { nome: 'Nubank', agregado: false },
  );
  assert.deepEqual(
    resolverInstituicao(item, conta({ issuer: { name: 'Banco Inter' } })),
    { nome: 'Banco Inter', agregado: false },
  );
});

test('rotulo manual do usuario vence tudo', () => {
  const item = { id: 'item-1', connector: { name: 'Meu Pluggy' } } as ItemPluggy;
  const rotulos = rotulosManuais('{"acc-1":"Bradesco","acc-2":"C6"}');
  assert.deepEqual(resolverInstituicao(item, conta({ institutionName: 'Nubank' }), rotulos),
    { nome: 'Bradesco', agregado: false });
});

test('rotulosManuais engole JSON quebrado sem derrubar o servidor', () => {
  assert.deepEqual(rotulosManuais('{isso nao e json'), {});
  assert.deepEqual(rotulosManuais(undefined), {});
  assert.deepEqual(rotulosManuais('{"a":1,"b":"ok"}'), { b: 'ok' });
});
