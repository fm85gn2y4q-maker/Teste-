import { getProduct } from '../data/catalog';
import { getBairro } from '../data/bairros';
import { Market, MarketQuote, NearbyMarket, QuoteLine, ShoppingItem } from '../types';

/**
 * Hash determinístico (mercado, produto) → variação de -4% a +4%,
 * para que os preços variem por item e não apenas por categoria.
 */
function priceJitter(marketId: string, productId: string): number {
  const key = `${marketId}:${productId}`;
  let h = 2166136261;
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  const unit = ((h >>> 0) % 1000) / 1000; // 0–1
  return 0.96 + unit * 0.08;
}

function roundPrice(value: number): number {
  return Math.round(value * 100) / 100;
}

/** Preço de tabela (sem promoção) de um produto em um mercado. */
export function fullUnitPrice(market: Market, productId: string): number {
  const product = getProduct(productId);
  const bairro = getBairro(market.bairroId);
  const categoryFactor = market.categoryFactors[product.category] ?? 1;
  return roundPrice(
    product.basePrice *
      bairro.costFactor *
      market.overallFactor *
      categoryFactor *
      priceJitter(market.id, productId),
  );
}

export function promotionFor(market: Market, productId: string): number {
  return market.promotions.find((p) => p.productId === productId)?.discountPct ?? 0;
}

/** Preço efetivo (com promoção aplicada), ou null se o mercado não vende o produto. */
export function effectiveUnitPrice(market: Market, productId: string): number | null {
  if (market.unavailable.includes(productId)) return null;
  const full = fullUnitPrice(market, productId);
  const discountPct = promotionFor(market, productId);
  return roundPrice(full * (1 - discountPct / 100));
}

/** Orçamento completo de uma lista de compras em um único mercado próximo. */
export function quoteMarket(nearby: NearbyMarket, list: ShoppingItem[]): MarketQuote {
  const { market } = nearby;
  const lines: QuoteLine[] = [];
  const missing: string[] = [];
  let totalSavedInPromos = 0;

  for (const item of list) {
    const unitPrice = effectiveUnitPrice(market, item.productId);
    if (unitPrice === null) {
      missing.push(item.productId);
      continue;
    }
    const full = fullUnitPrice(market, item.productId);
    lines.push({
      productId: item.productId,
      quantity: item.quantity,
      unitPrice,
      fullUnitPrice: full,
      discountPct: promotionFor(market, item.productId),
      lineTotal: roundPrice(unitPrice * item.quantity),
    });
    totalSavedInPromos += (full - unitPrice) * item.quantity;
  }

  const availableTotal = roundPrice(lines.reduce((sum, l) => sum + l.lineTotal, 0));
  return {
    market,
    bairroName: nearby.bairroName,
    distanceKm: nearby.distanceKm,
    travelCost: nearby.travelCost,
    lines,
    missing,
    availableTotal,
    effectiveTotal: roundPrice(availableTotal + nearby.travelCost),
    coverage: list.length === 0 ? 1 : (list.length - missing.length) / list.length,
    totalSavedInPromos: roundPrice(totalSavedInPromos),
  };
}
