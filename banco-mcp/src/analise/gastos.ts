import { soma } from '../util/dinheiro.js';
import { normalizar } from '../providers/filtro.js';
import type { Centavos, Transacao } from '../providers/types.js';

export interface Grupo {
  chave: string;
  total: Centavos;
  quantidade: number;
  percentual: number;
  maiorLancamento?: Transacao;
}

function agrupar(transacoes: Transacao[], chaveDe: (t: Transacao) => string): Grupo[] {
  const mapa = new Map<string, Transacao[]>();
  for (const t of transacoes) {
    const k = chaveDe(t);
    const lista = mapa.get(k);
    if (lista) lista.push(t);
    else mapa.set(k, [t]);
  }
  const totalGeral = soma(transacoes.map((t) => Math.abs(t.valor)));
  const grupos: Grupo[] = [];
  for (const [chave, itens] of mapa) {
    const total = soma(itens.map((t) => Math.abs(t.valor)));
    grupos.push({
      chave,
      total,
      quantidade: itens.length,
      percentual: totalGeral === 0 ? 0 : (total / totalGeral) * 100,
      maiorLancamento: itens.reduce((a, b) => (Math.abs(b.valor) > Math.abs(a.valor) ? b : a)),
    });
  }
  grupos.sort((a, b) => b.total - a.total);
  return grupos;
}

export const porCategoria = (t: Transacao[]): Grupo[] => agrupar(t, (x) => x.categoria);

export const porEstabelecimento = (t: Transacao[]): Grupo[] =>
  agrupar(t, (x) => x.contraparte ?? x.descricao);

export const porInstituicao = (t: Transacao[]): Grupo[] => agrupar(t, (x) => x.instituicao);

export const porMetodo = (t: Transacao[]): Grupo[] => agrupar(t, (x) => x.metodo);

export interface Comparacao {
  chave: string;
  atual: Centavos;
  anterior: Centavos;
  delta: Centavos;
  variacaoPct: number | null;
}

/** Compara duas listas de saidas por categoria, incluindo o que sumiu e o que surgiu. */
export function compararCategorias(atual: Transacao[], anterior: Transacao[]): Comparacao[] {
  const a = new Map(porCategoria(atual).map((g) => [g.chave, g.total]));
  const b = new Map(porCategoria(anterior).map((g) => [g.chave, g.total]));
  const chaves = new Set([...a.keys(), ...b.keys()]);
  const out: Comparacao[] = [];
  for (const chave of chaves) {
    const va = a.get(chave) ?? 0;
    const vb = b.get(chave) ?? 0;
    out.push({
      chave,
      atual: va,
      anterior: vb,
      delta: va - vb,
      variacaoPct: vb === 0 ? null : ((va - vb) / vb) * 100,
    });
  }
  out.sort((x, y) => Math.abs(y.delta) - Math.abs(x.delta));
  return out;
}

export interface Recorrencia {
  descricao: string;
  categoria: string;
  valorTipico: Centavos;
  ocorrencias: number;
  ultimaData: string;
  /** Intervalo mediano em dias entre ocorrencias. */
  intervaloDias: number;
}

/**
 * Detecta pagamento recorrente por repeticao: mesmo estabelecimento, tres ou mais
 * vezes, com intervalo proximo de um mes e valor estavel. Serve para achar a
 * assinatura esquecida que ninguem lembra de ter contratado.
 */
export function detectarRecorrentes(transacoes: Transacao[]): Recorrencia[] {
  const saidas = transacoes.filter((t) => t.valor < 0);
  const mapa = new Map<string, Transacao[]>();
  for (const t of saidas) {
    const k = normalizar(t.contraparte ?? t.descricao).replace(/\s*-?\s*parcela.*$/i, '').trim();
    const lista = mapa.get(k);
    if (lista) lista.push(t);
    else mapa.set(k, [t]);
  }

  const out: Recorrencia[] = [];
  for (const itens of mapa.values()) {
    if (itens.length < 3) continue;
    const ordenadas = [...itens].sort((a, b) => a.data.localeCompare(b.data));
    const intervalos: number[] = [];
    for (let i = 1; i < ordenadas.length; i++) {
      const d1 = Date.parse(`${ordenadas[i - 1]!.data}T00:00:00Z`);
      const d2 = Date.parse(`${ordenadas[i]!.data}T00:00:00Z`);
      intervalos.push(Math.round((d2 - d1) / 86_400_000));
    }
    intervalos.sort((a, b) => a - b);
    const mediana = intervalos[Math.floor(intervalos.length / 2)] ?? 0;
    if (mediana < 20 || mediana > 45) continue;

    const valores = ordenadas.map((t) => Math.abs(t.valor)).sort((a, b) => a - b);
    const tipico = valores[Math.floor(valores.length / 2)]!;
    const dispersao = tipico === 0 ? 1 : (valores[valores.length - 1]! - valores[0]!) / tipico;
    if (dispersao > 0.4) continue;

    const ultima = ordenadas[ordenadas.length - 1]!;
    out.push({
      descricao: ultima.contraparte ?? ultima.descricao,
      categoria: ultima.categoria,
      valorTipico: tipico,
      ocorrencias: ordenadas.length,
      ultimaData: ultima.data,
      intervaloDias: mediana,
    });
  }
  out.sort((a, b) => b.valorTipico - a.valorTipico);
  return out;
}
