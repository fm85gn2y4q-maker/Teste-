import { OHLCV, SignalResult } from './types';

interface Candle {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  body: number;
  range: number;
  upperShadow: number;
  lowerShadow: number;
  isBullish: boolean;
}

function toC(ohlcv: OHLCV): Candle {
  const body = Math.abs(ohlcv.close - ohlcv.open);
  const range = ohlcv.high - ohlcv.low;
  const isBullish = ohlcv.close >= ohlcv.open;
  const upperShadow = ohlcv.high - Math.max(ohlcv.open, ohlcv.close);
  const lowerShadow = Math.min(ohlcv.open, ohlcv.close) - ohlcv.low;
  return { ...ohlcv, body, range, upperShadow, lowerShadow, isBullish };
}

// Calcula o tamanho médio de corpo nos últimos N candles
function avgBody(candles: Candle[], n: number, idx: number): number {
  const slice = candles.slice(Math.max(0, idx - n), idx);
  if (slice.length === 0) return 0;
  return slice.reduce((a, c) => a + c.body, 0) / slice.length;
}

interface PatternHit {
  name: string;
  score: number; // -100 to +100
  confidence: number;
}

// ── Detectores de padrão ─────────────────────────────────────────────────────

function detectHammer(c: Candle, prev: Candle, avg: number): PatternHit | null {
  // Hammer: sombra inferior >= 2x corpo, corpo pequeno no topo, após queda
  if (!prev.isBullish && c.lowerShadow >= 2 * c.body && c.upperShadow < c.body && c.body > 0) {
    const conf = Math.min(0.9, (c.lowerShadow / c.body) / 5);
    return { name: 'Hammer', score: 65, confidence: conf };
  }
  return null;
}

function detectInvHammer(c: Candle, prev: Candle): PatternHit | null {
  if (!prev.isBullish && c.upperShadow >= 2 * c.body && c.lowerShadow < c.body * 0.5 && c.body > 0) {
    return { name: 'Inverted Hammer', score: 45, confidence: 0.55 };
  }
  return null;
}

function detectShootingStar(c: Candle, prev: Candle): PatternHit | null {
  if (prev.isBullish && c.upperShadow >= 2 * c.body && c.lowerShadow < c.body * 0.3 && c.body > 0) {
    return { name: 'Shooting Star', score: -70, confidence: 0.75 };
  }
  return null;
}

function detectHangingMan(c: Candle, prev: Candle): PatternHit | null {
  if (prev.isBullish && c.lowerShadow >= 2 * c.body && c.upperShadow < c.body * 0.5 && c.body > 0) {
    return { name: 'Hanging Man', score: -55, confidence: 0.6 };
  }
  return null;
}

function detectDoji(c: Candle, avg: number): PatternHit | null {
  // Doji: corpo <= 5% do range médio
  if (c.range > 0 && c.body <= avg * 0.05) {
    return { name: 'Doji', score: 0, confidence: 0.5 };
  }
  return null;
}

function detectBullEngulfing(curr: Candle, prev: Candle): PatternHit | null {
  if (!prev.isBullish && curr.isBullish && curr.open < prev.close && curr.close > prev.open) {
    return { name: 'Bullish Engulfing', score: 80, confidence: 0.80 };
  }
  return null;
}

function detectBearEngulfing(curr: Candle, prev: Candle): PatternHit | null {
  if (prev.isBullish && !curr.isBullish && curr.open > prev.close && curr.close < prev.open) {
    return { name: 'Bearish Engulfing', score: -80, confidence: 0.80 };
  }
  return null;
}

function detectPiercingLine(curr: Candle, prev: Candle): PatternHit | null {
  const mid = (prev.open + prev.close) / 2;
  if (!prev.isBullish && curr.isBullish && curr.open < prev.low && curr.close > mid && curr.close < prev.open) {
    return { name: 'Piercing Line', score: 65, confidence: 0.65 };
  }
  return null;
}

function detectDarkCloud(curr: Candle, prev: Candle): PatternHit | null {
  const mid = (prev.open + prev.close) / 2;
  if (prev.isBullish && !curr.isBullish && curr.open > prev.high && curr.close < mid && curr.close > prev.open) {
    return { name: 'Dark Cloud Cover', score: -65, confidence: 0.65 };
  }
  return null;
}

function detectMorningStar(a: Candle, b: Candle, c: Candle, avg: number): PatternHit | null {
  // a: grande vela baixista, b: corpo pequeno (star), c: grande vela altista
  if (!a.isBullish && a.body > avg * 0.6 && b.body < avg * 0.3 && c.isBullish && c.body > avg * 0.6 && c.close > (a.open + a.close) / 2) {
    return { name: 'Morning Star', score: 85, confidence: 0.82 };
  }
  return null;
}

function detectEveningStar(a: Candle, b: Candle, c: Candle, avg: number): PatternHit | null {
  if (a.isBullish && a.body > avg * 0.6 && b.body < avg * 0.3 && !c.isBullish && c.body > avg * 0.6 && c.close < (a.open + a.close) / 2) {
    return { name: 'Evening Star', score: -85, confidence: 0.82 };
  }
  return null;
}

