import type {
  Cartao, Conta, Emprestimo, Instituicao, Investimento, MetodoTransacao,
  TipoInvestimento, Transacao,
} from '../types.js';

/** Reais (float) -> centavos, tolerante a null. */
export function centavos(v: unknown): number {
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? Math.round(n * 100) : 0;
}

export function dia(v: unknown): string {
  if (typeof v !== 'string' || v.length < 10) return '';
  return v.slice(0, 10);
}

export interface ItemPluggy {
  id: string;
  status?: string;
  createdAt?: string;
  updatedAt?: string;
  connector?: { id?: number; name?: string; type?: string; institutionUrl?: string };
  consentExpiresAt?: string;
  products?: string[];
}

export interface ContaPluggy {
  id: string;
  itemId: string;
  type?: string;
  subtype?: string;
  number?: string;
  name?: string;
  marketingName?: string;
  balance?: number;
  currencyCode?: string;
  updatedAt?: string;
  bankData?: { transferNumber?: string; overdraftContractedLimit?: number };
  creditData?: {
    brand?: string;
    creditLimit?: number;
    availableCreditLimit?: number;
    balanceCloseDate?: string;
    balanceDueDate?: string;
    minimumPayment?: number;
    level?: string;
  };
}

export interface TransacaoPluggy {
  id: string;
  accountId: string;
  description?: string;
  descriptionRaw?: string;
  amount?: number;
  date?: string;
  category?: string;
  balance?: number;
  type?: 'DEBIT' | 'CREDIT';
  merchant?: { name?: string; businessName?: string };
  paymentData?: { paymentMethod?: string; receiver?: { name?: string }; payer?: { name?: string } };
}

const TIPO_CONTA: Record<string, Conta['tipo']> = {
  CHECKING_ACCOUNT: 'corrente',
  SAVINGS_ACCOUNT: 'poupanca',
  PAYMENT_ACCOUNT: 'pagamento',
};

export function mapearInstituicao(item: ItemPluggy): Instituicao {
  const status =
    item.status === 'UPDATED' || item.status === 'UPDATING' ? 'ativa'
    : item.status === 'LOGIN_ERROR' || item.status === 'OUTDATED' ? 'expirada'
    : item.status === 'WAITING_USER_INPUT' ? 'erro'
    : 'erro';
  return {
    id: item.id,
    nome: item.connector?.name ?? 'Instituicao desconhecida',
    tipo: item.connector?.type === 'INVESTMENT' ? 'corretora' : 'banco',
    conectadaEm: dia(item.createdAt),
    status,
    ...(item.consentExpiresAt ? { consentimentoExpiraEm: dia(item.consentExpiresAt) } : {}),
    ...(item.updatedAt ? { ultimaSincronizacao: item.updatedAt } : {}),
    escopos: item.products ?? [],
  };
}

export function ehCartao(c: ContaPluggy): boolean {
  return c.type === 'CREDIT' || c.subtype === 'CREDIT_CARD';
}

export function mapearConta(c: ContaPluggy, nomeInstituicao: string): Conta {
  return {
    id: c.id,
    instituicaoId: c.itemId,
    instituicao: nomeInstituicao,
    tipo: TIPO_CONTA[c.subtype ?? ''] ?? 'corrente',
    ...(c.marketingName || c.name ? { apelido: c.marketingName ?? c.name! } : {}),
    ...(c.bankData?.transferNumber ? { agencia: c.bankData.transferNumber.split('/')[0]! } : {}),
    numero: mascarar(c.number ?? ''),
    moeda: 'BRL',
    saldo: centavos(c.balance),
    saldoDisponivel: centavos(c.balance) + centavos(c.bankData?.overdraftContractedLimit),
    ...(c.bankData?.overdraftContractedLimit
      ? { limiteChequeEspecial: centavos(c.bankData.overdraftContractedLimit) }
      : {}),
    atualizadoEm: c.updatedAt ?? '',
  };
}

export function mapearCartao(c: ContaPluggy, nomeInstituicao: string): Cartao {
  const credito = c.creditData ?? {};
  return {
    id: c.id,
    instituicaoId: c.itemId,
    instituicao: nomeInstituicao,
    apelido: c.marketingName ?? c.name ?? 'Cartao de credito',
    bandeira: credito.brand ?? '-',
    finalNumero: (c.number ?? '').slice(-4),
    limiteTotal: centavos(credito.creditLimit),
    limiteDisponivel: centavos(credito.availableCreditLimit),
    diaFechamento: Number(dia(credito.balanceCloseDate).slice(8, 10)) || 1,
    diaVencimento: Number(dia(credito.balanceDueDate).slice(8, 10)) || 10,
    titularidade: 'titular',
  };
}

