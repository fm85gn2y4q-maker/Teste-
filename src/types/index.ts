export type Category =
  | 'Básicos'
  | 'Hortifrúti'
  | 'Carnes e Frios'
  | 'Laticínios'
  | 'Padaria'
  | 'Bebidas'
  | 'Limpeza'
  | 'Higiene';

export interface Product {
  id: string;
  name: string;
  unit: string;
  category: Category;
  basePrice: number;
  aliases?: string[];
}

export interface Promotion {
  productId: string;
  discountPct: number;
}

export interface Market {
  id: string;
  name: string;
  bairroId: string;
  address: string;
  /** Multiplicador de preço por categoria (1 = preço de referência). */
  categoryFactors: Partial<Record<Category, number>>;
  /** Multiplicador geral do mercado (perfil caro/barato da rede). */
  overallFactor: number;
  promotions: Promotion[];
  /** Produtos que este mercado não vende. */
  unavailable: string[];
}

/** Mercado alcançável a partir do bairro do usuário. */
export interface NearbyMarket {
  market: Market;
  bairroName: string;
  distanceKm: number;
  /** Custo estimado de ida e volta até este mercado. */
  travelCost: number;
}

export interface ShoppingItem {
  productId: string;
  quantity: number;
}

export interface QuoteLine {
  productId: string;
  quantity: number;
  unitPrice: number;
  fullUnitPrice: number;
  discountPct: number;
  lineTotal: number;
}

export interface MarketQuote {
  market: Market;
  bairroName: string;
  distanceKm: number;
  travelCost: number;
  lines: QuoteLine[];
  missing: string[];
  /** Total apenas dos itens disponíveis. */
  availableTotal: number;
  /** Custo-benefício: itens + deslocamento. */
  effectiveTotal: number;
  /** Cobertura da lista (0–1). */
  coverage: number;
  totalSavedInPromos: number;
}

export interface PlanStop {
  market: Market;
  bairroName: string;
  distanceKm: number;
  travelCost: number;
  lines: QuoteLine[];
  subtotal: number;
}

export interface SmartPlan {
  stops: PlanStop[];
  itemsTotal: number;
  travelCost: number;
  effectiveTotal: number;
  missing: string[];
  savingsVsBestSingle: number;
}

export interface ComparisonResult {
  quotes: MarketQuote[];
  bestSingle: MarketQuote | null;
  worstComplete: MarketQuote | null;
  plan: SmartPlan | null;
}
