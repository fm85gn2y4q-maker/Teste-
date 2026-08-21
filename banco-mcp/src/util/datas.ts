/**
 * Datas em ISO curto (YYYY-MM-DD), sempre tratadas como data civil de Brasilia.
 * Nada de Date com fuso: o extrato de 31/01 nao pode virar 30/01 porque o
 * processo roda em UTC.
 */

const RE_DIA = /^\d{4}-\d{2}-\d{2}$/;
const RE_MES = /^\d{4}-\d{2}$/;

export function hojeISO(agora: Date = new Date()): string {
  // -03:00 fixo (Brasilia nao tem mais horario de verao desde 2019).
  const brasilia = new Date(agora.getTime() - 3 * 60 * 60 * 1000);
  return brasilia.toISOString().slice(0, 10);
}

export function ehDia(s: string): boolean {
  return RE_DIA.test(s);
}

export function ehMes(s: string): boolean {
  return RE_MES.test(s);
}

export function partes(dia: string): { ano: number; mes: number; dia: number } {
  if (!ehDia(dia)) throw new Error(`Data invalida (use YYYY-MM-DD): ${dia}`);
  return {
    ano: Number(dia.slice(0, 4)),
    mes: Number(dia.slice(5, 7)),
    dia: Number(dia.slice(8, 10)),
  };
}

export function mesDe(dia: string): string {
  return dia.slice(0, 7);
}

export function diasNoMes(ano: number, mes: number): number {
  return new Date(Date.UTC(ano, mes, 0)).getUTCDate();
}

export function montarDia(ano: number, mes: number, dia: number): string {
  const d = Math.min(dia, diasNoMes(ano, mes));
  return `${ano}-${String(mes).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

export function somarDias(dia: string, n: number): string {
  const { ano, mes, dia: d } = partes(dia);
  const base = new Date(Date.UTC(ano, mes - 1, d));
  base.setUTCDate(base.getUTCDate() + n);
  return base.toISOString().slice(0, 10);
}

export function somarMeses(mes: string, n: number): string {
  if (!ehMes(mes)) throw new Error(`Mes invalido (use YYYY-MM): ${mes}`);
  const ano = Number(mes.slice(0, 4));
  const m = Number(mes.slice(5, 7));
  const total = ano * 12 + (m - 1) + n;
  const novoAno = Math.floor(total / 12);
  const novoMes = (total % 12) + 1;
  return `${novoAno}-${String(novoMes).padStart(2, '0')}`;
}

export function primeiroDia(mes: string): string {
  return `${mes}-01`;
}

export function ultimoDia(mes: string): string {
  const ano = Number(mes.slice(0, 4));
  const m = Number(mes.slice(5, 7));
  return `${mes}-${String(diasNoMes(ano, m)).padStart(2, '0')}`;
}

const MESES_PT = [
  'janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
];

export function mesPorExtenso(mes: string): string {
  const idx = Number(mes.slice(5, 7)) - 1;
  return `${MESES_PT[idx] ?? mes}/${mes.slice(0, 4)}`;
}

export function formatarDia(dia: string): string {
  const { ano, mes, dia: d } = partes(dia);
  return `${String(d).padStart(2, '0')}/${String(mes).padStart(2, '0')}/${ano}`;
}

export interface Periodo {
  de: string;
  ate: string;
  rotulo: string;
}

/**
 * Resolve um periodo a partir de entradas soltas. Aceita:
 *   - de/ate explicitos
 *   - mes "YYYY-MM"
 *   - atalhos: "mes_atual", "mes_passado", "ultimos_30_dias", "ultimos_90_dias",
 *     "ano_atual", "ultimos_12_meses"
 * Sem nada, devolve o mes corrente.
 */
export function resolverPeriodo(
  entrada: { de?: string; ate?: string; mes?: string; periodo?: string },
  hoje: string = hojeISO(),
): Periodo {
  const { de, ate, mes, periodo } = entrada;

  if (de || ate) {
    const inicio = de ?? somarDias(ate!, -30);
    const fim = ate ?? hoje;
    if (inicio > fim) throw new Error(`Periodo invertido: ${inicio} vem depois de ${fim}.`);
    return { de: inicio, ate: fim, rotulo: `${formatarDia(inicio)} a ${formatarDia(fim)}` };
  }

  if (mes) {
    if (!ehMes(mes)) throw new Error(`Mes invalido (use YYYY-MM): ${mes}`);
    return { de: primeiroDia(mes), ate: ultimoDia(mes), rotulo: mesPorExtenso(mes) };
  }

  const mesHoje = mesDe(hoje);
  switch (periodo) {
    case undefined:
    case 'mes_atual':
      return { de: primeiroDia(mesHoje), ate: hoje, rotulo: `${mesPorExtenso(mesHoje)} (ate hoje)` };
    case 'mes_passado': {
      const anterior = somarMeses(mesHoje, -1);
      return { de: primeiroDia(anterior), ate: ultimoDia(anterior), rotulo: mesPorExtenso(anterior) };
    }
    case 'ultimos_30_dias':
      return { de: somarDias(hoje, -29), ate: hoje, rotulo: 'ultimos 30 dias' };
    case 'ultimos_90_dias':
      return { de: somarDias(hoje, -89), ate: hoje, rotulo: 'ultimos 90 dias' };
    case 'ano_atual':
      return { de: `${hoje.slice(0, 4)}-01-01`, ate: hoje, rotulo: `ano de ${hoje.slice(0, 4)}` };
    case 'ultimos_12_meses': {
      const inicio = primeiroDia(somarMeses(mesHoje, -11));
      return { de: inicio, ate: hoje, rotulo: 'ultimos 12 meses' };
    }
    default:
      throw new Error(`Periodo desconhecido: ${periodo}`);
  }
}

/** Periodo imediatamente anterior, de mesmo tamanho, para comparacao. */
export function periodoAnterior(p: Periodo): Periodo {
  const dias = diferencaEmDias(p.de, p.ate) + 1;
  const ate = somarDias(p.de, -1);
  const de = somarDias(ate, -(dias - 1));
  return { de, ate, rotulo: `${formatarDia(de)} a ${formatarDia(ate)}` };
}

export function diferencaEmDias(de: string, ate: string): number {
  const a = partes(de);
  const b = partes(ate);
  const ms = Date.UTC(b.ano, b.mes - 1, b.dia) - Date.UTC(a.ano, a.mes - 1, a.dia);
  return Math.round(ms / 86_400_000);
}

/** Lista de meses YYYY-MM cobertos por um periodo, em ordem. */
export function mesesEntre(de: string, ate: string): string[] {
  const out: string[] = [];
  let m = mesDe(de);
  const fim = mesDe(ate);
  while (m <= fim) {
    out.push(m);
    m = somarMeses(m, 1);
  }
  return out;
}
