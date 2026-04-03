import { OHLCV, ConvergenceResult, SignalResult, Direction } from './types';
import { analyzeIndicators } from './indicators';
import { analyzeCandlestick } from './candlestick';
import { analyzePriceAction } from './priceAction';

const SCHOOL_WEIGHTS: Record<string, number> = {
  indicators: 0.40,
  candlestick: 0.30,
  priceAction: 0.30,
};

export function runConvergenceAnalysis(
  ticker: string,
  candles: OHLCV[],
): ConvergenceResult {
  const timestamp = Date.now();

  // ── Rodar cada escola
  const schools: SignalResult[] = [
    analyzeIndicators(candles),
    analyzeCandlestick(candles),
    analyzePriceAction(candles),
  ];

  // ── Weighted average score
  let totalWeight = 0;
  let weightedSum = 0;
  for (const s of schools) {
    const w = SCHOOL_WEIGHTS[s.school] ?? 0.33;
    weightedSum += s.score * s.confidence * w;
    totalWeight += s.confidence * w;
  }
  const overallScore = totalWeight > 0 ? weightedSum / totalWeight : 0;

  // ── Confidence score da convergência (quão alinhadas estão as escolas)
  const directions = schools.map((s) => s.direction);
  const bullishCount = directions.filter((d) => d === 'bullish').length;
  const bearishCount = directions.filter((d) => d === 'bearish').length;
  const alignedCount = Math.max(bullishCount, bearishCount);
  const alignmentMultiplier = alignedCount === 3 ? 1.3 : alignedCount === 2 ? 1.0 : 0.6;

  // ── Direction
  const finalScore = Math.max(-100, Math.min(100, overallScore * alignmentMultiplier));
  const direction: Direction =
    finalScore > 20 ? 'bullish' : finalScore < -20 ? 'bearish' : 'neutral';

  // ── Stop loss: mediana dos stops individuais
  const stops = schools.map((s) => s.stopLevel).filter((s): s is number => s != null);
  const price = candles[candles.length - 1].close;
  const stopLoss = stops.length > 0 ? median(stops) : price * (direction === 'bullish' ? 0.97 : 1.03);

  // ── Targets: cluster dos targets individuais
  const allTargets = schools.flatMap((s) => s.targetLevels).filter((t) => {
    if (direction === 'bullish') return t > price;
    if (direction === 'bearish') return t < price;
    return false;
  });

  const sortedTargets = [...allTargets].sort((a, b) =>
    direction === 'bullish' ? a - b : b - a,
  );

  const primaryTarget = sortedTargets[0] ?? (direction === 'bullish' ? price * 1.05 : price * 0.95);
  const secondaryTarget = sortedTargets[1];

  // ── R:R
  const risk = Math.abs(price - stopLoss);
  const reward = Math.abs(primaryTarget - price);
  const riskRewardRatio = risk > 0 ? parseFloat((reward / risk).toFixed(2)) : 0;

  // ── Asymmetry score: (R:R - 1) × convergence confidence
  const convergenceConfidence = Math.min(1, (Math.abs(finalScore) / 100) * alignmentMultiplier);
  const asymmetryScore = parseFloat(((riskRewardRatio - 1) * convergenceConfidence).toFixed(2));

  return {
    ticker,
    timestamp,
    overallScore: Math.round(finalScore),
    direction,
    schools,
    stopLoss,
    primaryTarget,
    secondaryTarget,
    riskRewardRatio,
    asymmetryScore,
  };
}

function median(arr: number[]): number {
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

// ── Helpers de apresentação ───────────────────────────────────────────────────

export function scoreLabel(score: number): string {
  if (score >= 60) return 'Forte Alta';
  if (score >= 30) return 'Alta Moderada';
  if (score >= -29) return 'Neutro';
  if (score >= -59) return 'Baixa Moderada';
  return 'Forte Baixa';
}

export function scoreColor(score: number): string {
  if (score >= 60) return '#16A34A';  // green-600
  if (score >= 30) return '#65A30D';  // lime-600
  if (score >= -29) return '#CA8A04'; // yellow-600
  if (score >= -59) return '#EA580C'; // orange-600
  return '#DC2626';                   // red-600
}

export function schoolLabel(school: string): string {
  switch (school) {
    case 'indicators': return 'Indicadores';
    case 'candlestick': return 'Candlestick';
    case 'priceAction': return 'Price Action';
    default: return school;
  }
}
