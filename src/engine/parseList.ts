import { CATALOG } from '../data/catalog';
import { Product, ShoppingItem } from '../types';

export interface ParseResult {
  items: ShoppingItem[];
  unmatched: string[];
}

function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function matchProduct(query: string): Product | null {
  const q = normalize(query);
  if (!q) return null;

  let best: { product: Product; score: number } | null = null;
  for (const product of CATALOG) {
    const candidates = [product.name, ...(product.aliases ?? [])].map(normalize);
    for (const candidate of candidates) {
      let score = 0;
      if (candidate === q) score = 100;
      else if (candidate.startsWith(q) || q.startsWith(candidate)) score = 80;
      else if (candidate.includes(q) || q.includes(candidate)) score = 60;
      if (score > 0 && (best === null || score > best.score)) {
        best = { product, score };
      }
    }
  }
  return best?.product ?? null;
}

/**
 * Interpreta uma linha de lista de compras, aceitando formatos comuns:
 * "2 arroz", "2x feijão", "arroz x2", "leite - 3", "café".
 */
function parseLine(line: string): { query: string; quantity: number } | null {
  const trimmed = line.trim();
  if (!trimmed) return null;

  let quantity = 1;
  let query = trimmed;

  const leading = trimmed.match(/^(\d+)\s*[xX]?\s+(.+)$/);
  const trailing = trimmed.match(/^(.+?)\s*[-–xX]\s*(\d+)$/);
  if (leading) {
    quantity = parseInt(leading[1], 10);
    query = leading[2];
  } else if (trailing) {
    quantity = parseInt(trailing[2], 10);
    query = trailing[1];
  }

  if (quantity < 1 || quantity > 99) quantity = 1;
  return { query, quantity };
}

/** Converte texto colado (uma linha por item) em itens da lista de compras. */
export function parseShoppingList(text: string): ParseResult {
  const items = new Map<string, number>();
  const unmatched: string[] = [];

  for (const rawLine of text.split(/\r?\n|;|,/)) {
    const parsed = parseLine(rawLine);
    if (!parsed) continue;
    const product = matchProduct(parsed.query);
    if (product) {
      items.set(product.id, (items.get(product.id) ?? 0) + parsed.quantity);
    } else {
      unmatched.push(parsed.query);
    }
  }

  return {
    items: [...items.entries()].map(([productId, quantity]) => ({ productId, quantity })),
    unmatched,
  };
}
