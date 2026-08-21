import { soma } from '../util/dinheiro.js';
import { mesDe, mesesEntre } from '../util/datas.js';
import type { Agendamento, Centavos, Conta, Transacao } from '../providers/types.js';
import { detectarRecorrentes } from './gastos.js';

export interface MesFluxo {
  mes: string;
  entradas: Centavos;
  saidas: Centavos;
  resultado: Centavos;
}

export function fluxoMensal(transacoes: Transacao[], de: string, ate: string): MesFluxo[] {
  const meses = mesesEntre(de, ate);
  const porMes = new Map<string, Transacao[]>(meses.map((m) => [m, []]));
  for (const t of transacoes) {
    porMes.get(mesDe(t.data))?.push(t);
  }
  return meses.map((mes) => {
    const itens = porMes.get(mes) ?? [];
    const entradas = soma(itens.filter((t) => t.valor > 0).map((t) => t.valor));
    const saidas = soma(itens.filter((t) => t.valor < 0).map((t) => -t.valor));
    return { mes, entradas, saidas, resultado: entradas - saidas };
  });
}

export interface Projecao {
  saldoAtual: Centavos;
  compromissosConhecidos: Centavos;
  gastoMedioMensal: Centavos;
  entradaMediaMensal: Centavos;
  saldoProjetado: Centavos;
  /** Meses de folga com o saldo atual, se a renda parasse hoje. */
  mesesDeFolga: number | null;
  compromissos: Array<{ descricao: string; valor: Centavos; data: string }>;
}

/**
 * Projeta o saldo para os proximos `dias` a partir do que ja se sabe:
 * agendamentos informados pelo banco mais recorrencias detectadas no extrato.
 * Nao e previsao: e o que ja esta contratado, somado ao ritmo dos ultimos meses.
 */
export function projetarFluxo(
  contas: Conta[],
  transacoes: Transacao[],
  agendamentos: Agendamento[],
  hoje: string,
  dias = 30,
): Projecao {
  const saldoAtual = soma(contas.map((c) => c.saldo));
  const fluxos = fluxoMensal(transacoes, transacoes[0]?.data ?? hoje, hoje);
  const fechados = fluxos.slice(0, -1).slice(-6);
  const media = (ns: number[]) => (ns.length === 0 ? 0 : Math.round(soma(ns) / ns.length));
  const gastoMedioMensal = media(fechados.map((f) => f.saidas));
  const entradaMediaMensal = media(fechados.map((f) => f.entradas));

  const limite = new Date(Date.parse(`${hoje}T00:00:00Z`) + dias * 86_400_000)
    .toISOString().slice(0, 10);

  const compromissos = agendamentos
    .filter((a) => a.data >= hoje && a.data <= limite && a.valor !== 0)
    .map((a) => ({ descricao: a.descricao, valor: a.valor, data: a.data }));

  const compromissosConhecidos = soma(compromissos.map((c) => c.valor));

  const proporcao = dias / 30;
  const saldoProjetado = Math.round(
    saldoAtual + compromissosConhecidos + (entradaMediaMensal - gastoMedioMensal) * proporcao,
  );

  const consumoLiquido = gastoMedioMensal;
  return {
    saldoAtual,
    compromissosConhecidos,
    gastoMedioMensal,
    entradaMediaMensal,
    saldoProjetado,
    mesesDeFolga: consumoLiquido > 0 ? Number((saldoAtual / consumoLiquido).toFixed(1)) : null,
    compromissos: compromissos.sort((a, b) => a.data.localeCompare(b.data)),
  };
}

/** Compromissos mensais fixos detectados no extrato, para dimensionar o custo de vida. */
export function custoFixoMensal(transacoes: Transacao[]): Centavos {
  return soma(detectarRecorrentes(transacoes).map((r) => r.valorTipico));
}
