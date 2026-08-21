import { criarRng, type Rng } from './rng.js';
import { ASSINATURAS, CARTAO_TODOS, sortearPorPeso } from './catalogo.js';
import {
  hojeISO, mesDe, mesesEntre, montarDia, somarDias, somarMeses, ultimoDia,
} from '../../util/datas.js';
import type {
  Agendamento, Cartao, Conta, Emprestimo, Fatura, Instituicao, Investimento, Transacao,
} from '../types.js';

export interface Acervo {
  hoje: string;
  instituicoes: Instituicao[];
  contas: Conta[];
  transacoes: Transacao[];
  cartoes: Cartao[];
  faturas: Fatura[];
  investimentos: Investimento[];
  emprestimos: Emprestimo[];
  agendamentos: Agendamento[];
}

const MESES_DE_HISTORICO = 14;

/** Um lancamento recorrente do dia a dia de uma familia de classe media. */
interface Recorrente {
  contaId: string;
  dia: number;
  descricao: string;
  contraparte?: string;
  categoria: string;
  metodo: Transacao['metodo'];
  min: number;
  max: number;
  /** Sinal ja embutido: negativo e saida. */
  sinal: 1 | -1;
  /** Comeca a valer a partir deste mes (YYYY-MM), se houver. */
  desde?: string;
}

function recorrentes(mesInicial: string): Recorrente[] {
  return [
    { contaId: 'itau-cc', dia: 5, descricao: 'SALARIO MENSAL', contraparte: 'TECNOVA SISTEMAS LTDA', categoria: 'Salario', metodo: 'salario', min: 1_248_000, max: 1_248_000, sinal: 1 },
    { contaId: 'itau-cc', dia: 20, descricao: 'PRO-LABORE', contraparte: 'MENEGATTI CONSULTORIA ME', categoria: 'Renda extra', metodo: 'pix', min: 180_000, max: 420_000, sinal: 1 },
    { contaId: 'itau-cc', dia: 10, descricao: 'ALUGUEL RESIDENCIAL', contraparte: 'IMOBILIARIA VILA NOVA', categoria: 'Moradia', metodo: 'boleto', min: 235_000, max: 235_000, sinal: -1 },
    { contaId: 'itau-cc', dia: 10, descricao: 'CONDOMINIO EDIF ATLANTICA', categoria: 'Moradia', metodo: 'boleto', min: 68_000, max: 74_500, sinal: -1 },
    { contaId: 'itau-cc', dia: 15, descricao: 'LIGHT SERVICOS DE ELETRICIDADE', categoria: 'Moradia', metodo: 'debito_automatico', min: 18_400, max: 34_900, sinal: -1 },
    { contaId: 'itau-cc', dia: 16, descricao: 'CEDAE SANEAMENTO', categoria: 'Moradia', metodo: 'debito_automatico', min: 9_800, max: 16_200, sinal: -1 },
    { contaId: 'itau-cc', dia: 20, descricao: 'VIVO FIBRA 700MB', categoria: 'Moradia', metodo: 'debito_automatico', min: 13_990, max: 13_990, sinal: -1 },
    { contaId: 'itau-cc', dia: 8, descricao: 'BRADESCO SAUDE PLANO FAMILIA', categoria: 'Saude', metodo: 'debito_automatico', min: 189_000, max: 214_000, sinal: -1 },
    { contaId: 'itau-cc', dia: 7, descricao: 'COLEGIO SAO VICENTE MENSALIDADE', categoria: 'Educacao', metodo: 'boleto', min: 148_000, max: 159_000, sinal: -1 },
    { contaId: 'itau-cc', dia: 6, descricao: 'APLICACAO PROGRAMADA XP', contraparte: 'XP INVESTIMENTOS CCTVM', categoria: 'Investimentos', metodo: 'ted', min: 200_000, max: 200_000, sinal: -1 },
    { contaId: 'itau-cc', dia: 5, descricao: 'PIX ENVIADO - CONTA NUBANK', contraparte: 'NU PAGAMENTOS SA', categoria: 'Transferencia', metodo: 'pix', min: 150_000, max: 150_000, sinal: -1 },
    { contaId: 'nubank-cp', dia: 5, descricao: 'PIX RECEBIDO - ITAU', contraparte: 'ITAU UNIBANCO SA', categoria: 'Transferencia', metodo: 'pix', min: 150_000, max: 150_000, sinal: 1 },
    { contaId: 'itau-cc', dia: 25, descricao: 'CONSIGNADO ITAU PARCELA', categoria: 'Emprestimos', metodo: 'debito_automatico', min: 89_740, max: 89_740, sinal: -1 },
    { contaId: 'itau-cc', dia: 12, descricao: 'FINANCIAMENTO VEICULAR PARCELA', categoria: 'Emprestimos', metodo: 'debito_automatico', min: 132_500, max: 132_500, sinal: -1 },
    { contaId: 'inter-cc', dia: 28, descricao: 'RENDIMENTO CDB LIQUIDEZ DIARIA', categoria: 'Rendimentos', metodo: 'rendimento', min: 42_000, max: 78_000, sinal: 1 },
    { contaId: 'itau-poup', dia: 3, descricao: 'RENDIMENTO POUPANCA', categoria: 'Rendimentos', metodo: 'rendimento', min: 3_100, max: 5_900, sinal: 1 },
    { contaId: 'itau-cc', dia: 1, descricao: 'TARIFA PACOTE DE SERVICOS', categoria: 'Tarifas', metodo: 'tarifa', min: 4_990, max: 4_990, sinal: -1, desde: somarMeses(mesInicial, 3) },
  ];
}

