import { soma } from '../util/dinheiro.js';
import { aplicarFiltro } from '../providers/filtro.js';
import type { BankProvider, Centavos, Transacao } from '../providers/types.js';
import type { Periodo } from '../util/datas.js';

/** Categorias que nao sao consumo: movem dinheiro de lugar, nao o gastam. */
export const CATEGORIAS_NAO_CONSUMO = new Set(['Transferencia', 'Cartao de credito']);
export const CATEGORIA_APLICACAO = 'Investimentos';

export interface OpcoesGasto {
  /** Somar as compras de cartao no lugar do debito da fatura. Padrao: true. */
  incluirCartao?: boolean;
  /** Contar aplicacao financeira como gasto. Padrao: false. */
  incluirAplicacoes?: boolean;
  instituicaoId?: string;
  contaId?: string;
}

export interface Gastos {
  saidas: Transacao[];
  entradas: Transacao[];
  totalSaidas: Centavos;
  totalEntradas: Centavos;
  notas: string[];
}

/**
 * Monta a visao economica do periodo, que e onde quase toda analise de extrato
 * erra: a mesma compra aparece duas vezes — uma na fatura do cartao, outra no
 * debito da fatura na conta. Aqui, por padrao, entra a compra e sai o debito.
 * Transferencia entre contas do proprio titular tambem nao e gasto.
 */
export async function levantarGastos(
  provider: BankProvider,
  periodo: Periodo,
  opcoes: OpcoesGasto = {},
): Promise<Gastos> {
  const incluirCartao = opcoes.incluirCartao ?? true;
  const incluirAplicacoes = opcoes.incluirAplicacoes ?? false;
  const notas: string[] = [];

  const movimentos = await provider.listarTransacoes({
    de: periodo.de,
    ate: periodo.ate,
    ...(opcoes.contaId ? { contaId: opcoes.contaId } : {}),
    ...(opcoes.instituicaoId ? { instituicaoId: opcoes.instituicaoId } : {}),
  });

  let saidas = movimentos.filter((t) => t.valor < 0);
  const entradas = movimentos.filter((t) => t.valor > 0 && !CATEGORIAS_NAO_CONSUMO.has(t.categoria));

  const antesFiltro = saidas.length;
  saidas = saidas.filter((t) => !CATEGORIAS_NAO_CONSUMO.has(t.categoria));
  if (antesFiltro !== saidas.length) {
    notas.push(
      'Pagamento de fatura e transferencia entre contas proprias ficaram de fora: nao sao gasto novo, ' +
      'sao o mesmo dinheiro mudando de lugar.',
    );
  }

  if (!incluirAplicacoes) {
    const antes = saidas.length;
    saidas = saidas.filter((t) => t.categoria !== CATEGORIA_APLICACAO);
    if (antes !== saidas.length) {
      notas.push('Aplicacoes financeiras nao entram como gasto (o dinheiro continua seu).');
    }
  }

  if (incluirCartao) {
    const cartoes = await provider.listarCartoes();
    const faturas = await provider.listarFaturas();
    const compras = faturas
      .flatMap((f) => f.lancamentos)
      .filter((t) => (!opcoes.instituicaoId || cartaoDaInstituicao(cartoes, t.contaId, opcoes.instituicaoId)));
    const noPeriodo = aplicarFiltro(compras, { de: periodo.de, ate: periodo.ate });

    // Conta de cartao tambem tem credito: estorno, cashback e o proprio
    // pagamento da fatura. Somar isso como gasto inverte o sinal do mes.
    const debitos = noPeriodo.filter((t) => t.valor < 0);
    const creditos = noPeriodo.filter((t) => t.valor > 0);

    if (debitos.length > 0) {
      notas.push(`Compras de cartao de credito somadas pela data da compra (${debitos.length} lancamentos).`);
      saidas = [...saidas, ...debitos];
    }
    if (creditos.length > 0) {
      const total = soma(creditos.map((t) => t.valor));
      notas.push(
        `${creditos.length} creditos no cartao (estorno, cashback ou pagamento de fatura) somam ` +
        `${(total / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })} e NAO foram ` +
        'descontados do gasto — nao da para distinguir com seguranca um estorno de um pagamento de fatura.',
      );
    }
  }

  saidas.sort((a, b) => a.data.localeCompare(b.data));

  return {
    saidas,
    entradas,
    totalSaidas: soma(saidas.map((t) => -t.valor)),
    totalEntradas: soma(entradas.map((t) => t.valor)),
    notas,
  };
}

function cartaoDaInstituicao(
  cartoes: Array<{ id: string; instituicaoId: string }>,
  cartaoId: string,
  instituicaoId: string,
): boolean {
  return cartoes.some((c) => c.id === cartaoId && c.instituicaoId === instituicaoId);
}

export interface Patrimonio {
  emConta: Centavos;
  investido: Centavos;
  faturasEmAberto: Centavos;
  dividas: Centavos;
  liquido: Centavos;
}

/** Patrimonio liquido: o que ha, menos o que se deve — inclusive a fatura ainda nao paga. */
export async function levantarPatrimonio(provider: BankProvider): Promise<Patrimonio> {
  const [contas, investimentos, emprestimos, faturas] = await Promise.all([
    provider.listarContas(),
    provider.listarInvestimentos(),
    provider.listarEmprestimos(),
    provider.listarFaturas(),
  ]);

  const emConta = soma(contas.map((c) => c.saldo));
  const investido = soma(investimentos.map((i) => i.valorAtual));
  const faturasEmAberto = soma(
    faturas.filter((f) => f.status === 'aberta' || f.status === 'fechada' || f.status === 'atrasada')
      .map((f) => f.valorTotal),
  );
  const dividas = soma(emprestimos.map((e) => e.saldoDevedor));

  return {
    emConta,
    investido,
    faturasEmAberto,
    dividas,
    liquido: emConta + investido - faturasEmAberto - dividas,
  };
}
