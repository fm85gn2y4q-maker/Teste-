export type Timeframe = '1d' | '1wk' | '1h';
export type Direction = 'bullish' | 'bearish' | 'neutral';
export type SchoolType = 'indicators' | 'candlestick' | 'priceAction';

export interface OHLCV {
  timestamp: number; // Unix ms
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface MarketData {
  ticker: string;
  name: string;
  currentPrice: number;
  change: number; // % change today
  candles: OHLCV[];
  timeframe: Timeframe;
}

export interface SignalResult {
  school: SchoolType;
  score: number; // -100 to +100
  confidence: number; // 0 to 1
  direction: Direction;
  signals: string[]; // human-readable
  stopLevel?: number;
  targetLevels: number[];
}

export interface ConvergenceResult {
  ticker: string;
  timestamp: number;
  overallScore: number; // -100 to +100
  direction: Direction;
  schools: SignalResult[];
  stopLoss: number;
  primaryTarget: number;
  secondaryTarget?: number;
  riskRewardRatio: number;
  asymmetryScore: number; // (R:R - 1) * confidence
}

export interface WatchlistAsset {
  ticker: string;
  name: string;
  currentPrice: number;
  change: number;
  convergence?: ConvergenceResult;
  lastUpdated?: number;
}