function instituicoes(hoje: string): Instituicao[] {
  const conectadaEm = somarDias(hoje, -212);
  return [
    {
      id: 'itau', nome: 'Itau Unibanco', tipo: 'banco', codigo: '341',
      conectadaEm, status: 'ativa',
      consentimentoExpiraEm: somarDias(conectadaEm, 365),
      ultimaSincronizacao: `${hoje}T06:12:00-03:00`,
      escopos: ['contas', 'cartoes', 'credito'],
    },
    {
      id: 'nubank', nome: 'Nubank', tipo: 'fintech', codigo: '260',
      conectadaEm: somarDias(hoje, -198), status: 'ativa',
      consentimentoExpiraEm: somarDias(hoje, 167),
      ultimaSincronizacao: `${hoje}T06:12:30-03:00`,
      escopos: ['contas', 'cartoes'],
    },
    {
      id: 'inter', nome: 'Banco Inter', tipo: 'banco', codigo: '077',
      conectadaEm: somarDias(hoje, -96), status: 'ativa',
      consentimentoExpiraEm: somarDias(hoje, 269),
      ultimaSincronizacao: `${hoje}T06:13:05-03:00`,
      escopos: ['contas', 'investimentos'],
    },
    {
      id: 'xp', nome: 'XP Investimentos', tipo: 'corretora', codigo: '102',
      conectadaEm: somarDias(hoje, -96), status: 'ativa',
      consentimentoExpiraEm: somarDias(hoje, 269),
      ultimaSincronizacao: `${hoje}T06:13:40-03:00`,
      escopos: ['investimentos'],
    },
    {
      id: 'bb', nome: 'Banco do Brasil', tipo: 'banco', codigo: '001',
      conectadaEm: somarDias(hoje, -401), status: 'expirada',
      consentimentoExpiraEm: somarDias(hoje, -36),
      ultimaSincronizacao: `${somarDias(hoje, -36)}T06:11:00-03:00`,
      escopos: ['contas'],
    },
  ];
}

const CONTAS_BASE: Array<Omit<Conta, 'saldo' | 'saldoDisponivel' | 'atualizadoEm'>> = [
  { id: 'itau-cc', instituicaoId: 'itau', instituicao: 'Itau Unibanco', tipo: 'corrente', apelido: 'Conta principal', agencia: '0912', numero: '****-4471', moeda: 'BRL', limiteChequeEspecial: 800_000 },
  { id: 'itau-poup', instituicaoId: 'itau', instituicao: 'Itau Unibanco', tipo: 'poupanca', apelido: 'Reserva escola', agencia: '0912', numero: '****-4471-9', moeda: 'BRL' },
  { id: 'nubank-cp', instituicaoId: 'nubank', instituicao: 'Nubank', tipo: 'pagamento', apelido: 'Dia a dia', numero: '****-8830', moeda: 'BRL' },
  { id: 'inter-cc', instituicaoId: 'inter', instituicao: 'Banco Inter', tipo: 'corrente', apelido: 'Reserva de emergencia', agencia: '0001', numero: '****-2265', moeda: 'BRL' },
];

