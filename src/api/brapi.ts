import { OHLCV, MarketData } from '../analysis/types';

const BASE_URL = 'https://brapi.dev/api';

let _apiToken = '';

export function setApiToken(token: string) {
  _apiToken = token;
}

function authParam(): string {
  return _apiToken ? `&token=${_apiToken}` : '';
}

// ── Tipos da resposta Brapi ───────────────────────────────────────────────────

interface BrapiQuote {
  symbol: string;
  shortName: string;
  regularMarketPrice: number;
  regularMarketChangePercent: number;
  historicalDataPrice?: BrapiHistorical[];
}

interface BrapiHistorical {
  date: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjustedClose: number;
}

interface BrapiQuoteResponse {
  results: BrapiQuote[];
  requestedAt: string;
}

// ── Busca cotação atual + histórico ──────────────────────────────────────────

export async function fetchMarketData(
  ticker: string,
  range: '1mo' | '3mo' | '6mo' | '1y' | '2y' = '6mo',
  interval: '1d' | '1wk' = '1d',
): Promise<MarketData> {
  const url =
    `${BASE_URL}/quote/${ticker}?` +
    `range=${range}&interval=${interval}&fundamental=false` +
    authParam();

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Brapi error ${response.status}: ${ticker}`);
  }

  const data: BrapiQuoteResponse = await response.json();
  const quote = data.results?.[0];

  if (!quote) {
    throw new Error(`Ativo não encontrado: ${ticker}`);
  }

  const candles: OHLCV[] = (quote.historicalDataPrice ?? []).map((h) => ({
    timestamp: h.date * 1000, // Brapi retorna segundos
    open: h.open,
    high: h.high,
    low: h.low,
    close: h.adjustedClose ?? h.close,
    volume: h.volume,
  })).filter((c) => c.open > 0 && c.close > 0);

  return {
    ticker: quote.symbol,
    name: quote.shortName ?? ticker,
    currentPrice: quote.regularMarketPrice,
    change: quote.regularMarketChangePercent,
    candles,
    timeframe: interval,
  };
}

// ── Busca múltiplos tickers (preço atual apenas) ──────────────────────────────

export interface QuoteSummary {
  ticker: string;
  name: string;
  price: number;
  change: number;
}

export async function fetchQuotes(tickers: string[]): Promise<QuoteSummary[]> {
  if (tickers.length === 0) return [];
  const joinedTickers = tickers.join(',');
  const url = `${BASE_URL}/quote/${joinedTickers}?fundamental=false${authParam()}`;

  const response = await fetch(url);
  if (!response.ok) throw new Error(`Brapi error ${response.status}`);

  const data: BrapiQuoteResponse = await response.json();
  return (data.results ?? []).map((q) => ({
    ticker: q.symbol,
    name: q.shortName ?? q.symbol,
    price: q.regularMarketPrice,
    change: q.regularMarketChangePercent,
  }));
}

// ── Busca lista de ativos (search) ───────────────────────────────────────────

export interface SearchResult {
  stock: string;
  name: string;
  type: string;
}

export async function searchTicker(query: string): Promise<SearchResult[]> {
  const url = `${BASE_URL}/available?search=${encodeURIComponent(query)}${authParam()}`;
  const response = await fetch(url);
  if (!response.ok) return [];
  const data = await response.json();
  return (data.stocks ?? []).slice(0, 20);
}
