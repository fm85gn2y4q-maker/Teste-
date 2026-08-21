import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ClientePluggy } from '../src/providers/pluggy/cliente.js';
import { PluggyProvider } from '../src/providers/pluggy/provider.js';
import { mapearTransacao } from '../src/providers/pluggy/mapear.js';

interface Chamada { metodo: string; caminho: string; query: URLSearchParams }

/** Fetch de mentira que devolve payloads no formato publico da Pluggy. */
function stubFetch(chamadas: Chamada[]): typeof fetch {
  return (async (entrada: string | URL | Request, init?: RequestInit) => {
    const url = new URL(typeof entrada === 'string' ? entrada : entrada.toString());
    chamadas.push({ metodo: init?.method ?? 'GET', caminho: url.pathname, query: url.searchParams });

    const json = (corpo: unknown) =>
      new Response(JSON.stringify(corpo), { status: 200, headers: { 'content-type': 'application/json' } });

    if (url.pathname === '/auth') return json({ apiKey: 'chave-de-teste' });
    if (url.pathname === '/items/item-1') {
      return json({
        id: 'item-1', status: 'UPDATED', createdAt: '2026-02-10T12:00:00.000Z',
        updatedAt: '2026-08-21T06:00:00.000Z', consentExpiresAt: '2027-02-10T12:00:00.000Z',
        connector: { id: 201, name: 'Itau', type: 'PERSONAL_BANK' }, products: ['ACCOUNTS', 'CREDIT_CARDS'],
      });
    }
    if (url.pathname === '/accounts') {
      return json({
        totalPages: 1,
        results: [
          {
            id: 'acc-1', itemId: 'item-1', type: 'BANK', subtype: 'CHECKING_ACCOUNT',
            number: '0912/44710', name: 'Conta corrente', balance: 4863.27, currencyCode: 'BRL',
            updatedAt: '2026-08-21T06:00:00.000Z', bankData: { transferNumber: '0912/44710', overdraftContractedLimit: 8000 },
          },
          {
            id: 'card-1', itemId: 'item-1', type: 'CREDIT', subtype: 'CREDIT_CARD',
            number: '1234567890129082', name: 'Visa Infinite', balance: 3120.5,
            creditData: {
              brand: 'VISA', creditLimit: 32000, availableCreditLimit: 28879.5,
              balanceCloseDate: '2026-08-20', balanceDueDate: '2026-08-27', minimumPayment: 468.07,
            },
          },
        ],
      });
    }
    if (url.pathname === '/transactions') {
      return json({
        totalPages: 1,
        results: [
          {
            id: 'tx-1', accountId: url.searchParams.get('accountId'), description: 'PIX ENVIADO',
            amount: -250.9, date: '2026-08-10T00:00:00.000Z', category: 'Transfers', type: 'DEBIT',
            balance: 4863.27, paymentData: { paymentMethod: 'PIX', receiver: { name: 'PADARIA REAL' } },
          },
          {
            id: 'tx-2', accountId: url.searchParams.get('accountId'), description: 'SALARIO',
            amount: 12480, date: '2026-08-05T00:00:00.000Z', category: 'Salary', type: 'CREDIT',
          },
        ],
      });
    }
    if (url.pathname === '/bills') {
      return json({
        totalPages: 1,
        results: [{ id: 'bill-1', dueDate: '2026-08-27T00:00:00.000Z', totalAmount: 3120.5, minimumPaymentAmount: 468.07 }],
      });
    }
    if (url.pathname === '/investments') {
      return json({
        totalPages: 1,
        results: [{
          id: 'inv-1', itemId: 'item-1', name: 'Tesouro Selic 2029', type: 'SECURITY',
          balance: 52340.11, amount: 48000, dueDate: '2029-03-01', date: '2026-08-21T00:00:00.000Z',
        }],
      });
    }
    if (url.pathname === '/loans') {
      return json({
        totalPages: 1,
        results: [{
          id: 'loan-1', itemId: 'item-1', productName: 'Consignado', contractAmount: 40000,
          outstandingBalance: 22435, installmentValue: 897.4, totalNumberOfInstallments: 60,
          paidInstallments: 34, dueDate: '2026-09-25', interestRates: [{ rate: 1.79, taxPeriodicity: 'MONTHLY' }],
        }],
      });
    }
    return new Response('{}', { status: 404 });
  }) as typeof fetch;
}

function criar(chamadas: Chamada[]): PluggyProvider {
  const cliente = new ClientePluggy({
    clientId: 'id', clientSecret: 'segredo', baseUrl: 'https://api.pluggy.ai', fetchImpl: stubFetch(chamadas),
  });
  return new PluggyProvider(cliente, ['item-1']);
}