const SALDO_INICIAL: Record<string, number> = {
  'itau-cc': 486_300,
  'itau-poup': 1_240_000,
  'nubank-cp': 78_400,
  'inter-cc': 4_820_000,
};

const CARTOES: Cartao[] = [
  { id: 'nubank-mc', instituicaoId: 'nubank', instituicao: 'Nubank', apelido: 'Nubank Ultravioleta', bandeira: 'Mastercard', finalNumero: '4417', limiteTotal: 1_800_000, limiteDisponivel: 0, diaFechamento: 28, diaVencimento: 5, titularidade: 'titular' },
  { id: 'itau-visa', instituicaoId: 'itau', instituicao: 'Itau Unibanco', apelido: 'Itau Visa Infinite', bandeira: 'Visa', finalNumero: '9082', limiteTotal: 3_200_000, limiteDisponivel: 0, diaFechamento: 20, diaVencimento: 27, titularidade: 'titular' },
];

function gerarTransacoesConta(
  rng: Rng,
  hoje: string,
  meses: string[],
): Transacao[] {
  const out: Transacao[] = [];
  const regras = recorrentes(meses[0]!);
  let seq = 0;

  for (const mes of meses) {
    const ano = Number(mes.slice(0, 4));
    const m = Number(mes.slice(5, 7));

    for (const r of regras) {
      if (r.desde && mes < r.desde) continue;
      const data = montarDia(ano, m, r.dia);
      if (data > hoje) continue;
      const bruto = rng.centavos(r.min, r.max);
      out.push({
        id: `tx-${++seq}`,
        contaId: r.contaId,
        instituicao: contaPara(r.contaId).instituicao,
        data,
        descricao: r.descricao,
        ...(r.contraparte ? { contraparte: r.contraparte } : {}),
        valor: bruto * r.sinal,
        metodo: r.metodo,
        categoria: r.categoria,
      });
    }

    // Gastos avulsos no debito/PIX da conta Nubank: o dia a dia.
    const avulsos = rng.inteiro(14, 26);
    for (let i = 0; i < avulsos; i++) {
      const dia = rng.inteiro(1, 28);
      const data = montarDia(ano, m, dia);
      if (data > hoje) continue;
      const est = sortearPorPeso(CARTAO_TODOS, rng.proximo());
      const pix = rng.chance(0.45);
      out.push({
        id: `tx-${++seq}`,
        contaId: 'nubank-cp',
        instituicao: 'Nubank',
        data,
        descricao: pix ? `PIX ENVIADO - ${est.nome}` : est.nome,
        contraparte: est.nome,
        valor: -rng.centavos(est.min, Math.min(est.max, 60_000)),
        metodo: pix ? 'pix' : 'cartao_debito',
        categoria: est.categoria,
      });
    }

    // Saques e imprevistos na conta principal.
    if (rng.chance(0.4)) {
      const data = montarDia(ano, m, rng.inteiro(2, 27));
      if (data <= hoje) {
        out.push({
          id: `tx-${++seq}`,
          contaId: 'itau-cc',
          instituicao: 'Itau Unibanco',
          data,
          descricao: 'SAQUE 24H BANCO24HORAS',
          valor: -rng.centavos(10_000, 60_000),
          metodo: 'saque',
          categoria: 'Saques',
        });
      }
    }
  }

  out.sort((a, b) => (a.data === b.data ? a.id.localeCompare(b.id) : a.data.localeCompare(b.data)));
  return out;
}

function contaPara(contaId: string): { instituicao: string } {
  const c = CONTAS_BASE.find((x) => x.id === contaId);
  if (!c) throw new Error(`Conta desconhecida no acervo mock: ${contaId}`);
  return { instituicao: c.instituicao };
}

