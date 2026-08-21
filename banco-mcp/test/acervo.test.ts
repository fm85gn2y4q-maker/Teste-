import { test } from 'node:test';
import assert from 'node:assert/strict';
import { acervoMock } from '../src/providers/mock/acervo.js';
import { MockProvider } from '../src/providers/mock/provider.js';
import { levantarGastos, levantarPatrimonio } from '../src/analise/consolidado.js';
import { detectarRecorrentes } from '../src/analise/gastos.js';
import { resolverPeriodo } from '../src/util/datas.js';

const HOJE = '2026-08-21';
const acervo = acervoMock({ hoje: HOJE, semente: 42 });

test('o acervo cobre 14 meses e nao tem lancamento no futuro', () => {
  assert.ok(acervo.transacoes.length > 500, `poucas transacoes: ${acervo.transacoes.length}`);
  const ultima = acervo.transacoes[acervo.transacoes.length - 1]!;
  assert.ok(ultima.data <= HOJE, `lancamento no futuro: ${ultima.data}`);
  const primeira = acervo.transacoes[0]!;
  assert.ok(primeira.data >= '2025-07-01' && primeira.data < '2025-08-01', primeira.data);
});

test('o saldo de cada conta fecha com o extrato', () => {
  for (const conta of acervo.contas) {
    const doExtrato = acervo.transacoes.filter((t) => t.contaId === conta.id);
    const ultimo = doExtrato[doExtrato.length - 1];
    assert.ok(ultimo, `conta sem movimento: ${conta.id}`);
    assert.equal(conta.saldo, ultimo.saldoApos, `saldo divergente em ${conta.id}`);
  }
});

test('o total da fatura e a soma dos lancamentos dela', () => {
  for (const f of acervo.faturas) {
    const somaLanc = f.lancamentos.reduce((a, t) => a + Math.abs(t.valor), 0);
    assert.equal(f.valorTotal, somaLanc, `fatura ${f.id} nao fecha`);
    assert.ok(f.dataVencimento > f.dataFechamento, `vencimento antes do fechamento em ${f.id}`);
  }
});

test('nenhuma compra de cartao entra em duas faturas', () => {
  const vistos = new Set<string>();
  for (const f of acervo.faturas) {
    for (const t of f.lancamentos) {
      assert.ok(!vistos.has(t.id), `lancamento ${t.id} repetido em ${f.id}`);
      vistos.add(t.id);
    }
  }
});

test('limite disponivel do cartao desconta o que ainda nao foi pago', () => {
  for (const c of acervo.cartoes) {
    const emAberto = acervo.faturas
      .filter((f) => f.cartaoId === c.id && (f.status === 'aberta' || f.status === 'fechada'))
      .reduce((a, f) => a + f.valorTotal, 0);
    assert.equal(c.limiteDisponivel, Math.max(0, c.limiteTotal - emAberto));
    assert.ok(c.limiteDisponivel <= c.limiteTotal);
  }
});

test('levantarGastos nao conta a mesma compra duas vezes', async () => {
  const provider = new MockProvider({ hoje: HOJE, semente: 42 });
  const periodo = resolverPeriodo({ mes: '2026-06' }, HOJE);
  const gastos = await levantarGastos(provider, periodo);

  const pagamentoDeFatura = gastos.saidas.filter((t) => t.categoria === 'Cartao de credito');
  assert.equal(pagamentoDeFatura.length, 0, 'debito da fatura entrou junto com as compras');

  const transferencias = gastos.saidas.filter((t) => t.categoria === 'Transferencia');
  assert.equal(transferencias.length, 0, 'transferencia entre contas proprias contada como gasto');

  const comCartao = gastos.saidas.filter((t) => t.metodo === 'cartao_credito');
  assert.ok(comCartao.length > 0, 'compras de cartao nao entraram');
  assert.ok(gastos.totalSaidas > 0);
});

test('patrimonio liquido desconta fatura em aberto e divida', async () => {
  const provider = new MockProvider({ hoje: HOJE, semente: 42 });
  const p = await levantarPatrimonio(provider);
  assert.equal(p.liquido, p.emConta + p.investido - p.faturasEmAberto - p.dividas);
  assert.ok(p.investido > 0 && p.dividas > 0);
});

test('assinatura mensal e reconhecida como recorrencia', () => {
  const doCartao = acervo.faturas.flatMap((f) => f.lancamentos);
  const recorrentes = detectarRecorrentes([...acervo.transacoes, ...doCartao]);
  const nomes = recorrentes.map((r) => r.descricao.toUpperCase());
  assert.ok(nomes.some((n) => n.includes('NETFLIX')), `Netflix nao detectada: ${nomes.join(', ')}`);
  assert.ok(nomes.some((n) => n.includes('SPOTIFY')), 'Spotify nao detectada');
  const netflix = recorrentes.find((r) => r.descricao.toUpperCase().includes('NETFLIX'))!;
  assert.ok(netflix.intervaloDias >= 25 && netflix.intervaloDias <= 35, `intervalo estranho: ${netflix.intervaloDias}`);
});

test('mesma semente produz o mesmo acervo', () => {
  const a = acervoMock({ hoje: HOJE, semente: 7 });
  const b = acervoMock({ hoje: HOJE, semente: 7 });
  assert.equal(a.transacoes.length, b.transacoes.length);
  assert.deepEqual(a.contas.map((c) => c.saldo), b.contas.map((c) => c.saldo));
});
