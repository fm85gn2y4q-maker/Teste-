/**
 * Modelo de dominio do Banco MCP.
 *
 * Tudo em centavos (inteiro) para nao arrastar erro de ponto flutuante por
 * dentro de somatorio de extrato. `valor` negativo e saida, positivo e entrada.
 *
 * A interface `BankProvider` nao tem UM metodo de escrita. Isso e proposital:
 * o servidor e read-only por construcao, nao por politica. Um adaptador novo
 * so consegue ler.
 */

export type Centavos = number;

export type StatusConexao = 'ativa' | 'expirada' | 'revogada' | 'erro';

export interface Instituicao {
  id: string;
  nome: string;
  tipo: 'banco' | 'corretora' | 'fintech' | 'cooperativa';
  /** Codigo COMPE / ISPB quando conhecido. */
  codigo?: string;
  conectadaEm: string;
  status: StatusConexao;
  /** Consentimento de Open Finance expira em ate 12 meses (Res. BCB 32/2020). */
  consentimentoExpiraEm?: string;
  ultimaSincronizacao?: string;
  /** Escopos consentidos, ex.: ['contas', 'cartoes', 'investimentos']. */
  escopos: string[];
}

export type TipoConta = 'corrente' | 'poupanca' | 'pagamento' | 'investimento';

export interface Conta {
  id: string;
  instituicaoId: string;
  instituicao: string;
  tipo: TipoConta;
  apelido?: string;
  agencia?: string;
  /** Mascarado na origem: nunca guardamos numero completo. */
  numero: string;
  moeda: 'BRL';
  saldo: Centavos;
  saldoDisponivel: Centavos;
  limiteChequeEspecial?: Centavos;
  atualizadoEm: string;
}

export type MetodoTransacao =
  | 'pix'
  | 'ted'
  | 'boleto'
  | 'cartao_credito'
  | 'cartao_debito'
  | 'debito_automatico'
  | 'saque'
  | 'tarifa'
  | 'rendimento'
  | 'salario'
  | 'transferencia_interna';

export interface Transacao {
  id: string;
  contaId: string;
  instituicao: string;
  /** YYYY-MM-DD */
  data: string;
  descricao: string;
  contraparte?: string;
  valor: Centavos;
  metodo: MetodoTransacao;
  categoria: string;
  /** Presente quando a origem informa saldo apos o lancamento. */
  saldoApos?: Centavos;
  /** Lancamento de fatura de cartao, nao movimenta conta. */
  faturaDe?: string;
}

export interface FiltroTransacoes {
  /** YYYY-MM-DD inclusivo */
  de: string;
  /** YYYY-MM-DD inclusivo */
  ate: string;
  contaId?: string;
  instituicaoId?: string;
  categoria?: string;
  /** Busca livre em descricao e contraparte, sem acento e sem caixa. */
  texto?: string;
  valorMinimo?: Centavos;
  valorMaximo?: Centavos;
  apenas?: 'entradas' | 'saidas';
}

export interface Cartao {
  id: string;
  instituicaoId: string;
  instituicao: string;
  apelido: string;
  bandeira: string;
  finalNumero: string;
  limiteTotal: Centavos;
  limiteDisponivel: Centavos;
  diaFechamento: number;
  diaVencimento: number;
  titularidade: 'titular' | 'adicional';
}

export type StatusFatura = 'aberta' | 'fechada' | 'paga' | 'atrasada';

export interface Fatura {
  id: string;
  cartaoId: string;
  cartao: string;
  instituicao: string;
  /** YYYY-MM */
  mesReferencia: string;
  status: StatusFatura;
  valorTotal: Centavos;
  valorMinimo: Centavos;
  valorPago?: Centavos;
  dataFechamento: string;
  dataVencimento: string;
  lancamentos: Transacao[];
}

export type TipoInvestimento =
  | 'tesouro_direto'
  | 'cdb'
  | 'lci_lca'
  | 'fundo'
  | 'acao'
  | 'fii'
  | 'previdencia'
  | 'cripto'
  | 'poupanca';

export interface Investimento {
  id: string;
  instituicaoId: string;
  instituicao: string;
  nome: string;
  tipo: TipoInvestimento;
  quantidade?: number;
  valorAplicado: Centavos;
  valorAtual: Centavos;
  indexador?: string;
  vencimento?: string;
  liquidez: 'diaria' | 'no_vencimento' | 'd_mais_1' | 'd_mais_30' | 'carencia';
  atualizadoEm: string;
}

export type TipoEmprestimo =
  | 'consignado'
  | 'pessoal'
  | 'financiamento_veicular'
  | 'financiamento_imobiliario'
  | 'cheque_especial'
  | 'rotativo_cartao';

export interface Emprestimo {
  id: string;
  instituicaoId: string;
  instituicao: string;
  tipo: TipoEmprestimo;
  descricao: string;
  valorContratado: Centavos;
  saldoDevedor: Centavos;
  /** Percentual ao mes, ex.: 1.79 */
  taxaJurosMensal: number;
  /** Custo Efetivo Total anual em percentual. */
  cetAnual?: number;
  valorParcela: Centavos;
  parcelasTotais: number;
  parcelasPagas: number;
  proximoVencimento?: string;
}

export interface Agendamento {
  id: string;
  instituicaoId: string;
  instituicao: string;
  contaId?: string;
  descricao: string;
  valor: Centavos;
  /** YYYY-MM-DD da proxima ocorrencia. */
  data: string;
  categoria: string;
  recorrente: boolean;
  frequencia?: 'mensal' | 'semanal' | 'anual';
  /** Detectado por padrao de repeticao em vez de informado pelo banco. */
  inferido?: boolean;
}

/**
 * Contrato que todo adaptador de banco implementa. Somente leitura.
 */
export interface BankProvider {
  readonly nome: string;
  /** Descricao curta da origem dos dados, repassada ao usuario nas respostas. */
  readonly origem: string;
  listarInstituicoes(): Promise<Instituicao[]>;
  listarContas(): Promise<Conta[]>;
  listarTransacoes(filtro: FiltroTransacoes): Promise<Transacao[]>;
  listarCartoes(): Promise<Cartao[]>;
  listarFaturas(cartaoId?: string, mesReferencia?: string): Promise<Fatura[]>;
  listarInvestimentos(): Promise<Investimento[]>;
  listarEmprestimos(): Promise<Emprestimo[]>;
  listarAgendamentos(): Promise<Agendamento[]>;
}
