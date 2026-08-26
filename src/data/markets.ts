import { Market, NearbyMarket } from '../types';
import { distanceKm, getBairro } from './bairros';

/**
 * Mercados inspirados nas redes que operam no Rio de Janeiro, com perfis de
 * preço típicos de cada bandeira. Endereços e preços são simulados.
 */
export const MARKETS: Market[] = [
  // Barra da Tijuca
  {
    id: 'assai-barra',
    name: 'Assaí Atacadista',
    bairroId: 'barra',
    address: 'Av. das Américas, 1500 — Barra',
    overallFactor: 0.85,
    categoryFactors: { 'Hortifrúti': 1.15, 'Padaria': 1.25, 'Carnes e Frios': 0.95 },
    promotions: [
      { productId: 'arroz-5kg', discountPct: 14 },
      { productId: 'oleo-900ml', discountPct: 10 },
      { productId: 'papel-hig-12', discountPct: 12 },
      { productId: 'cerveja-lata', discountPct: 15 },
    ],
    unavailable: ['alface-un', 'pao-frances-kg', 'bolo-pronto', 'iogurte-170g'],
  },
  {
    id: 'paodeacucar-barra',
    name: 'Pão de Açúcar',
    bairroId: 'barra',
    address: 'Av. Olegário Maciel, 130 — Barra',
    overallFactor: 1.15,
    categoryFactors: { 'Padaria': 0.9, 'Hortifrúti': 0.95, 'Laticínios': 0.97 },
    promotions: [
      { productId: 'cafe-500g', discountPct: 20 },
      { productId: 'suco-1l', discountPct: 12 },
    ],
    unavailable: [],
  },
  {
    id: 'zonasul-barra',
    name: 'Zona Sul',
    bairroId: 'barra',
    address: 'Av. das Américas, 4666 (BarraShopping)',
    overallFactor: 1.12,
    categoryFactors: { 'Padaria': 0.85, 'Hortifrúti': 0.92 },
    promotions: [
      { productId: 'pao-frances-kg', discountPct: 10 },
      { productId: 'mussarela-200g', discountPct: 12 },
    ],
    unavailable: [],
  },
  {
    id: 'extra-barra',
    name: 'Extra Hiper',
    bairroId: 'barra',
    address: 'Av. Ayrton Senna, 2150 — Barra',
    overallFactor: 0.99,
    categoryFactors: { 'Básicos': 0.96, 'Limpeza': 0.94, 'Bebidas': 0.95 },
    promotions: [
      { productId: 'sabao-po-1kg', discountPct: 15 },
      { productId: 'refri-2l', discountPct: 18 },
      { productId: 'frango-kg', discountPct: 8 },
    ],
    unavailable: [],
  },

  // Recreio
  {
    id: 'guanabara-recreio',
    name: 'Supermercados Guanabara',
    bairroId: 'recreio',
    address: 'Av. das Américas, 15500 — Recreio',
    overallFactor: 0.89,
    categoryFactors: { 'Básicos': 0.93, 'Bebidas': 0.94 },
    promotions: [
      { productId: 'feijao-1kg', discountPct: 18 },
      { productId: 'acucar-1kg', discountPct: 12 },
      { productId: 'frango-kg', discountPct: 12 },
      { productId: 'detergente-500ml', discountPct: 20 },
    ],
    unavailable: [],
  },
  {
    id: 'mundial-recreio',
    name: 'Supermercados Mundial',
    bairroId: 'recreio',
    address: 'Estrada Benvindo de Novais, 850 — Recreio',
    overallFactor: 0.93,
    categoryFactors: { 'Hortifrúti': 0.88, 'Carnes e Frios': 0.93 },
    promotions: [
      { productId: 'banana-kg', discountPct: 15 },
      { productId: 'carne-moida-kg', discountPct: 10 },
    ],
    unavailable: [],
  },
  {
    id: 'hortifruti-recreio',
    name: 'Hortifruti Natural da Terra',
    bairroId: 'recreio',
    address: 'Av. Alfredo Baltazar da Silveira, 580',
    overallFactor: 1.05,
    categoryFactors: { 'Hortifrúti': 0.75, 'Padaria': 0.95, 'Laticínios': 0.98 },
    promotions: [
      { productId: 'tomate-kg', discountPct: 15 },
      { productId: 'maca-kg', discountPct: 12 },
      { productId: 'alface-un', discountPct: 10 },
    ],
    unavailable: [
      'refri-2l', 'cerveja-lata', 'sabao-po-1kg', 'agua-sanitaria-1l', 'amaciante-2l',
      'esponja-4un', 'papel-hig-12', 'sabonete-90g', 'creme-dental', 'shampoo-350ml',
      'desodorante',
    ],
  },

  // Jacarepaguá (Freguesia)
  {
    id: 'atacadao-jacarepagua',
    name: 'Atacadão',
    bairroId: 'jacarepagua',
    address: 'Estrada dos Bandeirantes, 1400',
    overallFactor: 0.84,
    categoryFactors: { 'Hortifrúti': 1.18, 'Padaria': 1.3, 'Carnes e Frios': 0.96 },
    promotions: [
      { productId: 'arroz-5kg', discountPct: 12 },
      { productId: 'macarrao-500g', discountPct: 15 },
      { productId: 'sabao-po-1kg', discountPct: 10 },
    ],
    unavailable: ['alface-un', 'pao-frances-kg', 'bolo-pronto', 'iogurte-170g', 'requeijao-200g'],
  },
  {
    id: 'guanabara-jacarepagua',
    name: 'Supermercados Guanabara',
    bairroId: 'jacarepagua',
    address: 'Estrada do Gabinal, 313 — Freguesia',
    overallFactor: 0.9,
    categoryFactors: { 'Básicos': 0.93, 'Laticínios': 0.96 },
    promotions: [
      { productId: 'leite-1l', discountPct: 12 },
      { productId: 'oleo-900ml', discountPct: 14 },
      { productId: 'linguica-kg', discountPct: 10 },
    ],
    unavailable: [],
  },
  {
    id: 'prezunic-jacarepagua',
    name: 'Prezunic',
    bairroId: 'jacarepagua',
    address: 'Av. Geremário Dantas, 800 — Freguesia',
    overallFactor: 0.96,
    categoryFactors: { 'Carnes e Frios': 0.92, 'Padaria': 0.95 },
    promotions: [
      { productId: 'contra-file-kg', discountPct: 12 },
      { productId: 'frango-kg', discountPct: 10 },
    ],
    unavailable: [],
  },

  // São Conrado
  {
    id: 'zonasul-saoconrado',
    name: 'Zona Sul',
    bairroId: 'sao-conrado',
    address: 'Estrada da Gávea, 899 (Fashion Mall)',
    overallFactor: 1.14,
    categoryFactors: { 'Padaria': 0.86, 'Hortifrúti': 0.93 },
    promotions: [{ productId: 'iogurte-170g', discountPct: 15 }],
    unavailable: [],
  },

  // Ipanema / Leblon
  {
    id: 'zonasul-leblon',
    name: 'Zona Sul',
    bairroId: 'ipanema-leblon',
    address: 'Rua Dias Ferreira, 290 — Leblon',
    overallFactor: 1.13,
    categoryFactors: { 'Padaria': 0.85, 'Hortifrúti': 0.92, 'Carnes e Frios': 0.97 },
    promotions: [
      { productId: 'pao-frances-kg', discountPct: 12 },
      { productId: 'manteiga-200g', discountPct: 10 },
    ],
    unavailable: [],
  },
  {
    id: 'hortifruti-ipanema',
    name: 'Hortifruti Natural da Terra',
    bairroId: 'ipanema-leblon',
    address: 'Rua Visconde de Pirajá, 359 — Ipanema',
    overallFactor: 1.07,
    categoryFactors: { 'Hortifrúti': 0.76, 'Laticínios': 0.98 },
    promotions: [
      { productId: 'banana-kg', discountPct: 12 },
      { productId: 'limao-kg', discountPct: 15 },
    ],
    unavailable: [
      'refri-2l', 'cerveja-lata', 'sabao-po-1kg', 'agua-sanitaria-1l', 'amaciante-2l',
      'esponja-4un', 'papel-hig-12', 'sabonete-90g', 'creme-dental', 'shampoo-350ml',
      'desodorante',
    ],
  },
  {
    id: 'paodeacucar-ipanema',
    name: 'Pão de Açúcar',
    bairroId: 'ipanema-leblon',
    address: 'Rua Barão da Torre, 342 — Ipanema',
    overallFactor: 1.16,
    categoryFactors: { 'Padaria': 0.9, 'Laticínios': 0.96 },
    promotions: [
      { productId: 'cafe-500g', discountPct: 18 },
      { productId: 'requeijao-200g', discountPct: 12 },
    ],
    unavailable: [],
  },

  // Copacabana
  {
    id: 'mundial-copacabana',
    name: 'Supermercados Mundial',
    bairroId: 'copacabana',
    address: 'Rua Barata Ribeiro, 439',
    overallFactor: 0.94,
    categoryFactors: { 'Hortifrúti': 0.88, 'Carnes e Frios': 0.94, 'Bebidas': 0.95 },
    promotions: [
      { productId: 'tomate-kg', discountPct: 12 },
      { productId: 'cerveja-lata', discountPct: 12 },
      { productId: 'contra-file-kg', discountPct: 10 },
    ],
    unavailable: [],
  },
  {
    id: 'zonasul-copacabana',
    name: 'Zona Sul',
    bairroId: 'copacabana',
    address: 'Av. Nossa Sra. de Copacabana, 1155',
    overallFactor: 1.11,
    categoryFactors: { 'Padaria': 0.86, 'Hortifrúti': 0.93 },
    promotions: [{ productId: 'bolo-pronto', discountPct: 15 }],
    unavailable: [],
  },
  {
    id: 'superprix-copacabana',
    name: 'SuperPrix',
    bairroId: 'copacabana',
    address: 'Rua Pompeu Loureiro, 32',
    overallFactor: 1.02,
    categoryFactors: { 'Laticínios': 0.95, 'Básicos': 0.97 },
    promotions: [
      { productId: 'leite-1l', discountPct: 10 },
      { productId: 'ovos-12', discountPct: 12 },
    ],
    unavailable: ['contra-file-kg'],
  },

  // Botafogo
  {
    id: 'extra-botafogo',
    name: 'Extra Hiper',
    bairroId: 'botafogo',
    address: 'Rua Voluntários da Pátria, 138',
    overallFactor: 0.98,
    categoryFactors: { 'Básicos': 0.95, 'Limpeza': 0.93 },
    promotions: [
      { productId: 'amaciante-2l', discountPct: 15 },
      { productId: 'arroz-5kg', discountPct: 10 },
    ],
    unavailable: [],
  },
  {
    id: 'mundial-botafogo',
    name: 'Supermercados Mundial',
    bairroId: 'botafogo',
    address: 'Rua São Clemente, 168',
    overallFactor: 0.93,
    categoryFactors: { 'Hortifrúti': 0.87, 'Carnes e Frios': 0.93 },
    promotions: [
      { productId: 'batata-kg', discountPct: 12 },
      { productId: 'frango-kg', discountPct: 10 },
      { productId: 'linguica-kg', discountPct: 12 },
    ],
    unavailable: [],
  },
  {
    id: 'superprix-botafogo',
    name: 'SuperPrix',
    bairroId: 'botafogo',
    address: 'Rua da Passagem, 108',
    overallFactor: 1.01,
    categoryFactors: { 'Padaria': 0.94, 'Laticínios': 0.96 },
    promotions: [{ productId: 'pao-forma', discountPct: 12 }],
    unavailable: ['contra-file-kg'],
  },

  // Tijuca
  {
    id: 'guanabara-tijuca',
    name: 'Supermercados Guanabara',
    bairroId: 'tijuca',
    address: 'Rua Conde de Bonfim, 344',
    overallFactor: 0.88,
    categoryFactors: { 'Básicos': 0.92, 'Bebidas': 0.94, 'Limpeza': 0.95 },
    promotions: [
      { productId: 'arroz-5kg', discountPct: 16 },
      { productId: 'feijao-1kg', discountPct: 15 },
      { productId: 'cafe-500g', discountPct: 12 },
      { productId: 'refri-2l', discountPct: 15 },
    ],
    unavailable: [],
  },
  {
    id: 'mundial-tijuca',
    name: 'Supermercados Mundial',
    bairroId: 'tijuca',
    address: 'Rua General Roca, 863',
    overallFactor: 0.93,
    categoryFactors: { 'Hortifrúti': 0.88, 'Carnes e Frios': 0.93 },
    promotions: [
      { productId: 'cebola-kg', discountPct: 12 },
      { productId: 'carne-moida-kg', discountPct: 10 },
    ],
    unavailable: [],
  },
  {
    id: 'prezunic-tijuca',
    name: 'Prezunic',
    bairroId: 'tijuca',
    address: 'Rua Mariz e Barros, 821',
    overallFactor: 0.97,
    categoryFactors: { 'Carnes e Frios': 0.92, 'Laticínios': 0.96 },
    promotions: [
      { productId: 'presunto-200g', discountPct: 12 },
      { productId: 'leite-1l', discountPct: 8 },
    ],
    unavailable: [],
  },

  // Centro
  {
    id: 'guanabara-centro',
    name: 'Supermercados Guanabara',
    bairroId: 'centro',
    address: 'Rua da Alfândega, 156',
    overallFactor: 0.89,
    categoryFactors: { 'Básicos': 0.93, 'Higiene': 0.95 },
    promotions: [
      { productId: 'acucar-1kg', discountPct: 15 },
      { productId: 'sabonete-90g', discountPct: 20 },
    ],
    unavailable: ['pao-frances-kg'],
  },
  {
    id: 'mundial-centro',
    name: 'Supermercados Mundial',
    bairroId: 'centro',
    address: 'Rua Sete de Setembro, 135',
    overallFactor: 0.94,
    categoryFactors: { 'Hortifrúti': 0.9, 'Bebidas': 0.94 },
    promotions: [{ productId: 'agua-1500ml', discountPct: 15 }],
    unavailable: [],
  },
  {
    id: 'assai-centro',
    name: 'Assaí Atacadista',
    bairroId: 'centro',
    address: 'Av. Brasil, 500 (Caju)',
    overallFactor: 0.86,
    categoryFactors: { 'Hortifrúti': 1.12, 'Padaria': 1.25, 'Carnes e Frios': 0.95 },
    promotions: [
      { productId: 'papel-hig-12', discountPct: 14 },
      { productId: 'oleo-900ml', discountPct: 12 },
      { productId: 'cerveja-lata', discountPct: 16 },
    ],
    unavailable: ['alface-un', 'pao-frances-kg', 'bolo-pronto', 'iogurte-170g'],
  },

  // Méier
  {
    id: 'guanabara-meier',
    name: 'Supermercados Guanabara',
    bairroId: 'meier',
    address: 'Rua Dias da Cruz, 255',
    overallFactor: 0.87,
    categoryFactors: { 'Básicos': 0.92, 'Carnes e Frios': 0.95 },
    promotions: [
      { productId: 'arroz-5kg', discountPct: 15 },
      { productId: 'frango-kg', discountPct: 14 },
      { productId: 'sabao-po-1kg', discountPct: 12 },
    ],
    unavailable: [],
  },
  {
    id: 'prezunic-meier',
    name: 'Prezunic',
    bairroId: 'meier',
    address: 'Rua Arquias Cordeiro, 312',
    overallFactor: 0.95,
    categoryFactors: { 'Carnes e Frios': 0.91, 'Padaria': 0.94 },
    promotions: [
      { productId: 'contra-file-kg', discountPct: 14 },
      { productId: 'linguica-kg', discountPct: 10 },
    ],
    unavailable: [],
  },
  {
    id: 'mundial-meier',
    name: 'Supermercados Mundial',
    bairroId: 'meier',
    address: 'Av. Amaro Cavalcanti, 35',
    overallFactor: 0.92,
    categoryFactors: { 'Hortifrúti': 0.87, 'Bebidas': 0.94 },
    promotions: [
      { productId: 'banana-kg', discountPct: 15 },
      { productId: 'suco-1l', discountPct: 10 },
    ],
    unavailable: [],
  },
];

/**
 * Mercados alcançáveis a partir de um bairro (o próprio + vizinhos),
 * com distância e custo estimado de deslocamento (ida e volta).
 */
export function marketsNear(homeBairroId: string, costPerKm: number): NearbyMarket[] {
  const result: NearbyMarket[] = [];
  for (const market of MARKETS) {
    const km = distanceKm(homeBairroId, market.bairroId);
    if (km === null) continue;
    result.push({
      market,
      bairroName: getBairro(market.bairroId).name,
      distanceKm: km,
      travelCost: Math.round(2 * km * costPerKm * 100) / 100,
    });
  }
  return result;
}
