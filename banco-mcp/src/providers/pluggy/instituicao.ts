import type { ContaPluggy, ItemPluggy } from './mapear.js';

/**
 * Conector que agrega varios bancos numa conexao so (Meu Pluggy, por exemplo).
 * Nesses casos o nome do conector nao identifica o banco da conta.
 */
const AGREGADOR = /pluggy|open ?finance|agregador/i;

/** Campos em que conectores diferentes escondem o nome da instituicao. */
const CHAVES_INSTITUICAO = [
  'institutionName', 'institution', 'bankName', 'issuer', 'providerName', 'financialInstitution',
];

/** Rotulos manuais por conta: BANCO_MCP_INSTITUICOES={"acc-1":"Nubank"} */
export function rotulosManuais(bruto: string | undefined): Record<string, string> {
  if (!bruto) return {};
  try {
    const obj = JSON.parse(bruto) as Record<string, unknown>;
    return Object.fromEntries(
      Object.entries(obj).filter(([, v]) => typeof v === 'string') as Array<[string, string]>,
    );
  } catch {
    return {};
  }
}

function textoDe(valor: unknown): string | null {
  if (typeof valor === 'string' && valor.trim()) return valor.trim();
  if (valor && typeof valor === 'object') {
    const nome = (valor as { name?: unknown }).name;
    if (typeof nome === 'string' && nome.trim()) return nome.trim();
  }
  return null;
}

/**
 * Descobre de que banco e a conta, em ordem de confianca:
 *   1. rotulo definido a mao pelo usuario;
 *   2. campo de instituicao que o proprio conector mandou;
 *   3. nome do conector — correto quando a conexao e de um banco so.
 *
 * Nao inventa: quando so sobra o nome de um conector agregador, devolve ele
 * mesmo e sinaliza `agregado`, para o diagnostico avisar em vez de fingir que
 * identificou o banco.
 */
export function resolverInstituicao(
  item: ItemPluggy,
  conta: ContaPluggy,
  rotulos: Record<string, string> = {},
): { nome: string; agregado: boolean } {
  const manual = rotulos[conta.id];
  if (manual) return { nome: manual, agregado: false };

  const registro = conta as unknown as Record<string, unknown>;
  for (const chave of CHAVES_INSTITUICAO) {
    const achado = textoDe(registro[chave]);
    if (achado) return { nome: achado, agregado: false };
  }

  const conector = item.connector?.name?.trim();
  if (conector) return { nome: conector, agregado: AGREGADOR.test(conector) };

  return { nome: item.id, agregado: true };
}
