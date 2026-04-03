import { OHLCV, SignalResult } from './types';

// ── Helpers ──────────────────────────────────────────────────────────────────

function sma(data: number[], period: number): number[] {
  const result: number[] = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) { result.push(NaN); continue; }
    const slice = data.slice(i - period + 1, i + 1);
    result.push(slice.reduce((a, b) => a + b, 0) / period);
  }
  return result;
}

function ema(data: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const result: number[] = new Array(data.length).fill(NaN);
  let firstValid = -1;
  for (let i = 0; i < data.length; i++) {
    if (!isNaN(data[i])) { firstValid = i; break; }
  }
  if (firstValid === -1 || firstValid + period - 1 >= data.length) return result;
  const seed = data.slice(firstValid, firstValid + period).reduce((a, b) => a + b, 0) / period;
  result[firstValid + period - 1] = seed;
  for (let i = firstValid + period; i < data.length; i++) {
    result[i] = data[i] * k + result[i - 1] * (1 - k);
  }
  return result;
}

function std(data: number[], period: number): number[] {
  const result: number[] = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) { result.push(NaN); continue; }
    const slice = data.slice(i - period + 1, i + 1);
    const mean = slice.reduce((a, b) => a + b, 0) / period;
    const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / period;
    result.push(Math.sqrt(variance));
  }
  return result;
}

// ── RSI ───────────────────────────────────────────────────────────────────────

