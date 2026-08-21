import { ClientePluggy } from './cliente.js';
import {
  ehCartao, mapearCartao, mapearConta, mapearEmprestimo, mapearInstituicao,
  mapearInvestimento, mapearTransacao,
  type ContaPluggy, type EmprestimoPluggy, type InvestimentoPluggy, type ItemPluggy,
  type TransacaoPluggy,
} from './mapear.js';
import { resolverInstituicao, rotulosManuais } from './instituicao.js';
import { aplicarFiltro } from '../filtro.js';
import { mesDe, mesesEntre, primeiroDia, somarDias, ultimoDia } from '../../util/datas.js';
import type {
  Agendamento, BankProvider, Cartao, Conta, Emprestimo, Fatura, FiltroTransacoes,
  Instituicao, Investimento, Transacao,
} from '../types.js';

interface Cache<T> {
  valor: T;
  expira: number;
}

const TTL_MS = 5 * 60 * 1000;

/**
 * Adaptador da Pluggy — agregador autorizado no Open Finance brasileiro.
 *
 * Cada `itemId` da Pluggy corresponde a uma conexao com um banco, criada pelo
 * usuario no Pluggy Connect. Este servidor apenas le esses itens: nao cria,
 * nao atualiza e nao remove conexao.
 *
 * O mapeamento de campos segue a documentacao publica da Pluggy, mas conector
 * de banco varia. Confira os primeiros resultados contra o extrato oficial
 * antes de confiar em numero agregado.
 */
export class PluggyProvider implements BankProvider {
  readonly nome = 'pluggy';
  readonly origem = 'Open Finance via Pluggy (agregador autorizado)';

  private itens: Cache<ItemPluggy[]> | null = null;
  private contasBrutas: Cache<Array<{ conta: ContaPluggy; instituicao: string; agregado: boolean }>> | null = null;
  private readonly rotulos: Record<string, string>;

  constructor(
    private readonly cliente: ClientePluggy,
    private readonly itemIds: string[],
    rotulos: Record<string, string> | string = process.env.BANCO_MCP_INSTITUICOES ?? '',
  ) {
    this.rotulos = typeof rotulos === 'string' ? rotulosManuais(rotulos) : rotulos;
    if (itemIds.length === 0) {
      throw new Error(
        'Nenhum item da Pluggy configurado. Defina PLUGGY_ITEM_IDS com os ids das conexoes ' +
        '(cada banco conectado no Pluggy Connect gera um item).',
      );
    }
  }

  private async carregarItens(): Promise<ItemPluggy[]> {
    if (this.itens && Date.now() < this.itens.expira) return this.itens.valor;
    const valor = await Promise.all(this.itemIds.map((id) => this.cliente.get<ItemPluggy>(`/items/${id}`)));
    this.itens = { valor, expira: Date.now() + TTL_MS };
    return valor;
  }

  async carregarContas(): Promise<Array<{ conta: ContaPluggy; instituicao: string; agregado: boolean }>> {
    if (this.contasBrutas && Date.now() < this.contasBrutas.expira) return this.contasBrutas.valor;
    const itens = await this.carregarItens();
    const listas = await Promise.all(
      itens.map(async (item) => {
        const contas = await this.cliente.paginar<ContaPluggy>('/accounts', { itemId: item.id });
        return contas.map((conta) => {
          const { nome, agregado } = resolverInstituicao(item, conta, this.rotulos);
          return { conta, instituicao: nome, agregado };
        });
      }),
    );
    const valor = listas.flat();
    this.contasBrutas = { valor, expira: Date.now() + TTL_MS };
    return valor;
  }

  async listarInstituicoes(): Promise<Instituicao[]> {
    return (await this.carregarItens()).map(mapearInstituicao);
  }

  async listarContas(): Promise<Conta[]> {
    return (await this.carregarContas())
      .filter(({ conta }) => !ehCartao(conta))
      .map(({ conta, instituicao }) => mapearConta(conta, instituicao));
  }

  async listarCartoes(): Promise<Cartao[]> {
    return (await this.carregarContas())
      .filter(({ conta }) => ehCartao(conta))
      .map(({ conta, instituicao }) => mapearCartao(conta, instituicao));
  }

