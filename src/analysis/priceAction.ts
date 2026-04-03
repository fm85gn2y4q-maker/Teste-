import { OHLCV, SignalResult } from './types';

// ── Swing points ──────────────────────────────────────────────────────────────

function findSwingHighs(candles: OHLCV[], lookback = 3): number[] {
  const highs: number[] = [];
  for (let i = lookback; i < candles.length - lookback; i++) {
    const win = candles.slice(i - lookback, i + lookback + 1);
    if (candles[i].high === Math.max(...win.map((c) => c.high))) {
      highs.push(candles[i].high);
    }
  }
  return highs;
}

function findSwingLows(candles: OHLCV[], lookback = 3): number[] {
  const lows: number[] = [];
  for (let i = lookback; i < candles.length - lookback; i++) {
    const win = candles.slice(i - lookback, i + lookback + 1);
    if (candles[i].low === Math.min(...win.map((c) => c.low))) {
      lows.push(candles[i].low);
    }
  }
  return lows;
}

// ── Trend detection via Higher Highs / Lower Lows ────────────────────────────

type Trend = 'uptrend' | 'downtrend' | 'ranging';

function detectTrend(candles: OHLCV[]): { trend: Trend; strength: number } {
  if (candles.length < 10) return { trend: 'ranging', strength: 0 };

  const highs = findSwingHighs(candles, 2);
  const lows = findSwingLows(candles, 2);

  if (highs.length < 2 || lows.length < 2) return { trend: 'ranging', strength: 0.3 };

  const lastHighs = highs.slice(-3);
  const lastLows = lows.slice(-3);

  const hhCount = lastHighs.filter((h, i) => i === 0 || h > lastHighs[i - 1]).length;
  const llCount = lastLows.filter((l, i) => i === 0 || l > lastLows[i - 1]).length;
  const lhCount = lastHighs.filter((h, i) => i === 0 || h < lastHighs[i - 1]).length;
  const hlCount = lastLows.filter((l, i) => i === 0 || l < lastLows[i - 1]).length;

  const upScore = hhCount + llCount;
  const downScore = lhCount + hlCount;

  if (upScore > downScore && upScore >= 3) {
    return { trend: 'uptrend', strength: Math.min(1, upScore / 6) };
  } else if (downScore > upScore && downScore >= 3) {
    return { trend: 'downtrend', strength: Math.min(1, downScore / 6) };
  }
  return { trend: 'ranging', strength: 0.3 };
}

// ── Níveis de suporte e resistência (cluster de swing points) ─────────────────

function clusterLevels(levels: number[], tolerance: number): number[] {
  if (levels.length === 0) return [];
  const sorted = [...levels].sort((a, b) => a - b);
  const clusters: number[][] = [[sorted[0]]];
  for (let i = 1; i < sorted.length; i++) {
    const last = clusters[clusters.length - 1];
    if (sorted[i] - last[last.length - 1] <= tolerance) {
      last.push(sorted[i]);
    } else {
      clusters.push([sorted[i]]);
    }
  }
  return clusters.map((cl) => cl.reduce((a, b) => a + b, 0) / cl.length);
}

function findSupportResistance(candles: OHLCV[]): { supports: number[]; resistances: number[] } {
  const price = candles[candles.length - 1].close;
  const tolerance = price * 0.005; // 0.5%

  const swingHighs = findSwingHighs(candles, 3);
  const swingLows = findSwingLows(candles, 3);

  const allResist = swingHighs.filter((h) => h > price);
  const allSupport = swingLows.filter((l) => l < price);

  return {
    supports: clusterLevels(allSupport, tolerance).slice(-3),
    resistances: clusterLevels(allResist, tolerance).slice(0, 3),
  };
}

// ── Detecção de padrões clássicos simples ─────────────────────────────────────

interface ClassicPattern {
  name: string;
  score: number;
}

function detectHeadAndShoulders(candles: OHLCV[]): ClassicPattern | null {
  const highs = findSwingHighs(candles, 3);
  if (highs.length < 5) return null;
  const last5 = highs.slice(-5);
  const [l1, l2, head, r1, r2] = last5;
  const shoulder = (l1 + r2) / 2;
  if (head > l1 * 1.02 && head > r2 * 1.02 && Math.abs(l1 - r2) / l1 < 0.05) {
    return { name: 'Ombro-Cabeça-Ombro (reversão baixista)', score: -75 };
  }
  return null;
}