test('o adaptador so emite GET, exceto a autenticacao', async () => {
  const chamadas: Chamada[] = [];
  const p = criar(chamadas);

  await p.listarInstituicoes();
  await p.listarContas();
  await p.listarCartoes();
  await p.listarTransacoes({ de: '2026-08-01', ate: '2026-08-31' });
  await p.listarFaturas();
  await p.listarInvestimentos();
  await p.listarEmprestimos();
  await p.listarAgendamentos();

  const escritas = chamadas.filter((c) => c.metodo !== 'GET');
  assert.deepEqual(escritas.map((c) => c.caminho), ['/auth'], 'houve requisicao de escrita fora do /auth');
  const caminhos = new Set(chamadas.map((c) => c.caminho));
  for (const esperado of ['/items/item-1', '/accounts', '/transactions', '/bills', '/investments', '/loans']) {
    assert.ok(caminhos.has(esperado), `nao consultou ${esperado}`);
  }
  // /items e /accounts sao cacheados por 5 minutos: nao se repetem a cada chamada.
  assert.equal(chamadas.filter((c) => c.caminho === '/accounts').length, 1);
});

test('conexao sem item configurado falha com mensagem util', () => {
  const cliente = new ClientePluggy({ clientId: 'a', clientSecret: 'b', baseUrl: 'x', fetchImpl: stubFetch([]) });
  assert.throws(() => new PluggyProvider(cliente, []), /PLUGGY_ITEM_IDS/);
});

test('contas e cartoes saem separados e em centavos', async () => {
  const p = criar([]);
  const contas = await p.listarContas();
  assert.equal(contas.length, 1);
  assert.equal(contas[0]!.saldo, 486327);
  assert.equal(contas[0]!.numero, '****0910'.replace('0910', '4710'));
  assert.equal(contas[0]!.limiteChequeEspecial, 800000);
  assert.equal(contas[0]!.saldoDisponivel, 486327 + 800000);

  const cartoes = await p.listarCartoes();
  assert.equal(cartoes.length, 1);
  assert.equal(cartoes[0]!.finalNumero, '9082');
  assert.equal(cartoes[0]!.limiteTotal, 3200000);
  assert.equal(cartoes[0]!.diaFechamento, 20);
  assert.equal(cartoes[0]!.diaVencimento, 27);
});

test('o tipo DEBIT/CREDIT manda sobre o sinal do valor', () => {
  const debito = mapearTransacao(
    { id: 'x', accountId: 'a', amount: 100, type: 'DEBIT', date: '2026-08-01' }, 'Itau', false,
  );
  assert.equal(debito.valor, -10000, 'DEBIT com valor positivo deveria virar saida');

  const credito = mapearTransacao(
    { id: 'y', accountId: 'a', amount: -50, type: 'CREDIT', date: '2026-08-01' }, 'Itau', false,
  );
  assert.equal(credito.valor, 5000);
});

test('a fatura junta valor oficial com os lancamentos do ciclo', async () => {
  const p = criar([]);
  const faturas = await p.listarFaturas();
  assert.equal(faturas.length, 1);
  const f = faturas[0]!;
  assert.equal(f.valorTotal, 312050);
  assert.equal(f.valorMinimo, 46807);
  assert.equal(f.dataVencimento, '2026-08-27');
  assert.ok(f.dataFechamento < f.dataVencimento);
  for (const l of f.lancamentos) assert.equal(l.metodo, 'cartao_credito');
});

test('investimento e emprestimo chegam com os campos que as ferramentas usam', async () => {
  const p = criar([]);
  const [inv] = await p.listarInvestimentos();
  assert.equal(inv!.valorAtual, 5234011);
  assert.equal(inv!.valorAplicado, 4800000);
  assert.equal(inv!.liquidez, 'no_vencimento');

  const [emp] = await p.listarEmprestimos();
  assert.equal(emp!.saldoDevedor, 2243500);
  assert.equal(emp!.valorParcela, 89740);
  assert.equal(emp!.taxaJurosMensal, 1.79);
});

test('erro HTTP da Pluggy vira mensagem com status e caminho', async () => {
  const cliente = new ClientePluggy({
    clientId: 'id', clientSecret: 'segredo', baseUrl: 'https://api.pluggy.ai',
    fetchImpl: (async (entrada: string | URL) => {
      const url = new URL(entrada.toString());
      if (url.pathname === '/auth') {
        return new Response(JSON.stringify({ apiKey: 'k' }), { status: 200 });
      }
      return new Response('{"message":"item not found"}', { status: 404 });
    }) as typeof fetch,
  });
  await assert.rejects(
    () => new PluggyProvider(cliente, ['item-x']).listarContas(),
    /Pluggy respondeu 404 em \/items\/item-x/,
  );
});
