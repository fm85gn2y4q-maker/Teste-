import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Path, Circle, Text as SvgText, G } from 'react-native-svg';
import { scoreColor, scoreLabel } from '../analysis/convergence';

interface Props {
  score: number; // -100 to +100
  size?: number;
}

export function ConvergenceGauge({ score, size = 180 }: Props) {
  const cx = size / 2;
  const cy = size / 2 + 10;
  const r = size * 0.38;
  const strokeWidth = size * 0.09;

  // O gauge vai de -100 (180°) a +100 (0°) — arco de 180°
  const startAngle = Math.PI; // esquerda
  const endAngle = 0;         // direita

  // Normaliza score de [-100, +100] para [0, 1]
  const normalized = (score + 100) / 200;
  const needleAngle = Math.PI - normalized * Math.PI; // PI → 0

  // Faixas de cor: vermelho | laranja | amarelo | verde-claro | verde
  const bands = [
    { from: 0.0, to: 0.2, color: '#DC2626' },
    { from: 0.2, to: 0.4, color: '#EA580C' },
    { from: 0.4, to: 0.6, color: '#CA8A04' },
    { from: 0.6, to: 0.8, color: '#65A30D' },
    { from: 0.8, to: 1.0, color: '#16A34A' },
  ];

  function arcPath(fromPct: number, toPct: number): string {
    const a1 = Math.PI - fromPct * Math.PI;
    const a2 = Math.PI - toPct * Math.PI;
    const x1 = cx + r * Math.cos(a1);
    const y1 = cy - r * Math.sin(a1);
    const x2 = cx + r * Math.cos(a2);
    const y2 = cy - r * Math.sin(a2);
    return `M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`;
  }

  const needleX = cx + (r - strokeWidth / 2) * 0.85 * Math.cos(needleAngle);
  const needleY = cy - (r - strokeWidth / 2) * 0.85 * Math.sin(needleAngle);

  const color = scoreColor(score);
  const label = scoreLabel(score);

  return (
    <View style={[styles.container, { width: size, height: size * 0.72 }]}>
      <Svg width={size} height={size * 0.72}>
        {/* Track (fundo cinza) */}
        <Path
          d={arcPath(0, 1)}
          stroke="#E5E7EB"
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
        />
        {/* Faixas coloridas */}
        {bands.map((b, i) => (
          <Path
            key={i}
            d={arcPath(b.from, b.to)}
            stroke={b.color}
            strokeWidth={strokeWidth}
            fill="none"
            opacity={0.3}
          />
        ))}
        {/* Progresso colorido até a posição atual */}
        <Path
          d={arcPath(0, normalized)}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
        />
        {/* Agulha */}
        <Path
          d={`M ${cx} ${cy} L ${needleX} ${needleY}`}
          stroke="#1F2937"
          strokeWidth={3}
          strokeLinecap="round"
        />
        <Circle cx={cx} cy={cy} r={6} fill="#1F2937" />
        {/* Rótulos extremos */}
        <SvgText x={cx - r - strokeWidth / 2 - 2} y={cy + 14} fontSize={10} fill="#9CA3AF" textAnchor="middle">-100</SvgText>
        <SvgText x={cx + r + strokeWidth / 2 + 2} y={cy + 14} fontSize={10} fill="#9CA3AF" textAnchor="middle">+100</SvgText>
      </Svg>
      {/* Score e label */}
      <View style={[styles.scoreBox, { marginTop: -size * 0.08 }]}>
        <Text style={[styles.scoreNum, { color }]}>{score > 0 ? '+' : ''}{score}</Text>
        <Text style={[styles.scoreLabel, { color }]}>{label}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center' },
  scoreBox: { alignItems: 'center' },
  scoreNum: { fontSize: 28, fontWeight: '800', letterSpacing: -1 },
  scoreLabel: { fontSize: 13, fontWeight: '600', marginTop: 2 },
});