function gerarComprasCartao(rng: Rng, hoje: string, meses: string[]): Transacao[] {
  const out: Transacao[] = [];
  let seq = 0;
  for (const cartao of CARTOES) {
    for (const mes of meses) {
      const ano = Number(mes.slice(0, 4));
      const m = Number(mes.slice(5, 7));
      const compras = cartao.id === 'nubank-mc' ? rng.inteiro(12, 22) : rng.inteiro(6, 14);
      for (let i = 0; i < compras; i++) {
        const data = montarDia(ano, m, rng.inteiro(1, 28));
        if (data > hoje) continue;
        const est = sortearPorPeso(CARTAO_TODOS, rng.proximo());
        const parcelas = est.max > 100_000 && rng.chance(0.25) ? rng.inteiro(2, 10) : 1;
        const total = rng.centavos(est.min, est.max);
        const valor = Math.round(total / parcelas);
        out.push({
          id: `cc-${cartao.id}-${++seq}`,
          contaId: cartao.id,
          instituicao: cartao.instituicao,
          data,
          descricao: parcelas > 1 ? `${est.nome} - PARCELA 1/${parcelas}` : est.nome,
          contraparte: est.nome,
          valor: -valor,
          metodo: 'cartao_credito',
          categoria: est.categoria,
          faturaDe: cartao.id,
        });
      }
      // Assinaturas caem sempre, no mesmo dia, no cartao principal.
      if (cartao.id === 'nubank-mc') {
        for (const a of ASSINATURAS) {
          const data = montarDia(ano, m, 3 + ASSINATURAS.indexOf(a));
          if (data > hoje) continue;
          out.push({
            id: `cc-${cartao.id}-${++seq}`,
            contaId: cartao.id,
            instituicao: cartao.instituicao,
            data,
            descricao: a.nome,
            contraparte: a.nome,
            valor: -rng.centavos(a.min, a.max),
            metodo: 'cartao_credito',
            categoria: a.categoria,
            faturaDe: cartao.id,
          });
        }
      }
    }
  }
  out.sort((a, b) => (a.data === b.data ? a.id.localeCompare(b.id) : a.data.localeCompare(b.data)));
  return out;
}

/**
 * Monta as faturas a partir das compras. A fatura de referencia YYYY-MM fecha
 * no dia de fechamento daquele mes e vence no vencimento seguinte; entram nela
 * as compras posteriores ao fechamento anterior.
 */
function montarFaturas(cartoes: Cartao[], compras: Transacao[], hoje: string, meses: string[]): Fatura[] {
  const faturas: Fatura[] = [];
  for (const cartao of cartoes) {
    const doCartao = compras.filter((c) => c.contaId === cartao.id);
    for (const mes of meses) {
      const ano = Number(mes.slice(0, 4));
      const m = Number(mes.slice(5, 7));
      const fechamento = montarDia(ano, m, cartao.diaFechamento);
      const fechamentoAnterior = (() => {
        const anterior = somarMeses(mes, -1);
        return montarDia(Number(anterior.slice(0, 4)), Number(anterior.slice(5, 7)), cartao.diaFechamento);
      })();
      const vencMes = cartao.diaVencimento <= cartao.diaFechamento ? somarMeses(mes, 1) : mes;
      const vencimento = montarDia(Number(vencMes.slice(0, 4)), Number(vencMes.slice(5, 7)), cartao.diaVencimento);

      const lancamentos = doCartao.filter((c) => c.data > fechamentoAnterior && c.data <= fechamento);
      if (lancamentos.length === 0 && fechamento > hoje) continue;

      const valorTotal = lancamentos.reduce((a, t) => a + Math.abs(t.valor), 0);
      const status: Fatura['status'] =
        vencimento < hoje ? 'paga' : fechamento <= hoje ? 'fechada' : 'aberta';

      faturas.push({
        id: `fat-${cartao.id}-${mes}`,
        cartaoId: cartao.id,
        cartao: cartao.apelido,
        instituicao: cartao.instituicao,
        mesReferencia: mes,
        status,
        valorTotal,
        valorMinimo: Math.round(valorTotal * 0.15),
        ...(status === 'paga' ? { valorPago: valorTotal } : {}),
        dataFechamento: fechamento,
        dataVencimento: vencimento,
        lancamentos,
      });
    }
  }
  faturas.sort((a, b) => b.mesReferencia.localeCompare(a.mesReferencia) || a.cartaoId.localeCompare(b.cartaoId));
  return faturas;
}