  async listarTransacoes(filtro: FiltroTransacoes): Promise<Transacao[]> {
    const contas = (await this.carregarContas()).filter(({ conta }) => !ehCartao(conta));
    const alvo = contas.filter(
      ({ conta }) =>
        (!filtro.contaId || conta.id === filtro.contaId) &&
        (!filtro.instituicaoId || conta.itemId === filtro.instituicaoId),
    );

    const listas = await Promise.all(
      alvo.map(async ({ conta, instituicao }) => {
        const brutas = await this.cliente.paginar<TransacaoPluggy>('/transactions', {
          accountId: conta.id, from: filtro.de, to: filtro.ate,
        });
        return brutas.map((t) => mapearTransacao(t, instituicao, false));
      }),
    );

    const todas = listas.flat().sort((a, b) => a.data.localeCompare(b.data));
    // A API ja filtra por data; o filtro local cobre categoria, texto e valor.
    return aplicarFiltro(todas, filtro);
  }

  /**
   * A Pluggy expressa a fatura em `/bills`, mas os lancamentos vem como
   * transacoes da conta de cartao. Aqui juntamos os dois: a fatura da o valor e
   * as datas oficiais, as transacoes do ciclo dao a composicao.
   */
  async listarFaturas(cartaoId?: string, mesReferencia?: string): Promise<Fatura[]> {
    const cartoes = (await this.carregarContas()).filter(({ conta }) => ehCartao(conta));
    const alvo = cartoes.filter(({ conta }) => !cartaoId || conta.id === cartaoId);
    const hoje = new Date().toISOString().slice(0, 10);
    const meses = mesReferencia ? [mesReferencia] : mesesEntre(somarDias(hoje, -365), hoje);

    const faturas: Fatura[] = [];
    for (const { conta, instituicao } of alvo) {
      const cartao = mapearCartao(conta, instituicao);
      const [contas, lancamentos] = await Promise.all([
        this.cliente.paginar<BillPluggy>('/bills', { accountId: conta.id }),
        this.cliente.paginar<TransacaoPluggy>('/transactions', {
          accountId: conta.id,
          from: primeiroDia(meses[0]!),
          to: ultimoDia(meses[meses.length - 1]!),
        }),
      ]);

      const mapeados = lancamentos.map((t) => mapearTransacao(t, instituicao, true));

      for (const bill of contas) {
        const vencimento = (bill.dueDate ?? '').slice(0, 10);
        if (!vencimento) continue;
        const referencia = mesDe(vencimento);
        if (mesReferencia && referencia !== mesReferencia) continue;

        const fechamento = somarDias(vencimento, -(cartao.diaVencimento - cartao.diaFechamento || 8));
        const fechamentoAnterior = somarDias(fechamento, -30);
        const doCiclo = mapeados.filter((t) => t.data > fechamentoAnterior && t.data <= fechamento);
        const total = Math.round((bill.totalAmount ?? 0) * 100);

        faturas.push({
          id: bill.id,
          cartaoId: conta.id,
          cartao: cartao.apelido,
          instituicao,
          mesReferencia: referencia,
          status: vencimento < hoje ? 'paga' : fechamento <= hoje ? 'fechada' : 'aberta',
          valorTotal: total,
          valorMinimo: Math.round((bill.minimumPaymentAmount ?? 0) * 100),
          dataFechamento: fechamento,
          dataVencimento: vencimento,
          lancamentos: doCiclo,
        });
      }
    }

    faturas.sort((a, b) => b.mesReferencia.localeCompare(a.mesReferencia));
    return faturas;
  }

  async listarInvestimentos(): Promise<Investimento[]> {
    const itens = await this.carregarItens();
    const listas = await Promise.all(
      itens.map(async (item) => {
        const brutos = await this.cliente.paginar<InvestimentoPluggy>('/investments', { itemId: item.id });
        return brutos.map((i) => mapearInvestimento(i, item.connector?.name ?? item.id));
      }),
    );
    return listas.flat();
  }

  async listarEmprestimos(): Promise<Emprestimo[]> {
    const itens = await this.carregarItens();
    const listas = await Promise.all(
      itens.map(async (item) => {
        const brutos = await this.cliente.paginar<EmprestimoPluggy>('/loans', { itemId: item.id });
        return brutos.map((e) => mapearEmprestimo(e, item.connector?.name ?? item.id));
      }),
    );
    return listas.flat();
  }

  /**
   * O Open Finance brasileiro nao expoe agendamento futuro em consulta de dados
   * (isso vive no lado de iniciacao de pagamento, que este servidor nao toca).
   * Devolvemos vazio em vez de inventar: quem quiser recorrencia usa
   * `listar_agendamentos`, que as detecta no proprio extrato.
   */
  async listarAgendamentos(): Promise<Agendamento[]> {
    return [];
  }
}

interface BillPluggy {
  id: string;
  dueDate?: string;
  totalAmount?: number;
  minimumPaymentAmount?: number;
}
