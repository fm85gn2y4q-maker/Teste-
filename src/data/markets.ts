import { Market, Region } from '../types';

export const REGIONS: Region[] = [
  { id: 'centro', name: 'Centro', costFactor: 1.05 },
  { id: 'zona-norte', name: 'Zona Norte', costFactor: 0.97 },
  { id: 'zona-sul', name: 'Zona Sul', costFactor: 1.1 },
  { id: 'zona-leste', name: 'Zona Leste', costFactor: 0.94 },
  { id: 'zona-oeste', name: 'Zona Oeste', costFactor: 1.0 },
];

export const MARKETS: Market[] = [
  // Centro
  {
    id: 'economax-centro',
    name: 'Economax',
    regionId: 'centro',
    address: 'Av. Central, 1200',
    overallFactor: 0.93,
    categoryFactors: { 'Hortifrúti': 1.08, 'Carnes e Frios': 1.05 },
    promotions: [
      { productId: 'arroz-5kg', discountPct: 12 },
      { productId: 'sabao-po-1kg', discountPct: 15 },
      { productId: 'refri-2l', discountPct: 20 },
    ],
    unavailable: ['pao-frances-kg', 'bolo-pronto'],
  },
  {
    id: 'bompreco-centro',
    name: 'Bom Preço Supermercados',
    regionId: 'centro',
    address: 'Rua XV de Novembro, 88',
    overallFactor: 1.0,
    categoryFactors: { 'Básicos': 0.95, 'Padaria': 0.92 },
    promotions: [
      { productId: 'leite-1l', discountPct: 10 },
      { productId: 'frango-kg', discountPct: 8 },
    ],
    unavailable: [],
  },
  {
    id: 'empori-centro',
    name: 'Empório Central',
    regionId: 'centro',
    address: 'Praça da Matriz, 45',
    overallFactor: 1.12,
    categoryFactors: { 'Hortifrúti': 0.9, 'Padaria': 0.88 },
    promotions: [{ productId: 'cafe-500g', discountPct: 18 }],
    unavailable: ['cerveja-lata', 'amaciante-2l'],
  },
  {
    id: 'atacamais-centro',
    name: 'Ataca+ Atacarejo',
    regionId: 'centro',
    address: 'Av. Industrial, 3000',
    overallFactor: 0.88,
    categoryFactors: { 'Hortifrúti': 1.15, 'Padaria': 1.2, 'Carnes e Frios': 0.95 },
    promotions: [
      { productId: 'papel-hig-12', discountPct: 14 },
      { productId: 'oleo-900ml', discountPct: 10 },
    ],
    unavailable: ['alface-un', 'pao-frances-kg', 'iogurte-170g'],
  },

  // Zona Norte
  {
    id: 'economax-norte',
    name: 'Economax',
    regionId: 'zona-norte',
    address: 'Av. dos Imigrantes, 500',
    overallFactor: 0.94,
    categoryFactors: { 'Hortifrúti': 1.06 },
    promotions: [
      { productId: 'feijao-1kg', discountPct: 15 },
      { productId: 'detergente-500ml', discountPct: 25 },
    ],
    unavailable: ['bolo-pronto'],
  },
  {
    id: 'quitanda-norte',
    name: 'Quitanda & Cia',
    regionId: 'zona-norte',
    address: 'Rua das Palmeiras, 210',
    overallFactor: 1.04,
    categoryFactors: { 'Hortifrúti': 0.82, 'Laticínios': 0.95 },
    promotions: [
      { productId: 'banana-kg', discountPct: 20 },
      { productId: 'tomate-kg', discountPct: 12 },
    ],
    unavailable: [
      'cerveja-lata', 'refri-2l', 'sabao-po-1kg', 'amaciante-2l',
      'papel-hig-12', 'shampoo-350ml', 'desodorante', 'contra-file-kg',
    ],
  },
  {
    id: 'superfamilia-norte',
    name: 'Super Família',
    regionId: 'zona-norte',
    address: 'Av. Norte, 1750',
    overallFactor: 0.99,
    categoryFactors: { 'Carnes e Frios': 0.92, 'Básicos': 0.97 },
    promotions: [
      { productId: 'carne-moida-kg', discountPct: 10 },
      { productId: 'linguica-kg', discountPct: 12 },
    ],
    unavailable: [],
  },

  // Zona Sul
  {
    id: 'gourmetmax-sul',
    name: 'GourmetMax',
    regionId: 'zona-sul',
    address: 'Al. das Acácias, 77',
    overallFactor: 1.18,
    categoryFactors: { 'Hortifrúti': 0.92, 'Carnes e Frios': 0.95, 'Padaria': 0.85 },
    promotions: [
      { productId: 'contra-file-kg', discountPct: 15 },
      { productId: 'suco-1l', discountPct: 10 },
    ],
    unavailable: [],
  },
  {
    id: 'bompreco-sul',
    name: 'Bom Preço Supermercados',
    regionId: 'zona-sul',
    address: 'Av. Beira-Rio, 950',
    overallFactor: 1.02,
    categoryFactors: { 'Básicos': 0.94, 'Limpeza': 0.93 },
    promotions: [
      { productId: 'arroz-5kg', discountPct: 10 },
      { productId: 'papel-hig-12', discountPct: 12 },
    ],
    unavailable: [],
  },
  {
    id: 'atacamais-sul',
    name: 'Ataca+ Atacarejo',
    regionId: 'zona-sul',
    address: 'Rod. Sul, km 12',
    overallFactor: 0.9,
    categoryFactors: { 'Hortifrúti': 1.12, 'Padaria': 1.25 },
    promotions: [
      { productId: 'cerveja-lata', discountPct: 18 },
      { productId: 'sabao-po-1kg', discountPct: 12 },
      { productId: 'frango-kg', discountPct: 9 },
    ],
    unavailable: ['pao-frances-kg', 'alface-un', 'bolo-pronto'],
  },
  {
    id: 'mercadinho-sul',
    name: 'Mercadinho da Esquina',
    regionId: 'zona-sul',
    address: 'Rua dos Ipês, 12',
    overallFactor: 1.09,
    categoryFactors: { 'Padaria': 0.9 },
    promotions: [{ productId: 'pao-frances-kg', discountPct: 10 }],
    unavailable: ['contra-file-kg', 'amaciante-2l', 'desodorante', 'suco-1l'],
  },

  // Zona Leste
  {
    id: 'atacamais-leste',
    name: 'Ataca+ Atacarejo',
    regionId: 'zona-leste',
    address: 'Av. do Trabalhador, 4200',
    overallFactor: 0.87,
    categoryFactors: { 'Hortifrúti': 1.1, 'Padaria': 1.18 },
    promotions: [
      { productId: 'arroz-5kg', discountPct: 15 },
      { productId: 'oleo-900ml', discountPct: 12 },
      { productId: 'papel-hig-12', discountPct: 10 },
    ],
    unavailable: ['alface-un', 'bolo-pronto', 'iogurte-170g'],
  },
  {
    id: 'superfamilia-leste',
    name: 'Super Família',
    regionId: 'zona-leste',
    address: 'Rua da Estação, 333',
    overallFactor: 0.97,
    categoryFactors: { 'Carnes e Frios': 0.9, 'Laticínios': 0.96 },
    promotions: [
      { productId: 'frango-kg', discountPct: 12 },
      { productId: 'leite-1l', discountPct: 8 },
    ],
    unavailable: [],
  },
  {
    id: 'feiralivre-leste',
    name: 'Feira Livre Leste',
    regionId: 'zona-leste',
    address: 'Praça do Mercado, s/n',
    overallFactor: 1.0,
    categoryFactors: { 'Hortifrúti': 0.78 },
    promotions: [
      { productId: 'tomate-kg', discountPct: 15 },
      { productId: 'batata-kg', discountPct: 10 },
    ],
    unavailable: [
      'refri-2l', 'cerveja-lata', 'sabao-po-1kg', 'agua-sanitaria-1l',
      'amaciante-2l', 'esponja-4un', 'papel-hig-12', 'sabonete-90g',
      'creme-dental', 'shampoo-350ml', 'desodorante', 'pao-forma', 'bolo-pronto',
    ],
  },

  // Zona Oeste
  {
    id: 'bompreco-oeste',
    name: 'Bom Preço Supermercados',
    regionId: 'zona-oeste',
    address: 'Av. das Torres, 2100',
    overallFactor: 1.01,
    categoryFactors: { 'Básicos': 0.95, 'Bebidas': 0.94 },
    promotions: [
      { productId: 'refri-2l', discountPct: 15 },
      { productId: 'macarrao-500g', discountPct: 10 },
    ],
    unavailable: [],
  },
  {
    id: 'economax-oeste',
    name: 'Economax',
    regionId: 'zona-oeste',
    address: 'Rua do Comércio, 640',
    overallFactor: 0.95,
    categoryFactors: { 'Hortifrúti': 1.05, 'Higiene': 0.93 },
    promotions: [
      { productId: 'shampoo-350ml', discountPct: 20 },
      { productId: 'creme-dental', discountPct: 15 },
    ],
    unavailable: ['pao-frances-kg'],
  },
  {
    id: 'gourmetmax-oeste',
    name: 'GourmetMax',
    regionId: 'zona-oeste',
    address: 'Shopping Oeste, loja 12',
    overallFactor: 1.15,
    categoryFactors: { 'Padaria': 0.87, 'Carnes e Frios': 0.96 },
    promotions: [{ productId: 'mussarela-200g', discountPct: 12 }],
    unavailable: [],
  },
];

export function marketsInRegion(regionId: string): Market[] {
  return MARKETS.filter((m) => m.regionId === regionId);
}

export function getRegion(regionId: string): Region {
  const r = REGIONS.find((x) => x.id === regionId);
  if (!r) throw new Error(`Região desconhecida: ${regionId}`);
  return r;
}
