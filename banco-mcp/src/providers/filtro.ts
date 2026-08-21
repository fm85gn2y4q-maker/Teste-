import type { FiltroTransacoes, Transacao } from './types.js';

/** Remove acento e caixa para busca livre que perdoa "alimentacao" vs "alimentação". */
export function normalizar(s: string): string {
  return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

/** Aplica o filtro em memoria. Usado pelo mock e como rede de seguranca sobre APIs. */
export function aplicarFiltro(transacoes: Transacao[], f: FiltroTransacoes): Transacao[] {
  const texto = f.texto ? normalizar(f.texto) : null;
  const categoria = f.categoria ? normalizar(f.categoria) : null;

  return transacoes.filter((t) => {
    if (t.data < f.de || t.data > f.ate) return false;
    if (f.contaId && t.contaId !== f.contaId) return false;
    if (f.apenas === 'entradas' && t.valor <= 0) return false;
    if (f.apenas === 'saidas' && t.valor >= 0) return false;
    if (categoria && normalizar(t.categoria) !== categoria) return false;
    if (f.valorMinimo !== undefined && Math.abs(t.valor) < f.valorMinimo) return false;
    if (f.valorMaximo !== undefined && Math.abs(t.valor) > f.valorMaximo) return false;
    if (texto) {
      const alvo = normalizar(`${t.descricao} ${t.contraparte ?? ''} ${t.categoria}`);
      if (!alvo.includes(texto)) return false;
    }
    return true;
  });
}
