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
  regionId: string;
  address: string;
  /** Multiplicador de preço por categoria (1 = preço de referência da região). */
  categoryFactors: Partial<Record<Category, number>>;
  /** Multiplicador geral do mercado (perfil caro/barato). */
  overallFactor: number;
  promotions: Promotion[];
  /** Produtos que este mercado não vende. */
  unavailable: string[];
}

export interface Region {
  id: string;
  name: string;
  /** Multiplicador de custo de vida da região. */
  costFactor: number;
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
  lines: QuoteLine[];
  missing: string[];
  /** Total apenas dos itens disponíveis. */
  availableTotal: number;
  /** Cobertura da lista (0–1). */
  coverage: number;
  totalSavedInPromos: number;
}

export interface PlanStop {
  market: Market;
  lines: QuoteLine[];
  subtotal: number;
}

export interface SmartPlan {
  stops: PlanStop[];
  itemsTotal: number;
  stopCost: number;
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
