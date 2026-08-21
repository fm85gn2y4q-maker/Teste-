import { acervoMock, type Acervo } from './acervo.js';
import { aplicarFiltro } from '../filtro.js';
import type {
  Agendamento, BankProvider, Cartao, Conta, Emprestimo, Fatura, FiltroTransacoes,
  Instituicao, Investimento, Transacao,
} from '../types.js';

/**
 * Provedor de demonstracao. Nao toca em banco nenhum: monta um acervo sintetico
 * coerente (14 meses, 4 instituicoes, 2 cartoes, carteira e dois emprestimos)
 * para o servidor funcionar sem credencial e para os testes terem chao firme.
 */
export class MockProvider implements BankProvider {
  readonly nome = 'mock';
  readonly origem = 'dados sinteticos de demonstracao (nenhum banco real consultado)';

  private readonly acervo: Acervo;

  constructor(opcoes: { hoje?: string; semente?: number } = {}) {
    this.acervo = acervoMock(opcoes);
  }

  async listarInstituicoes(): Promise<Instituicao[]> {
    return this.acervo.instituicoes;
  }

  async listarContas(): Promise<Conta[]> {
    return this.acervo.contas;
  }

  async listarTransacoes(filtro: FiltroTransacoes): Promise<Transacao[]> {
    let base = this.acervo.transacoes;
    if (filtro.instituicaoId) {
      const contas = new Set(
        this.acervo.contas.filter((c) => c.instituicaoId === filtro.instituicaoId).map((c) => c.id),
      );
      base = base.filter((t) => contas.has(t.contaId));
    }
    return aplicarFiltro(base, filtro);
  }

  async listarCartoes(): Promise<Cartao[]> {
    return this.acervo.cartoes;
  }

  async listarFaturas(cartaoId?: string, mesReferencia?: string): Promise<Fatura[]> {
    return this.acervo.faturas.filter(
      (f) => (!cartaoId || f.cartaoId === cartaoId) && (!mesReferencia || f.mesReferencia === mesReferencia),
    );
  }

  async listarInvestimentos(): Promise<Investimento[]> {
    return this.acervo.investimentos;
  }

  async listarEmprestimos(): Promise<Emprestimo[]> {
    return this.acervo.emprestimos;
  }

  async listarAgendamentos(): Promise<Agendamento[]> {
    return this.acervo.agendamentos;
  }
}
