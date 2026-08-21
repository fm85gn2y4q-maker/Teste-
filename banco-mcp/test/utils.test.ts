import { test } from 'node:test';
import assert from 'node:assert/strict';
import { brl, paraCentavos, soma, variacao } from '../src/util/dinheiro.js';
import {
  diferencaEmDias, mesesEntre, montarDia, periodoAnterior, resolverPeriodo, somarDias, somarMeses,
} from '../src/util/datas.js';
import { aplicarFiltro, normalizar } from '../src/providers/filtro.js';

test('brl formata centavos no padrao brasileiro', () => {
  assert.equal(brl(0), 'R$ 0,00');
  assert.equal(brl(5), 'R$ 0,05');
  assert.equal(brl(123456), 'R$ 1.234,56');
  assert.equal(brl(-123456), '-R$ 1.234,56');
  assert.equal(brl(100000000), 'R$ 1.000.000,00');
});

test('paraCentavos aceita numero e string brasileira', () => {
  assert.equal(paraCentavos(1234.56), 123456);
  assert.equal(paraCentavos('1.234,56'), 123456);
  assert.equal(paraCentavos('R$ 89,90'), 8990);
  // O ponto flutuante classico: 0.1 + 0.2 nao pode virar 30 centavos errados.
  assert.equal(soma([paraCentavos(0.1), paraCentavos(0.2)]), 30);
});

test('variacao tolera base zero', () => {
  assert.equal(variacao(0, 100), null);
  assert.equal(variacao(100, 150), 50);
});

test('montarDia nunca estoura o fim do mes', () => {
  assert.equal(montarDia(2026, 2, 31), '2026-02-28');
  assert.equal(montarDia(2024, 2, 30), '2024-02-29');
  assert.equal(montarDia(2026, 4, 31), '2026-04-30');
});

test('aritmetica de datas nao escorrega no fim do ano', () => {
  assert.equal(somarDias('2025-12-31', 1), '2026-01-01');
  assert.equal(somarDias('2026-01-01', -1), '2025-12-31');
  assert.equal(somarMeses('2026-01', -1), '2025-12');
  assert.equal(somarMeses('2026-12', 1), '2027-01');
  assert.equal(diferencaEmDias('2026-01-01', '2026-03-01'), 59);
});

test('resolverPeriodo cobre os atalhos', () => {
  const hoje = '2026-08-21';
  assert.deepEqual(
    { ...resolverPeriodo({ periodo: 'mes_passado' }, hoje) },
    { de: '2026-07-01', ate: '2026-07-31', rotulo: 'julho/2026' },
  );
  assert.equal(resolverPeriodo({ periodo: 'mes_atual' }, hoje).de, '2026-08-01');
  assert.equal(resolverPeriodo({ periodo: 'ultimos_30_dias' }, hoje).de, '2026-07-23');
  assert.equal(resolverPeriodo({ mes: '2026-02' }, hoje).ate, '2026-02-28');
  assert.equal(resolverPeriodo({ periodo: 'ultimos_12_meses' }, hoje).de, '2025-09-01');
});

test('resolverPeriodo recusa periodo invertido', () => {
  assert.throws(() => resolverPeriodo({ de: '2026-05-01', ate: '2026-04-01' }), /invertido/);
});

test('periodoAnterior tem o mesmo tamanho e nao se sobrepoe', () => {
  const p = resolverPeriodo({ mes: '2026-03' }, '2026-08-21');
  const anterior = periodoAnterior(p);
  assert.equal(anterior.ate, '2026-02-28');
  assert.equal(diferencaEmDias(anterior.de, anterior.ate), diferencaEmDias(p.de, p.ate));
});

test('mesesEntre lista os meses em ordem', () => {
  assert.deepEqual(mesesEntre('2025-11-15', '2026-02-03'), ['2025-11', '2025-12', '2026-01', '2026-02']);
});

test('busca livre ignora acento e caixa', () => {
  assert.equal(normalizar('Alimentação'), 'alimentacao');
  const t = [{
    id: '1', contaId: 'c', instituicao: 'X', data: '2026-08-01',
    descricao: 'PADARIA SÃO JOSÉ', valor: -1000, metodo: 'pix' as const, categoria: 'Alimentação',
  }];
  assert.equal(aplicarFiltro(t, { de: '2026-08-01', ate: '2026-08-31', texto: 'sao jose' }).length, 1);
  assert.equal(aplicarFiltro(t, { de: '2026-08-01', ate: '2026-08-31', categoria: 'alimentacao' }).length, 1);
  assert.equal(aplicarFiltro(t, { de: '2026-08-01', ate: '2026-08-31', apenas: 'entradas' }).length, 0);
});
