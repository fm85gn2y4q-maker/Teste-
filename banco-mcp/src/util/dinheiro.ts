import type { Centavos } from '../providers/types.js';

/** Converte reais (numero ou string "1.234,56") para centavos inteiros. */
export function paraCentavos(valor: number | string): Centavos {
  if (typeof valor === 'number') return Math.round(valor * 100);
  const limpo = valor.trim().replace(/[R$\s]/g, '').replace(/\./g, '').replace(',', '.');
  const n = Number(limpo);
  if (!Number.isFinite(n)) throw new Error(`Valor monetario invalido: ${valor}`);
  return Math.round(n * 100);
}

/** Formata centavos como "R$ 1.234,56". Negativo vira "-R$ 1.234,56". */
export function brl(centavos: Centavos): string {
  const negativo = centavos < 0;
  const abs = Math.abs(centavos);
  const inteiro = Math.floor(abs / 100);
  const resto = String(abs % 100).padStart(2, '0');
  const milhar = inteiro.toLocaleString('pt-BR');
  return `${negativo ? '-' : ''}R$ ${milhar},${resto}`;
}

/** Formata percentual com uma casa: 12.3% */
export function pct(valor: number, casas = 1): string {
  const s = valor.toFixed(casas).replace('.', ',');
  return `${valor > 0 ? '+' : ''}${s}%`;
}

/** Variacao percentual de `de` para `para`, tolerante a base zero. */
export function variacao(de: Centavos, para: Centavos): number | null {
  if (de === 0) return null;
  return ((para - de) / Math.abs(de)) * 100;
}

export const soma = (valores: Centavos[]): Centavos => valores.reduce((a, b) => a + b, 0);