const METODO: Record<string, MetodoTransacao> = {
  PIX: 'pix',
  TED: 'ted',
  DOC: 'ted',
  BOLETO: 'boleto',
  SLIP: 'boleto',
  DEBIT_CARD: 'cartao_debito',
  CREDIT_CARD: 'cartao_credito',
  TRANSFER: 'ted',
};

export function mapearTransacao(t: TransacaoPluggy, nomeInstituicao: string, deCartao: boolean): Transacao {
  const valor = centavos(t.amount);
  // A Pluggy ja devolve o sinal, mas nem todo conector e consistente: quando
  // vier `type`, ele manda.
  const sinalizado = t.type === 'DEBIT' ? -Math.abs(valor) : t.type === 'CREDIT' ? Math.abs(valor) : valor;
  const contraparte =
    t.merchant?.name ?? t.merchant?.businessName ??
    t.paymentData?.receiver?.name ?? t.paymentData?.payer?.name;

  return {
    id: t.id,
    contaId: t.accountId,
    instituicao: nomeInstituicao,
    data: dia(t.date),
    descricao: t.description ?? t.descriptionRaw ?? 'Lancamento sem descricao',
    ...(contraparte ? { contraparte } : {}),
    valor: sinalizado,
    metodo: deCartao ? 'cartao_credito' : (METODO[t.paymentData?.paymentMethod ?? ''] ?? 'transferencia_interna'),
    categoria: t.category ?? 'Sem categoria',
    ...(t.balance !== undefined ? { saldoApos: centavos(t.balance) } : {}),
    ...(deCartao ? { faturaDe: t.accountId } : {}),
  };
}

const TIPO_INVESTIMENTO: Record<string, TipoInvestimento> = {
  MUTUAL_FUND: 'fundo',
  EQUITY: 'acao',
  ETF: 'fundo',
  FIXED_INCOME: 'cdb',
  SECURITY: 'tesouro_direto',
  PENSION: 'previdencia',
};

export interface InvestimentoPluggy {
  id: string;
  itemId: string;
  name?: string;
  type?: string;
  subtype?: string;
  balance?: number;
  amount?: number;
  value?: number;
  quantity?: number;
  dueDate?: string;
  date?: string;
  annualRate?: number;
  issuer?: string;
}

export function mapearInvestimento(i: InvestimentoPluggy, nomeInstituicao: string): Investimento {
  const atual = centavos(i.balance ?? i.value);
  return {
    id: i.id,
    instituicaoId: i.itemId,
    instituicao: nomeInstituicao,
    nome: i.name ?? i.issuer ?? 'Investimento',
    tipo: TIPO_INVESTIMENTO[i.type ?? ''] ?? 'fundo',
    ...(i.quantity ? { quantidade: i.quantity } : {}),
    valorAplicado: centavos(i.amount) || atual,
    valorAtual: atual,
    ...(i.annualRate ? { indexador: `${i.annualRate}% a.a.` } : {}),
    ...(i.dueDate ? { vencimento: dia(i.dueDate) } : {}),
    liquidez: i.dueDate ? 'no_vencimento' : 'd_mais_1',
    atualizadoEm: dia(i.date),
  };
}

export interface EmprestimoPluggy {
  id: string;
  itemId: string;
  contractNumber?: string;
  productName?: string;
  contractAmount?: number;
  outstandingBalance?: number;
  installmentValue?: number;
  totalNumberOfInstallments?: number;
  paidInstallments?: number;
  dueDate?: string;
  interestRates?: Array<{ rate?: number; taxPeriodicity?: string }>;
  cet?: number;
}

export function mapearEmprestimo(e: EmprestimoPluggy, nomeInstituicao: string): Emprestimo {
  const taxa = e.interestRates?.[0];
  const mensal = taxa?.taxPeriodicity === 'ANNUAL' && taxa.rate
    ? (Math.pow(1 + taxa.rate / 100, 1 / 12) - 1) * 100
    : (taxa?.rate ?? 0);
  return {
    id: e.id,
    instituicaoId: e.itemId,
    instituicao: nomeInstituicao,
    tipo: 'pessoal',
    descricao: e.productName ?? e.contractNumber ?? 'Contrato de credito',
    valorContratado: centavos(e.contractAmount),
    saldoDevedor: centavos(e.outstandingBalance),
    taxaJurosMensal: Number(mensal.toFixed(2)),
    ...(e.cet ? { cetAnual: e.cet } : {}),
    valorParcela: centavos(e.installmentValue),
    parcelasTotais: e.totalNumberOfInstallments ?? 0,
    parcelasPagas: e.paidInstallments ?? 0,
    ...(e.dueDate ? { proximoVencimento: dia(e.dueDate) } : {}),
  };
}

function mascarar(numero: string): string {
  const limpo = numero.replace(/\s/g, '');
  if (limpo.length <= 4) return limpo;
  return `****${limpo.slice(-4)}`;
}
