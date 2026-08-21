/** Estabelecimentos e a categoria em que caem, do jeito que aparecem no extrato. */
export interface Estabelecimento {
  nome: string;
  categoria: string;
  min: number;
  max: number;
  /** Peso relativo na hora de sortear. */
  peso: number;
}

export const MERCADO: Estabelecimento[] = [
  { nome: 'PAO DE ACUCAR', categoria: 'Mercado', min: 8_000, max: 46_000, peso: 5 },
  { nome: 'ASSAI ATACADISTA', categoria: 'Mercado', min: 18_000, max: 92_000, peso: 3 },
  { nome: 'SUPERMERCADO PRINCESA', categoria: 'Mercado', min: 4_500, max: 28_000, peso: 4 },
  { nome: 'HORTIFRUTI', categoria: 'Mercado', min: 3_200, max: 14_000, peso: 3 },
];

export const ALIMENTACAO: Estabelecimento[] = [
  { nome: 'IFOOD *IFD', categoria: 'Alimentacao', min: 3_400, max: 14_500, peso: 6 },
  { nome: 'PADARIA REAL', categoria: 'Alimentacao', min: 1_200, max: 6_800, peso: 5 },
  { nome: 'RESTAURANTE MADERO', categoria: 'Alimentacao', min: 8_900, max: 24_000, peso: 2 },
  { nome: 'SUBWAY', categoria: 'Alimentacao', min: 2_800, max: 5_600, peso: 2 },
  { nome: 'STARBUCKS', categoria: 'Alimentacao', min: 1_900, max: 4_800, peso: 2 },
  { nome: 'RA CATERING LTDA', categoria: 'Alimentacao', min: 3_100, max: 7_400, peso: 3 },
];

export const TRANSPORTE: Estabelecimento[] = [
  { nome: 'UBER *TRIP', categoria: 'Transporte', min: 1_400, max: 8_900, peso: 6 },
  { nome: '99APP *99', categoria: 'Transporte', min: 1_100, max: 6_200, peso: 3 },
  { nome: 'POSTO SHELL SELECT', categoria: 'Transporte', min: 12_000, max: 32_000, peso: 3 },
  { nome: 'ESTAPAR ESTACIONAMENTO', categoria: 'Transporte', min: 1_500, max: 5_000, peso: 2 },
  { nome: 'CONCESSIONARIA CCR', categoria: 'Transporte', min: 900, max: 3_800, peso: 2 },
];

export const SAUDE: Estabelecimento[] = [
  { nome: 'DROGARIA PACHECO', categoria: 'Saude', min: 2_300, max: 18_000, peso: 4 },
  { nome: 'DROGASIL', categoria: 'Saude', min: 1_900, max: 15_000, peso: 3 },
  { nome: 'LAB SERGIO FRANCO', categoria: 'Saude', min: 8_000, max: 42_000, peso: 1 },
  { nome: 'SMART FIT', categoria: 'Saude', min: 9_990, max: 9_990, peso: 2 },
];

export const ASSINATURAS: Estabelecimento[] = [
  { nome: 'NETFLIX.COM', categoria: 'Assinaturas', min: 4_490, max: 4_490, peso: 1 },
  { nome: 'SPOTIFY', categoria: 'Assinaturas', min: 3_490, max: 3_490, peso: 1 },
  { nome: 'APPLE.COM/BILL', categoria: 'Assinaturas', min: 990, max: 4_990, peso: 1 },
  { nome: 'AMAZON PRIME BR', categoria: 'Assinaturas', min: 1_490, max: 1_490, peso: 1 },
  { nome: 'OPENAI *CHATGPT', categoria: 'Assinaturas', min: 11_500, max: 12_800, peso: 1 },
];

export const COMPRAS: Estabelecimento[] = [
  { nome: 'AMAZON BR', categoria: 'Compras', min: 3_500, max: 68_000, peso: 4 },
  { nome: 'MERCADOLIVRE', categoria: 'Compras', min: 2_800, max: 54_000, peso: 4 },
  { nome: 'MAGAZINE LUIZA', categoria: 'Compras', min: 9_900, max: 120_000, peso: 1 },
  { nome: 'RENNER', categoria: 'Vestuario', min: 8_900, max: 46_000, peso: 2 },
  { nome: 'CENTAURO', categoria: 'Vestuario', min: 12_000, max: 58_000, peso: 1 },
  { nome: 'LEROY MERLIN', categoria: 'Casa', min: 4_500, max: 78_000, peso: 1 },
  { nome: 'PETZ', categoria: 'Pets', min: 4_200, max: 26_000, peso: 2 },
];

export const LAZER: Estabelecimento[] = [
  { nome: 'CINEMARK', categoria: 'Lazer', min: 4_400, max: 14_000, peso: 2 },
  { nome: 'INGRESSO.COM', categoria: 'Lazer', min: 6_000, max: 32_000, peso: 1 },
  { nome: 'LATAM AIRLINES', categoria: 'Viagem', min: 48_000, max: 320_000, peso: 1 },
  { nome: 'BOOKING.COM', categoria: 'Viagem', min: 32_000, max: 210_000, peso: 1 },
];

export const CARTAO_TODOS: Estabelecimento[] = [
  ...MERCADO, ...ALIMENTACAO, ...TRANSPORTE, ...SAUDE, ...COMPRAS, ...LAZER,
];

/** Sorteio com peso. */
export function sortearPorPeso(itens: Estabelecimento[], r: number): Estabelecimento {
  const total = itens.reduce((a, i) => a + i.peso, 0);
  let acc = r * total;
  for (const i of itens) {
    acc -= i.peso;
    if (acc <= 0) return i;
  }
  return itens[itens.length - 1]!;
}