function detectThreeWhiteSoldiers(a: Candle, b: Candle, c: Candle, avg: number): PatternHit | null {
  if (a.isBullish && b.isBullish && c.isBullish && a.body > avg * 0.5 && b.body > avg * 0.5 && c.body > avg * 0.5 && b.open > a.open && c.open > b.open && b.close > a.close && c.close > b.close) {
    return { name: 'Three White Soldiers', score: 90, confidence: 0.85 };
  }
  return null;
}

function detectThreeBlackCrows(a: Candle, b: Candle, c: Candle, avg: number): PatternHit | null {
  if (!a.isBullish && !b.isBullish && !c.isBullish && a.body > avg * 0.5 && b.body > avg * 0.5 && c.body > avg * 0.5 && b.open < a.open && c.open < b.open && b.close < a.close && c.close < b.close) {
    return { name: 'Three Black Crows', score: -90, confidence: 0.85 };
  }
  return null;
}

// ── School Analyzer: Candlestick ──────────────────────────────────────────────

export function analyzeCandlestick(rawCandles: OHLCV[]): SignalResult {
  if (rawCandles.length < 3) {
    return { school: 'candlestick', score: 0, confidence: 0, direction: 'neutral', signals: ['Dados insuficientes'], targetLevels: [] };
  }

  const candles = rawCandles.map(toC);
  const n = candles.length;
  const avg = avgBody(candles, 20, n - 1) || candles[n - 1].range * 0.3;

  const hits: PatternHit[] = [];

  const c0 = candles[n - 1];
  const c1 = candles[n - 2];
  const c2 = candles[n - 3];

  // Padrões de 1 candle
  const doji = detectDoji(c0, avg);
  if (doji) hits.push(doji);

  if (!doji) {
    const hammer = detectHammer(c0, c1, avg);
    if (hammer) hits.push(hammer);

    const invHammer = detectInvHammer(c0, c1);
    if (invHammer) hits.push(invHammer);

    const shootingStar = detectShootingStar(c0, c1);
    if (shootingStar) hits.push(shootingStar);

    const hangingMan = detectHangingMan(c0, c1);
    if (hangingMan) hits.push(hangingMan);
  }

  // Padrões de 2 candles
  const bullEng = detectBullEngulfing(c0, c1);
  if (bullEng) hits.push(bullEng);

  const bearEng = detectBearEngulfing(c0, c1);
  if (bearEng) hits.push(bearEng);

  const piercing = detectPiercingLine(c0, c1);
  if (piercing) hits.push(piercing);

  const darkCloud = detectDarkCloud(c0, c1);
  if (darkCloud) hits.push(darkCloud);

  // Padrões de 3 candles
  const morning = detectMorningStar(c2, c1, c0, avg);
  if (morning) hits.push(morning);

  const evening = detectEveningStar(c2, c1, c0, avg);
  if (evening) hits.push(evening);

  const soldiers = detectThreeWhiteSoldiers(c2, c1, c0, avg);
  if (soldiers) hits.push(soldiers);

  const crows = detectThreeBlackCrows(c2, c1, c0, avg);
  if (crows) hits.push(crows);

  if (hits.length === 0) {
    // Sem padrão claro — score neutro baseado na vela atual
    const bodyScore = c0.isBullish ? (c0.body / (c0.range || 1)) * 20 : -(c0.body / (c0.range || 1)) * 20;
    return {
      school: 'candlestick',
      score: Math.round(bodyScore),
      confidence: 0.3,
      direction: 'neutral',
      signals: ['Sem padrão relevante detectado'],
      targetLevels: [],
    };
  }

  // Prioriza o hit com maior |score|
  hits.sort((a, b) => Math.abs(b.score) - Math.abs(a.score));
  const primary = hits[0];

  // Contexto: padrão no suporte/resistência aumenta confiança
  const recentHigh = Math.max(...rawCandles.slice(-20).map((c) => c.high));
  const recentLow = Math.min(...rawCandles.slice(-20).map((c) => c.low));
  const price = c0.close;
  const nearSupport = (price - recentLow) / (recentHigh - recentLow) < 0.2;
  const nearResistance = (price - recentLow) / (recentHigh - recentLow) > 0.8;
  const contextMultiplier = (nearSupport && primary.score > 0) || (nearResistance && primary.score < 0) ? 1.2 : 1.0;

  const finalScore = Math.max(-100, Math.min(100, primary.score * contextMultiplier));
  const confidence = Math.min(0.95, primary.confidence * contextMultiplier);
  const direction = finalScore > 15 ? 'bullish' : finalScore < -15 ? 'bearish' : 'neutral';

  const signals = hits.slice(0, 3).map((h) => `${h.name} (${h.score > 0 ? '+' : ''}${h.score})`);
  if (nearSupport && primary.score > 0) signals.push('Padrão em nível de suporte — maior confiabilidade');
  if (nearResistance && primary.score < 0) signals.push('Padrão em nível de resistência — maior confiabilidade');

  const atr = c0.range;
  const targetLevels = primary.score > 0
    ? [price + atr * 1.5, price + atr * 3]
    : [price - atr * 1.5, price - atr * 3];

  return {
    school: 'candlestick',
    score: Math.round(finalScore),
    confidence,
    direction,
    signals,
    stopLevel: primary.score > 0 ? recentLow : recentHigh,
    targetLevels,
  };
}