function gerarInvestimentos(rng: Rng, hoje: string): Investimento[] {
  const base: Array<Omit<Investimento, 'valorAtual' | 'atualizadoEm'> & { ganho: [number, number] }> = [
    { id: 'inv-1', instituicaoId: 'xp', instituicao: 'XP Investimentos', nome: 'Tesouro Selic 2029', tipo: 'tesouro_direto', valorAplicado: 4_800_000, indexador: 'SELIC + 0,04%', vencimento: '2029-03-01', liquidez: 'diaria', ganho: [0.09, 0.14] },
    { id: 'inv-2', instituicaoId: 'inter', instituicao: 'Banco Inter', nome: 'CDB Inter 110% CDI', tipo: 'cdb', valorAplicado: 3_500_000, indexador: '110% CDI', vencimento: '2027-11-20', liquidez: 'diaria', ganho: [0.08, 0.12] },
    { id: 'inv-3', instituicaoId: 'xp', instituicao: 'XP Investimentos', nome: 'LCI Habitacao 96% CDI', tipo: 'lci_lca', valorAplicado: 2_000_000, indexador: '96% CDI', vencimento: '2027-05-15', liquidez: 'no_vencimento', ganho: [0.07, 0.10] },
    { id: 'inv-4', instituicaoId: 'xp', instituicao: 'XP Investimentos', nome: 'XP Macro Plus FIC FIM', tipo: 'fundo', valorAplicado: 1_500_000, liquidez: 'd_mais_30', ganho: [-0.04, 0.16] },
    { id: 'inv-5', instituicaoId: 'xp', instituicao: 'XP Investimentos', nome: 'ITSA4', tipo: 'acao', quantidade: 1_400, valorAplicado: 1_386_000, liquidez: 'd_mais_1', ganho: [-0.12, 0.28] },
    { id: 'inv-6', instituicaoId: 'xp', instituicao: 'XP Investimentos', nome: 'PETR4', tipo: 'acao', quantidade: 500, valorAplicado: 1_920_000, liquidez: 'd_mais_1', ganho: [-0.18, 0.34] },
    { id: 'inv-7', instituicaoId: 'xp', instituicao: 'XP Investimentos', nome: 'HGLG11', tipo: 'fii', quantidade: 90, valorAplicado: 1_431_000, liquidez: 'd_mais_1', ganho: [-0.08, 0.14] },
    { id: 'inv-8', instituicaoId: 'xp', instituicao: 'XP Investimentos', nome: 'MXRF11', tipo: 'fii', quantidade: 900, valorAplicado: 918_000, liquidez: 'd_mais_1', ganho: [-0.06, 0.11] },
    { id: 'inv-9', instituicaoId: 'xp', instituicao: 'XP Investimentos', nome: 'XP Seguros Previdencia PGBL', tipo: 'previdencia', valorAplicado: 6_200_000, liquidez: 'carencia', ganho: [0.05, 0.13] },
  ];
  return base.map((b) => {
    const { ganho, ...resto } = b;
    const fator = 1 + (ganho[0] + rng.proximo() * (ganho[1] - ganho[0]));
    return { ...resto, valorAtual: Math.round(b.valorAplicado * fator), atualizadoEm: hoje };
  });
}

function gerarEmprestimos(hoje: string): Emprestimo[] {
  return [
    {
      id: 'emp-1', instituicaoId: 'itau', instituicao: 'Itau Unibanco', tipo: 'consignado',
      descricao: 'Credito consignado privado', valorContratado: 4_000_000, saldoDevedor: 2_243_500,
      taxaJurosMensal: 1.79, cetAnual: 24.6, valorParcela: 89_740, parcelasTotais: 60, parcelasPagas: 34,
      proximoVencimento: proximoDiaDoMes(hoje, 25),
    },
    {
      id: 'emp-2', instituicaoId: 'itau', instituicao: 'Itau Unibanco', tipo: 'financiamento_veicular',
      descricao: 'Financiamento veiculo - CDC 48x', valorContratado: 5_600_000, saldoDevedor: 2_915_000,
      taxaJurosMensal: 1.42, cetAnual: 19.8, valorParcela: 132_500, parcelasTotais: 48, parcelasPagas: 26,
      proximoVencimento: proximoDiaDoMes(hoje, 12),
    },
  ];
}

function proximoDiaDoMes(hoje: string, dia: number): string {
  const mes = mesDe(hoje);
  const candidato = montarDia(Number(mes.slice(0, 4)), Number(mes.slice(5, 7)), dia);
  if (candidato >= hoje) return candidato;
  const prox = somarMeses(mes, 1);
  return montarDia(Number(prox.slice(0, 4)), Number(prox.slice(5, 7)), dia);
}

