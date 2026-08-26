import {
  ComparisonResult,
  MarketQuote,
  NearbyMarket,
  PlanStop,
  QuoteLine,
  ShoppingItem,
  SmartPlan,
} from '../types';
import { effectiveUnitPrice, fullUnitPrice, promotionFor, quoteMarket } from './pricing';

export interface PlannerOptions {
  /** Número máximo de mercados no plano dividido. */
  maxStops: number;
  /** Custo estimado (R$/km) de deslocamento — combustível/tempo. */
  costPerKm: number;
}

export const DEFAULT_PLANNER_OPTIONS: PlannerOptions = {
  maxStops: 3,
  costPerKm: 1.5,
};

function round(value: number): number {
  return Math.round(value * 100) / 100;
}

/**
 * Ordena orçamentos por custo-benefício: primeiro maior cobertura da lista,
 * depois menor custo efetivo (itens + deslocamento).
 */
export function rankQuotes(quotes: MarketQuote[]): MarketQuote[] {
  return [...quotes].sort((a, b) => {
    if (a.coverage !== b.coverage) return b.coverage - a.coverage;
    return a.effectiveTotal - b.effectiveTotal;
  });
}

function subsetsUpTo<T>(items: T[], maxSize: number): T[][] {
  const result: T[][] = [];
  const n = items.length;
  for (let mask = 1; mask < 1 << n; mask++) {
    const subset: T[] = [];
    for (let i = 0; i < n; i++) {
      if (mask & (1 << i)) subset.push(items[i]);
    }
    if (subset.length <= maxSize) result.push(subset);
  }
  return result;
}

interface SubsetEvaluation {
  used: NearbyMarket[];
  assignment: Map<string, ShoppingItem[]>;
  itemsTotal: number;
  travelCost: number;
  missing: string[];
  effectiveTotal: number;
  coveredCount: number;
}

function evaluateSubset(subset: NearbyMarket[], list: ShoppingItem[]): SubsetEvaluation {
  const assignment = new Map<string, ShoppingItem[]>();
  const missing: string[] = [];
  let itemsTotal = 0;
  const usedIds = new Set<string>();

  for (const item of list) {
    let best: { nearby: NearbyMarket; price: number } | null = null;
    for (const nearby of subset) {
      const price = effectiveUnitPrice(nearby.market, item.productId);
      if (price !== null && (best === null || price < best.price)) {
        best = { nearby, price };
      }
    }
    if (!best) {
      missing.push(item.productId);
      continue;
    }
    itemsTotal += best.price * item.quantity;
    usedIds.add(best.nearby.market.id);
    const bucket = assignment.get(best.nearby.market.id) ?? [];
    bucket.push(item);
    assignment.set(best.nearby.market.id, bucket);
  }

  const used = subset.filter((n) => usedIds.has(n.market.id));
  const travelCost = round(used.reduce((sum, n) => sum + n.travelCost, 0));
  return {
    used,
    assignment,
    itemsTotal: round(itemsTotal),
    travelCost,
    missing,
    effectiveTotal: round(itemsTotal + travelCost),
    coveredCount: list.length - missing.length,
  };
}

/**
 * Plano inteligente: testa todas as combinações de até `maxStops` mercados
 * próximos, atribui cada item ao mercado mais barato da combinação e escolhe
 * a combinação com maior cobertura e menor custo efetivo, já somando o
 * deslocamento até cada mercado visitado.
 */
export function buildSmartPlan(
  nearby: NearbyMarket[],
  list: ShoppingItem[],
  options: PlannerOptions,
  bestSingleEffectiveTotal: number | null,
): SmartPlan | null {
  if (list.length === 0 || nearby.length === 0) return null;

  let best: SubsetEvaluation | null = null;
  for (const subset of subsetsUpTo(nearby, options.maxStops)) {
    const evaluated = evaluateSubset(subset, list);
    if (
      best === null ||
      evaluated.coveredCount > best.coveredCount ||
      (evaluated.coveredCount === best.coveredCount &&
        evaluated.effectiveTotal < best.effectiveTotal)
    ) {
      best = evaluated;
    }
  }
  if (!best) return null;

  const stops: PlanStop[] = best.used.map((n) => {
    const items = best!.assignment.get(n.market.id) ?? [];
    const lines: QuoteLine[] = items.map((item) => {
      const unitPrice = effectiveUnitPrice(n.market, item.productId)!;
      return {
        productId: item.productId,
        quantity: item.quantity,
        unitPrice,
        fullUnitPrice: fullUnitPrice(n.market, item.productId),
        discountPct: promotionFor(n.market, item.productId),
        lineTotal: round(unitPrice * item.quantity),
      };
    });
    return {
      market: n.market,
      bairroName: n.bairroName,
      distanceKm: n.distanceKm,
      travelCost: n.travelCost,
      lines,
      subtotal: round(lines.reduce((sum, l) => sum + l.lineTotal, 0)),
    };
  });
  stops.sort((a, b) => b.subtotal - a.subtotal);

  return {
    stops,
    itemsTotal: best.itemsTotal,
    travelCost: best.travelCost,
    effectiveTotal: best.effectiveTotal,
    missing: best.missing,
    savingsVsBestSingle:
      bestSingleEffectiveTotal === null ? 0 : round(bestSingleEffectiveTotal - best.effectiveTotal),
  };
}

/**
 * Comparação completa a partir do bairro do usuário: orçamento por mercado
 * próximo (custo-benefício = itens + deslocamento) + plano dividido ótimo.
 */
export function compareNearby(
  nearby: NearbyMarket[],
  list: ShoppingItem[],
  options: PlannerOptions = DEFAULT_PLANNER_OPTIONS,
): ComparisonResult {
  const quotes = rankQuotes(nearby.map((n) => quoteMarket(n, list)));
  const bestSingle = quotes.length > 0 && list.length > 0 ? quotes[0] : null;

  const complete = quotes.filter((q) => q.missing.length === 0);
  const worstComplete = complete.length > 1 ? complete[complete.length - 1] : null;

  const plan = buildSmartPlan(
    nearby,
    list,
    options,
    bestSingle ? bestSingle.effectiveTotal : null,
  );

  return { quotes, bestSingle, worstComplete, plan };
}