export function computeRSI(closes: number[], period = 14): number[] {
  const result: number[] = new Array(closes.length).fill(NaN);
  if (closes.length < period + 1) return result;

  let avgGain = 0, avgLoss = 0;
  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff > 0) avgGain += diff; else avgLoss += Math.abs(diff);
  }
  avgGain /= period;
  avgLoss /= period;

  result[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);

  for (let i = period + 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? Math.abs(diff) : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    result[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return result;
}

// ── MACD ──────────────────────────────────────────────────────────────────────

export function computeMACD(
  closes: number[],
  fast = 12,
  slow = 26,
  signal = 9,
): { macd: number[]; signal: number[]; histogram: number[] } {
  const emaFast = ema(closes, fast);
  const emaSlow = ema(closes, slow);
  const macd = closes.map((_, i) =>
    isNaN(emaFast[i]) || isNaN(emaSlow[i]) ? NaN : emaFast[i] - emaSlow[i],
  );
  const sig = ema(macd, signal);
  const histogram = macd.map((m, i) =>
    isNaN(m) || isNaN(sig[i]) ? NaN : m - sig[i],
  );
  return { macd, signal: sig, histogram };
}

// ── Bollinger Bands ───────────────────────────────────────────────────────────

export function computeBollinger(
  closes: number[],
  period = 20,
  multiplier = 2,
): { upper: number[]; middle: number[]; lower: number[] } {
  const middle = sma(closes, period);
  const s = std(closes, period);
  const upper = middle.map((m, i) => (isNaN(m) ? NaN : m + multiplier * s[i]));
  const lower = middle.map((m, i) => (isNaN(m) ? NaN : m - multiplier * s[i]));
  return { upper, middle, lower };
}

// ── Stochastic ────────────────────────────────────────────────────────────────

export function computeStochastic(
  candles: OHLCV[],
  kPeriod = 14,
  dPeriod = 3,
): { k: number[]; d: number[] } {
  const k: number[] = new Array(candles.length).fill(NaN);
  for (let i = kPeriod - 1; i < candles.length; i++) {
    const slice = candles.slice(i - kPeriod + 1, i + 1);
    const high = Math.max(...slice.map((c) => c.high));
    const low = Math.min(...slice.map((c) => c.low));
    k[i] = high === low ? 0 : ((candles[i].close - low) / (high - low)) * 100;
  }
  const d = sma(k.map((v) => (isNaN(v) ? 0 : v)), dPeriod);
  // re-apply NaN mask
  const dClean = d.map((v, i) => (i < kPeriod + dPeriod - 2 ? NaN : v));
  return { k, d: dClean };
}

// ── Moving Averages ───────────────────────────────────────────────────────────

export function computeMAs(closes: number[]): {
  sma20: number[];
  sma50: number[];
  sma200: number[];
  ema9: number[];
} {
  return {
    sma20: sma(closes, 20),
    sma50: sma(closes, 50),
    sma200: sma(closes, 200),
    ema9: ema(closes, 9),
  };
}

// ── ATR ───────────────────────────────────────────────────────────────────────

export function computeATR(candles: OHLCV[], period = 14): number[] {
  const tr: number[] = [NaN];
  for (let i = 1; i < candles.length; i++) {
    const hl = candles[i].high - candles[i].low;
    const hc = Math.abs(candles[i].high - candles[i - 1].close);
    const lc = Math.abs(candles[i].low - candles[i - 1].close);
    tr.push(Math.max(hl, hc, lc));
  }
  const atr: number[] = new Array(candles.length).fill(NaN);
  const seed = tr.slice(1, period + 1).reduce((a, b) => a + b, 0) / period;
  atr[period] = seed;
  for (let i = period + 1; i < candles.length; i++) {
    atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period;
  }
  return atr;
}

// ── School Analyzer: Technical Indicators ────────────────────────────────────

export function analyzeIndicators(candles: OHLCV[]): SignalResult {
  const closes = candles.map((c) => c.close);
  const n = closes.length;
  const price = closes[n - 1];

  const rsiArr = computeRSI(closes);
  const rsi = rsiArr[n - 1];

  const { macd: macdArr, signal: sigArr, histogram: histArr } = computeMACD(closes);
  const macd = macdArr[n - 1];
  const sig = sigArr[n - 1];
  const hist = histArr[n - 1];
  const prevHist = histArr[n - 2];

  const { upper, middle, lower } = computeBollinger(closes);
  const bb_upper = upper[n - 1];
  const bb_mid = middle[n - 1];
  const bb_lower = lower[n - 1];
  const bb_width = bb_upper - bb_lower;
  const bb_pct = bb_width > 0 ? (price - bb_lower) / bb_width : 0.5;

  const { k: kArr, d: dArr } = computeStochastic(candles);
  const stoch_k = kArr[n - 1];
  const stoch_d = dArr[n - 1];

  const { sma20, sma50, ema9 } = computeMAs(closes);

  // ── Score cada sub-indicador em [-100, +100]
  const scores: { val: number; weight: number; label: string }[] = [];
  const signals: string[] = [];

  // RSI
  if (!isNaN(rsi)) {
    let rsiScore = 0;
    if (rsi < 30) { rsiScore = -40 + ((30 - rsi) / 30) * -60; signals.push(`RSI ${rsi.toFixed(0)} — sobrevendido`); }
    else if (rsi > 70) { rsiScore = 40 + ((rsi - 70) / 30) * 60; signals.push(`RSI ${rsi.toFixed(0)} — sobrecomprado`); }
    else { rsiScore = (rsi - 50) * 1.6; }
    // Divergência simples: rsi subindo mas fechamento caindo
    const rsi5 = rsiArr[n - 5]; const price5 = closes[n - 5];
    if (!isNaN(rsi5)) {
      if (price < price5 && rsi > rsi5) { rsiScore += 20; signals.push('Divergência altista RSI'); }
      else if (price > price5 && rsi < rsi5) { rsiScore -= 20; signals.push('Divergência baixista RSI'); }
    }
    scores.push({ val: Math.max(-100, Math.min(100, rsiScore)), weight: 0.25, label: 'RSI' });
  }

  // MACD
  if (!isNaN(macd) && !isNaN(sig)) {
    let macdScore = macd > sig ? 50 : -50;
    if (!isNaN(prevHist)) {
      if (hist > 0 && prevHist < 0) { macdScore = 80; signals.push('MACD cruzou para cima'); }
      else if (hist < 0 && prevHist > 0) { macdScore = -80; signals.push('MACD cruzou para baixo'); }
      else if (hist > 0 && hist > prevHist) { macdScore = 60; signals.push('MACD histograma crescendo'); }
      else if (hist < 0 && hist < prevHist) { macdScore = -60; signals.push('MACD histograma caindo'); }
    }
    scores.push({ val: macdScore, weight: 0.25, label: 'MACD' });
  }

  // Bollinger
  if (!isNaN(bb_pct)) {
    let bbScore = 0;
    if (bb_pct < 0.1) { bbScore = -70; signals.push('Preço na banda inferior Bollinger'); }
    else if (bb_pct > 0.9) { bbScore = 70; signals.push('Preço na banda superior Bollinger'); }
    else { bbScore = (bb_pct - 0.5) * 100; }
    // Squeeze: bandas estreitas = breakout iminente (neutro por ora)
    const bb_pct_width = bb_width / bb_mid;
    if (bb_pct_width < 0.03) { signals.push('Bollinger Squeeze — breakout iminente'); bbScore *= 0.3; }
    scores.push({ val: Math.max(-100, Math.min(100, bbScore)), weight: 0.2, label: 'Bollinger' });
  }

  // Stochastic
  if (!isNaN(stoch_k) && !isNaN(stoch_d)) {
    let stochScore = 0;
    if (stoch_k < 20 && stoch_k > stoch_d) { stochScore = -60; signals.push(`Estocástico ${stoch_k.toFixed(0)} — sobrevendido`); }
    else if (stoch_k > 80 && stoch_k < stoch_d) { stochScore = 60; signals.push(`Estocástico ${stoch_k.toFixed(0)} — sobrecomprado`); }
    else { stochScore = (stoch_k - 50) * 1.2; }
    scores.push({ val: Math.max(-100, Math.min(100, stochScore)), weight: 0.15, label: 'Estocástico' });
  }

  // Médias móveis
  const ma20 = sma20[n - 1]; const ma50 = sma50[n - 1];
  if (!isNaN(ma20) && !isNaN(ma50)) {
    let maScore = 0;
    if (price > ma20 && price > ma50) maScore = 60;
    else if (price < ma20 && price < ma50) maScore = -60;
    else if (price > ma20) maScore = 25;
    else maScore = -25;
    // Golden/Death Cross
    const prevMa20 = sma20[n - 2]; const prevMa50 = sma50[n - 2];
    if (!isNaN(prevMa20) && !isNaN(prevMa50)) {
      if (ma20 > ma50 && prevMa20 <= prevMa50) { maScore = 90; signals.push('Golden Cross MM20/MM50'); }
      else if (ma20 < ma50 && prevMa20 >= prevMa50) { maScore = -90; signals.push('Death Cross MM20/MM50'); }
    }
    if (!isNaN(ema9[n - 1])) {
      const crossMsg = price > ema9[n - 1] ? 'Preço acima EMA9' : 'Preço abaixo EMA9';
      signals.push(crossMsg);
    }
    scores.push({ val: Math.max(-100, Math.min(100, maScore)), weight: 0.15, label: 'Médias Móveis' });
  }

  if (scores.length === 0) {
    return { school: 'indicators', score: 0, confidence: 0, direction: 'neutral', signals: ['Dados insuficientes'], targetLevels: [] };
  }

  const totalWeight = scores.reduce((a, s) => a + s.weight, 0);
  const weightedScore = scores.reduce((a, s) => a + s.val * s.weight, 0) / totalWeight;
  const confidence = Math.min(0.95, scores.length / 5 * 0.9);
  const direction = weightedScore > 15 ? 'bullish' : weightedScore < -15 ? 'bearish' : 'neutral';

  // ATR-based stop
  const atr = computeATR(candles);
  const atrVal = atr[n - 1];
  const stopLevel = isNaN(atrVal) ? undefined : price - atrVal * 2;
  const targetLevels = isNaN(atrVal) ? [] : [price + atrVal * 2, price + atrVal * 4];

  return {
    school: 'indicators',
    score: Math.round(weightedScore),
    confidence,
    direction,
    signals: signals.slice(0, 5),
    stopLevel,
    targetLevels,
  };
}