function gerarAgendamentos(hoje: string): Agendamento[] {
  return [
    { id: 'ag-1', instituicaoId: 'itau', instituicao: 'Itau Unibanco', contaId: 'itau-cc', descricao: 'IPTU 2026 - cota 7/10', valor: -48_600, data: proximoDiaDoMes(hoje, 15), categoria: 'Impostos', recorrente: true, frequencia: 'mensal' },
    { id: 'ag-2', instituicaoId: 'itau', instituicao: 'Itau Unibanco', contaId: 'itau-cc', descricao: 'IPVA 2026 - parcela 3/3', valor: -139_400, data: proximoDiaDoMes(hoje, 18), categoria: 'Impostos', recorrente: false },
    { id: 'ag-3', instituicaoId: 'nubank', instituicao: 'Nubank', contaId: 'nubank-cp', descricao: 'Fatura Nubank Ultravioleta (debito automatico)', valor: 0, data: proximoDiaDoMes(hoje, 5), categoria: 'Cartao', recorrente: true, frequencia: 'mensal' },
    { id: 'ag-4', instituicaoId: 'inter', instituicao: 'Banco Inter', contaId: 'inter-cc', descricao: 'Seguro residencial Porto', valor: -8_940, data: proximoDiaDoMes(hoje, 22), categoria: 'Seguros', recorrente: true, frequencia: 'mensal' },
  ];
}

let cache: Acervo | null = null;

/** Gera (e memoiza) o acervo sintetico completo. */
export function acervoMock(opcoes: { hoje?: string; semente?: number } = {}): Acervo {
  const hoje = opcoes.hoje ?? hojeISO();
  const semente = opcoes.semente ?? 20260821;
  if (cache && cache.hoje === hoje && !opcoes.semente) return cache;

  const rng = criarRng(semente);
  const mesInicial = somarMeses(mesDe(hoje), -(MESES_DE_HISTORICO - 1));
  const meses = mesesEntre(`${mesInicial}-01`, hoje);

  const transacoes = gerarTransacoesConta(rng, hoje, meses);
  const compras = gerarComprasCartao(rng, hoje, meses);

  // Debito da fatura na conta: cai no vencimento, com o valor real da fatura.
  const faturas = montarFaturas(CARTOES, compras, hoje, meses);
  let seqPg = 0;
  for (const f of faturas) {
    if (f.status !== 'paga' || f.valorTotal === 0) continue;
    const contaDebito = f.cartaoId === 'nubank-mc' ? 'nubank-cp' : 'itau-cc';
    transacoes.push({
      id: `pg-${++seqPg}`,
      contaId: contaDebito,
      instituicao: f.instituicao,
      data: f.dataVencimento,
      descricao: `PAGAMENTO FATURA ${f.cartao.toUpperCase()}`,
      valor: -f.valorTotal,
      metodo: 'debito_automatico',
      categoria: 'Cartao de credito',
    });
  }
  transacoes.sort((a, b) => (a.data === b.data ? a.id.localeCompare(b.id) : a.data.localeCompare(b.data)));

  // Saldos: parte do saldo inicial e roda o extrato inteiro.
  const saldoCorrente = new Map<string, number>(Object.entries(SALDO_INICIAL));
  for (const t of transacoes) {
    const atual = (saldoCorrente.get(t.contaId) ?? 0) + t.valor;
    saldoCorrente.set(t.contaId, atual);
    t.saldoApos = atual;
  }

  const contas: Conta[] = CONTAS_BASE.map((c) => {
    const saldo = saldoCorrente.get(c.id) ?? 0;
    return {
      ...c,
      saldo,
      saldoDisponivel: saldo + (c.limiteChequeEspecial ?? 0),
      atualizadoEm: `${hoje}T06:13:40-03:00`,
    };
  });

  // Limite disponivel do cartao = limite - fatura aberta - fechada nao paga.
  const cartoes: Cartao[] = CARTOES.map((c) => {
    const comprometido = faturas
      .filter((f) => f.cartaoId === c.id && (f.status === 'aberta' || f.status === 'fechada'))
      .reduce((a, f) => a + f.valorTotal, 0);
    return { ...c, limiteDisponivel: Math.max(0, c.limiteTotal - comprometido) };
  });

  const acervo: Acervo = {
    hoje,
    instituicoes: instituicoes(hoje),
    contas,
    transacoes,
    cartoes,
    faturas,
    investimentos: gerarInvestimentos(rng, hoje),
    emprestimos: gerarEmprestimos(hoje),
    agendamentos: gerarAgendamentos(hoje),
  };

  if (!opcoes.semente) cache = acervo;
  return acervo;
}

export function limparCacheMock(): void {
  cache = null;
}

export const _internos = { montarFaturas, ultimoDia };
