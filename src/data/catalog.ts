import { Product } from '../types';

export const CATALOG: Product[] = [
  // Básicos
  { id: 'arroz-5kg', name: 'Arroz branco 5kg', unit: 'pct', category: 'Básicos', basePrice: 26.9, aliases: ['arroz'] },
  { id: 'feijao-1kg', name: 'Feijão carioca 1kg', unit: 'pct', category: 'Básicos', basePrice: 8.49, aliases: ['feijao', 'feijão'] },
  { id: 'acucar-1kg', name: 'Açúcar refinado 1kg', unit: 'pct', category: 'Básicos', basePrice: 4.99, aliases: ['acucar', 'açúcar'] },
  { id: 'sal-1kg', name: 'Sal refinado 1kg', unit: 'pct', category: 'Básicos', basePrice: 2.79, aliases: ['sal'] },
  { id: 'oleo-900ml', name: 'Óleo de soja 900ml', unit: 'un', category: 'Básicos', basePrice: 7.29, aliases: ['oleo', 'óleo'] },
  { id: 'macarrao-500g', name: 'Macarrão espaguete 500g', unit: 'pct', category: 'Básicos', basePrice: 4.59, aliases: ['macarrao', 'macarrão', 'espaguete'] },
  { id: 'farinha-trigo-1kg', name: 'Farinha de trigo 1kg', unit: 'pct', category: 'Básicos', basePrice: 5.89, aliases: ['farinha'] },
  { id: 'cafe-500g', name: 'Café torrado e moído 500g', unit: 'pct', category: 'Básicos', basePrice: 18.9, aliases: ['cafe', 'café'] },
  { id: 'molho-tomate', name: 'Molho de tomate 340g', unit: 'un', category: 'Básicos', basePrice: 3.29, aliases: ['molho'] },
  { id: 'milho-lata', name: 'Milho verde em conserva 170g', unit: 'lata', category: 'Básicos', basePrice: 3.99, aliases: ['milho'] },

  // Hortifrúti
  { id: 'banana-kg', name: 'Banana prata kg', unit: 'kg', category: 'Hortifrúti', basePrice: 6.99, aliases: ['banana'] },
  { id: 'maca-kg', name: 'Maçã gala kg', unit: 'kg', category: 'Hortifrúti', basePrice: 9.98, aliases: ['maca', 'maçã'] },
  { id: 'tomate-kg', name: 'Tomate kg', unit: 'kg', category: 'Hortifrúti', basePrice: 8.9, aliases: ['tomate'] },
  { id: 'cebola-kg', name: 'Cebola kg', unit: 'kg', category: 'Hortifrúti', basePrice: 5.49, aliases: ['cebola'] },
  { id: 'batata-kg', name: 'Batata inglesa kg', unit: 'kg', category: 'Hortifrúti', basePrice: 6.49, aliases: ['batata'] },
  { id: 'alface-un', name: 'Alface crespa un', unit: 'un', category: 'Hortifrúti', basePrice: 3.49, aliases: ['alface'] },
  { id: 'cenoura-kg', name: 'Cenoura kg', unit: 'kg', category: 'Hortifrúti', basePrice: 4.99, aliases: ['cenoura'] },
  { id: 'limao-kg', name: 'Limão tahiti kg', unit: 'kg', category: 'Hortifrúti', basePrice: 5.99, aliases: ['limao', 'limão'] },

  // Carnes e Frios
  { id: 'frango-kg', name: 'Peito de frango kg', unit: 'kg', category: 'Carnes e Frios', basePrice: 19.9, aliases: ['frango', 'peito de frango'] },
  { id: 'carne-moida-kg', name: 'Carne moída (patinho) kg', unit: 'kg', category: 'Carnes e Frios', basePrice: 39.9, aliases: ['carne moida', 'carne moída', 'patinho'] },
  { id: 'contra-file-kg', name: 'Contra-filé kg', unit: 'kg', category: 'Carnes e Frios', basePrice: 49.9, aliases: ['contra file', 'contra-filé', 'bife'] },
  { id: 'linguica-kg', name: 'Linguiça toscana kg', unit: 'kg', category: 'Carnes e Frios', basePrice: 22.9, aliases: ['linguica', 'linguiça'] },
  { id: 'presunto-200g', name: 'Presunto fatiado 200g', unit: 'pct', category: 'Carnes e Frios', basePrice: 8.9, aliases: ['presunto'] },
  { id: 'mussarela-200g', name: 'Queijo mussarela fatiado 200g', unit: 'pct', category: 'Carnes e Frios', basePrice: 10.9, aliases: ['mussarela', 'queijo'] },

  // Laticínios
  { id: 'leite-1l', name: 'Leite integral 1L', unit: 'un', category: 'Laticínios', basePrice: 5.79, aliases: ['leite'] },
  { id: 'manteiga-200g', name: 'Manteiga com sal 200g', unit: 'un', category: 'Laticínios', basePrice: 12.9, aliases: ['manteiga'] },
  { id: 'iogurte-170g', name: 'Iogurte natural 170g', unit: 'un', category: 'Laticínios', basePrice: 3.79, aliases: ['iogurte'] },
  { id: 'requeijao-200g', name: 'Requeijão cremoso 200g', unit: 'un', category: 'Laticínios', basePrice: 8.49, aliases: ['requeijao', 'requeijão'] },
  { id: 'ovos-12', name: 'Ovos brancos dúzia', unit: 'dz', category: 'Laticínios', basePrice: 12.9, aliases: ['ovos', 'ovo'] },

  // Padaria
  { id: 'pao-frances-kg', name: 'Pão francês kg', unit: 'kg', category: 'Padaria', basePrice: 16.9, aliases: ['pao frances', 'pão francês', 'pao'] },
  { id: 'pao-forma', name: 'Pão de forma 480g', unit: 'pct', category: 'Padaria', basePrice: 8.99, aliases: ['pao de forma', 'pão de forma'] },
  { id: 'bolo-pronto', name: 'Bolo pronto 250g', unit: 'un', category: 'Padaria', basePrice: 9.9, aliases: ['bolo'] },

  // Bebidas
  { id: 'refri-2l', name: 'Refrigerante cola 2L', unit: 'un', category: 'Bebidas', basePrice: 9.99, aliases: ['refrigerante', 'refri', 'coca'] },
  { id: 'suco-1l', name: 'Suco de uva integral 1L', unit: 'un', category: 'Bebidas', basePrice: 12.9, aliases: ['suco'] },
  { id: 'agua-1500ml', name: 'Água mineral 1,5L', unit: 'un', category: 'Bebidas', basePrice: 2.99, aliases: ['agua', 'água'] },
  { id: 'cerveja-lata', name: 'Cerveja pilsen lata 350ml', unit: 'lata', category: 'Bebidas', basePrice: 3.79, aliases: ['cerveja'] },

  // Limpeza
  { id: 'detergente-500ml', name: 'Detergente neutro 500ml', unit: 'un', category: 'Limpeza', basePrice: 2.89, aliases: ['detergente'] },
  { id: 'sabao-po-1kg', name: 'Sabão em pó 1kg', unit: 'cx', category: 'Limpeza', basePrice: 14.9, aliases: ['sabao', 'sabão', 'sabao em po'] },
  { id: 'agua-sanitaria-1l', name: 'Água sanitária 1L', unit: 'un', category: 'Limpeza', basePrice: 4.29, aliases: ['agua sanitaria', 'água sanitária'] },
  { id: 'amaciante-2l', name: 'Amaciante de roupas 2L', unit: 'un', category: 'Limpeza', basePrice: 13.9, aliases: ['amaciante'] },
  { id: 'esponja-4un', name: 'Esponja multiuso 4un', unit: 'pct', category: 'Limpeza', basePrice: 5.49, aliases: ['esponja'] },

  // Higiene
  { id: 'papel-hig-12', name: 'Papel higiênico 12 rolos', unit: 'pct', category: 'Higiene', basePrice: 21.9, aliases: ['papel higienico', 'papel higiênico', 'papel'] },
  { id: 'sabonete-90g', name: 'Sabonete 90g', unit: 'un', category: 'Higiene', basePrice: 2.99, aliases: ['sabonete'] },
  { id: 'creme-dental', name: 'Creme dental 90g', unit: 'un', category: 'Higiene', basePrice: 4.99, aliases: ['pasta de dente', 'creme dental'] },
  { id: 'shampoo-350ml', name: 'Shampoo 350ml', unit: 'un', category: 'Higiene', basePrice: 15.9, aliases: ['shampoo', 'xampu'] },
  { id: 'desodorante', name: 'Desodorante aerossol 150ml', unit: 'un', category: 'Higiene', basePrice: 13.9, aliases: ['desodorante'] },
];

export const PRODUCT_BY_ID: Record<string, Product> = Object.fromEntries(
  CATALOG.map((p) => [p.id, p]),
);

export function getProduct(id: string): Product {
  const p = PRODUCT_BY_ID[id];
  if (!p) throw new Error(`Produto desconhecido: ${id}`);
  return p;
}