function detectInvHeadAndShoulders(candles: OHLCV[]): ClassicPattern | null {
  const lows = findSwingLows(candles, 3);
  if (lows.length < 5) return null;
  const last5 = lows.slice(-5);
  const [l1, l2, head, r1, r2] = last5;
  if (head < l1 * 0.98 && head < r2 * 0.98 && Math.abs(l1 - r2) / l1 < 0.05) {
    return { name: 'OCO Invertido (reversão altista)', score: 75 };
  }
  return null;
}

function detectAscendingTriangle(candles: OHLCV[]): ClassicPattern | null {
  const recent = candles.slice(-30);
  const highs = recent.map((c) => c.high);
  const lows = recent.map((c) => c.low);
  const maxHigh = Math.max(...highs);
  const minLow = Math.min(...lows);
  // Máximas quase iguais + mínimas subindo = triângulo ascendente
  const topVariance = highs.filter((h) => h > maxHigh * 0.98).length;
  if (topVariance >= 2 && lows[lows.length - 1] > lows[0] * 1.02) {
    return { name: 'Triângulo Ascendente (breakout altista esperado)', score: 60 };
  }
  return null;
}

// ── School Analyzer: Price Action & Classical Patterns ───────────────────────

export function analyzePriceAction(candles: OHLCV[]): SignalResult {
  if (candles.length < 20) {
    return { school: 'priceAction', score: 0, confidence: 0, direction: 'neutral', signals: ['Dados insuficientes'], targetLevels: [] };
  }

  const price = candles[candles.length - 1].close;
  const signals: string[] = [];
  let score = 0;
  let confidence = 0.5;

  // ── Tendência
  const { trend, strength } = detectTrend(candles);
  const trendScore = trend === 'uptrend' ? strength * 70 : trend === 'downtrend' ? -strength * 70 : 0;
  score += trendScore * 0.5;
  if (trend !== 'ranging') {
    signals.push(`${trend === 'uptrend' ? 'Tendência de alta' : 'Tendência de baixa'} confirmada (HH/HL ou LH/LL)`);
    confidence += 0.15;
  } else {
    signals.push('Mercado em consolidação — aguardar direcional');
  }

  // ── Suportes e Resistências
  const { supports, resistances } = findSupportResistance(candles);
  const nearestSupport = supports.length > 0 ? supports[supports.length - 1] : null;
  const nearestResistance = resistances.length > 0 ? resistances[0] : null;

  if (nearestSupport && nearestResistance) {
    const rangeTotal = nearestResistance - nearestSupport;
    const pricePos = (price - nearestSupport) / rangeTotal;

    if (pricePos < 0.15) {
      score += 50; confidence += 0.1;
      signals.push(`Preço próximo ao suporte R$${nearestSupport.toFixed(2)}`);
    } else if (pricePos > 0.85) {
      score -= 50; confidence += 0.1;
      signals.push(`Preço próximo à resistência R$${nearestResistance.toFixed(2)}`);
    } else {
      signals.push(`Preço entre S/R: R$${nearestSupport.toFixed(2)} – R$${nearestResistance.toFixed(2)}`);
    }
  }

  // ── Padrões clássicos
  const hs = detectHeadAndShoulders(candles);
  if (hs) { score += hs.score * 0.5; confidence += 0.1; signals.push(hs.name); }

  const ihs = detectInvHeadAndShoulders(candles);
  if (ihs) { score += ihs.score * 0.5; confidence += 0.1; signals.push(ihs.name); }

  const asc = detectAscendingTriangle(candles);
  if (asc) { score += asc.score * 0.4; confidence += 0.08; signals.push(asc.name); }

  score = Math.max(-100, Math.min(100, score));
  confidence = Math.min(0.9, confidence);
  const direction = score > 15 ? 'bullish' : score < -15 ? 'bearish' : 'neutral';

  // Stops e targets baseados em S/R
  const stopLevel = nearestSupport ?? price * 0.97;
  const primaryTarget = nearestResistance ?? price * 1.05;
  const targetLevels = nearestResistance ? [nearestResistance] : [price * 1.05];
  if (nearestResistance && supports.length > 1) {
    const rangeSize = nearestResistance - (nearestSupport ?? 0);
    targetLevels.push(nearestResistance + rangeSize * 0.5);
  }

  return {
    school: 'priceAction',
    score: Math.round(score),
    confidence,
    direction,
    signals: signals.slice(0, 5),
    stopLevel,
    targetLevels,
  };
}
