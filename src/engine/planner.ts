import {
  ComparisonResult,
  Market,
  MarketQuote,
  PlanStop,
  QuoteLine,
  ShoppingItem,
  SmartPlan,
} from '../types';
import { effectiveUnitPrice, fullUnitPrice, promotionFor, quoteMarket } from './pricing';

export interface PlannerOptions {
  /** Número máximo de mercados no plano dividido. */
  maxStops: number;
  /** Custo estimado (R$) de deslocamento por mercado adicional visitado. */
  extraStopCost: number;
}

export const DEFAULT_PLANNER_OPTIONS: PlannerOptions = {
  maxStops: 3,
  extraStopCost: 8,
};

function round(value: number): number {
  return Math.round(value * 100) / 100;
}

/**
 * Ordena orçamentos: primeiro maior cobertura da lista, depois menor total.
 * Um mercado que não tem 3 itens da lista não pode "vencer" só por isso.
 */
export function rankQuotes(quotes: MarketQuote[]): MarketQuote[] {
  return [...quotes].sort((a, b) => {
    if (a.coverage !== b.coverage) return b.coverage - a.coverage;
    return a.availableTotal - b.availableTotal;
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
  markets: Market[];
  assignment: Map<string, { market: Market; item: ShoppingItem }[]>;
  itemsTotal: number;
  missing: string[];
  effectiveTotal: number;
  coveredCount: number;
}

function evaluateSubset(
  markets: Market[],
  list: ShoppingItem[],
  extraStopCost: number,
): SubsetEvaluation {
  const assignment = new Map<string, { market: Market; item: ShoppingItem }[]>();
  const missing: string[] = [];
  let itemsTotal = 0;
  const usedMarkets = new Set<string>();

  for (const item of list) {
    let best: { market: Market; price: number } | null = null;
    for (const market of markets) {
      const price = effectiveUnitPrice(market, item.productId);
      if (price !== null && (best === null || price < best.price)) {
        best = { market, price };
      }
    }
    if (!best) {
      missing.push(item.productId);
      continue;
    }
    itemsTotal += best.price * item.quantity;
    usedMarkets.add(best.market.id);
    const bucket = assignment.get(best.market.id) ?? [];
    bucket.push({ market: best.market, item });
    assignment.set(best.market.id, bucket);
  }

  const stopCost = Math.max(0, usedMarkets.size - 1) * extraStopCost;
  return {
    markets: markets.filter((m) => usedMarkets.has(m.id)),
    assignment,
    itemsTotal: round(itemsTotal),
    missing,
    effectiveTotal: round(itemsTotal + stopCost),
    coveredCount: list.length - missing.length,
  };
}

/**
 * Plano inteligente: testa todas as combinações de até `maxStops` mercados,
 * atribui cada item ao mercado mais barato da combinação e escolhe a
 * combinação com maior cobertura e menor custo efetivo (itens + deslocamento).
 */
export function buildSmartPlan(
  regionMarkets: Market[],
  list: ShoppingItem[],
  options: PlannerOptions,
  bestSingleTotal: number | null,
): SmartPlan | null {
  if (list.length === 0 || regionMarkets.length === 0) return null;

  let best: SubsetEvaluation | null = null;
  for (const subset of subsetsUpTo(regionMarkets, options.maxStops)) {
    const evaluated = evaluateSubset(subset, list, options.extraStopCost);
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

  const stops: PlanStop[] = best.markets.map((market) => {
    const entries = best!.assignment.get(market.id) ?? [];
    const lines: QuoteLine[] = entries.map(({ item }) => {
      const unitPrice = effectiveUnitPrice(market, item.productId)!;
      return {
        productId: item.productId,
        quantity: item.quantity,
        unitPrice,
        fullUnitPrice: fullUnitPrice(market, item.productId),
        discountPct: promotionFor(market, item.productId),
        lineTotal: round(unitPrice * item.quantity),
      };
    });
    return {
      market,
      lines,
      subtotal: round(lines.reduce((sum, l) => sum + l.lineTotal, 0)),
    };
  });
  stops.sort((a, b) => b.subtotal - a.subtotal);

  const stopCost = Math.max(0, stops.length - 1) * options.extraStopCost;
  return {
    stops,
    itemsTotal: best.itemsTotal,
    stopCost: round(stopCost),
    effectiveTotal: best.effectiveTotal,
    missing: best.missing,
    savingsVsBestSingle:
      bestSingleTotal === null ? 0 : round(bestSingleTotal - best.effectiveTotal),
  };
}

/** Comparação completa: orçamento por mercado + melhor mercado único + plano dividido. */
export function compareRegion(
  regionMarkets: Market[],
  list: ShoppingItem[],
  options: PlannerOptions = DEFAULT_PLANNER_OPTIONS,
): ComparisonResult {
  const quotes = rankQuotes(regionMarkets.map((m) => quoteMarket(m, list)));
  const bestSingle = quotes.length > 0 && list.length > 0 ? quotes[0] : null;

  const complete = quotes.filter((q) => q.missing.length === 0);
  const worstComplete = complete.length > 1 ? complete[complete.length - 1] : null;

  const plan = buildSmartPlan(
    regionMarkets,
    list,
    options,
    bestSingle ? bestSingle.availableTotal : null,
  );

  return { quotes, bestSingle, worstComplete, plan };
}
