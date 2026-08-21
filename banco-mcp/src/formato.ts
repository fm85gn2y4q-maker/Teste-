import { brl } from './util/dinheiro.js';
import type { Centavos } from './providers/types.js';

/** Tabela markdown com alinhamento por coluna. */
export function tabela(
  cabecalho: string[],
  linhas: Array<Array<string | number>>,
  alinhamento?: Array<'esq' | 'dir' | 'centro'>,
): string {
  if (linhas.length === 0) return '_Sem linhas._';
  const sep = cabecalho.map((_, i) => {
    switch (alinhamento?.[i]) {
      case 'dir': return '---:';
      case 'centro': return ':---:';
      default: return '---';
    }
  });
  const corpo = linhas.map((l) => `| ${l.join(' | ')} |`).join('\n');
  return `| ${cabecalho.join(' | ')} |\n| ${sep.join(' | ')} |\n${corpo}`;
}

/** Barrinha de proporcao para leitura rapida de "quanto isso pesa". */
export function barra(percentual: number, largura = 12): string {
  const cheios = Math.max(0, Math.min(largura, Math.round((percentual / 100) * largura)));
  return '#'.repeat(cheios) + '.'.repeat(largura - cheios);
}

/** Sinal legivel para resultado: sobra ou falta. */
export function resultado(valor: Centavos): string {
  if (valor > 0) return `sobrou ${brl(valor)}`;
  if (valor < 0) return `faltou ${brl(-valor)}`;
  return 'ficou zerado';
}

/**
 * Rodape de procedencia. Vai em toda resposta: numero sem origem e numero que
 * ninguem consegue conferir depois.
 */
export function procedencia(origem: string, atualizadoEm?: string): string {
  const quando = atualizadoEm ? ` Dados de ${atualizadoEm}.` : '';
  return `\n---\nFonte: ${origem}.${quando} Consulta somente leitura.`;
}

export function titulo(texto: string, nivel = 2): string {
  return `${'#'.repeat(nivel)} ${texto}`;
}

/** "consentimento expirado", nao "consentimento expirada". */
export function statusConsentimento(status: string): string {
  switch (status) {
    case 'ativa': return 'ativo';
    case 'expirada': return 'expirado';
    case 'revogada': return 'revogado';
    default: return 'com erro';
  }
}

export function lista(itens: string[]): string {
  return itens.map((i) => `- ${i}`).join('\n');
}
