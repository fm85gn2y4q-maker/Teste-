import React, { useMemo } from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import Svg, { Line, Rect, Path, Text as SvgText } from 'react-native-svg';
import { OHLCV } from '../analysis/types';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface Props {
  candles: OHLCV[];
  width?: number;
  height?: number;
  visibleCount?: number;
}

export function CandleChart({ candles, width = SCREEN_WIDTH - 32, height = 220, visibleCount = 60 }: Props) {
  const data = candles.slice(-visibleCount);

  const { minLow, maxHigh, priceRange } = useMemo(() => {
    if (data.length === 0) return { minLow: 0, maxHigh: 1, priceRange: 1 };
    const minLow = Math.min(...data.map((c) => c.low));
    const maxHigh = Math.max(...data.map((c) => c.high));
    const padding = (maxHigh - minLow) * 0.05;
    return {
      minLow: minLow - padding,
      maxHigh: maxHigh + padding,
      priceRange: maxHigh - minLow + 2 * padding,
    };
  }, [data]);

  const PAD_LEFT = 4;
  const PAD_RIGHT = 44;
  const PAD_TOP = 8;
  const PAD_BOTTOM = 20;
  const chartW = width - PAD_LEFT - PAD_RIGHT;
  const chartH = height - PAD_TOP - PAD_BOTTOM;
  const candleW = Math.max(1, (chartW / data.length) * 0.7);

  function toY(price: number): number {
    return PAD_TOP + chartH - ((price - minLow) / priceRange) * chartH;
  }

  const yLabels = useMemo(() => {
    const steps = 4;
    return Array.from({ length: steps + 1 }, (_, i) => {
      const price = minLow + (priceRange * i) / steps;
      return { price, y: toY(price) };
    });
  }, [minLow, priceRange, chartH]);

  if (data.length < 2) {
    return (
      <View style={[styles.container, { width, height }]}>
        <Text style={styles.emptyText}>Carregando gráfico…</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, { width, height }]}>
      <Svg width={width} height={height}>
        {/* Grid horizontal */}
        {yLabels.map((label, i) => (
          <React.Fragment key={i}>
            <Line
              x1={PAD_LEFT}
              y1={label.y}
              x2={PAD_LEFT + chartW}
              y2={label.y}
              stroke="#F3F4F6"
              strokeWidth={1}
            />
            <SvgText
              x={PAD_LEFT + chartW + 4}
              y={label.y + 4}
              fontSize={9}
              fill="#9CA3AF"
            >
              {label.price >= 1000
                ? (label.price / 1000).toFixed(1) + 'k'
                : label.price.toFixed(2)}
            </SvgText>
          </React.Fragment>
        ))}

        {/* Candles */}
        {data.map((c, i) => {
          const x = PAD_LEFT + (i / data.length) * chartW + ((chartW / data.length) - candleW) / 2;
          const isBull = c.close >= c.open;
          const color = isBull ? '#16A34A' : '#DC2626';

          const bodyTop = toY(Math.max(c.open, c.close));
          const bodyBottom = toY(Math.min(c.open, c.close));
          const bodyH = Math.max(1, bodyBottom - bodyTop);

          const wickX = x + candleW / 2;

          return (
            <React.Fragment key={i}>
              {/* Wick superior */}
              <Line
                x1={wickX} y1={toY(c.high)}
                x2={wickX} y2={bodyTop}
                stroke={color} strokeWidth={1}
              />
              {/* Corpo */}
              <Rect
                x={x} y={bodyTop}
                width={candleW} height={bodyH}
                fill={isBull ? color : color}
                opacity={isBull ? 0.9 : 0.85}
                rx={1}
              />
              {/* Wick inferior */}
              <Line
                x1={wickX} y1={bodyBottom}
                x2={wickX} y2={toY(c.low)}
                stroke={color} strokeWidth={1}
              />
            </React.Fragment>
          );
        })}

        {/* Último preço — linha horizontal */}
        {(() => {
          const lastClose = data[data.length - 1].close;
          const y = toY(lastClose);
          const isBull = data[data.length - 1].close >= data[data.length - 1].open;
          const color = isBull ? '#16A34A' : '#DC2626';
          return (
            <>
              <Line
                x1={PAD_LEFT} y1={y}
                x2={PAD_LEFT + chartW} y2={y}
                stroke={color} strokeWidth={1}
                strokeDasharray="3,3"
              />
              <Rect
                x={PAD_LEFT + chartW + 2} y={y - 7}
                width={40} height={14}
                fill={color} rx={3}
              />
              <SvgText
                x={PAD_LEFT + chartW + 22} y={y + 4}
                fontSize={9} fill="#fff"
                textAnchor="middle"
              >
                {lastClose.toFixed(2)}
              </SvgText>
            </>
          );
        })()}
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    borderRadius: 16,
    overflow: 'hidden',
    marginBottom: 12,
  },
  emptyText: {
    color: '#9CA3AF',
    textAlign: 'center',
    marginTop: 80,
    fontSize: 14,
  },
});
