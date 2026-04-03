import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { SignalResult } from '../analysis/types';
import { scoreColor, schoolLabel } from '../analysis/convergence';

interface Props {
  schools: SignalResult[];
}

export function SchoolBars({ schools }: Props) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Escolas de Análise</Text>
      {schools.map((s) => {
        const color = scoreColor(s.score);
        const pct = (s.score + 100) / 2; // 0 – 100%
        const bullPct = Math.max(0, pct - 50);
        const bearPct = Math.max(0, 50 - pct);
        return (
          <View key={s.school} style={styles.row}>
            <Text style={styles.schoolName}>{schoolLabel(s.school)}</Text>
            <View style={styles.barWrap}>
              {/* Metade esquerda (baixista) */}
              <View style={styles.leftHalf}>
                <View style={[styles.bearBar, { width: `${bearPct * 2}%`, backgroundColor: '#DC2626' }]} />
              </View>
              {/* Centro */}
              <View style={styles.centerLine} />
              {/* Metade direita (altista) */}
              <View style={styles.rightHalf}>
                <View style={[styles.bullBar, { width: `${bullPct * 2}%`, backgroundColor: '#16A34A' }]} />
              </View>
            </View>
            <Text style={[styles.scoreText, { color }]}>
              {s.score > 0 ? '+' : ''}{s.score}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 14,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  schoolName: {
    width: 90,
    fontSize: 13,
    color: '#4B5563',
    fontWeight: '500',
  },
  barWrap: {
    flex: 1,
    flexDirection: 'row',
    height: 10,
    borderRadius: 5,
    overflow: 'hidden',
    backgroundColor: '#F3F4F6',
    marginHorizontal: 8,
  },
  leftHalf: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  rightHalf: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  bearBar: {
    height: 10,
    borderRadius: 5,
  },
  bullBar: {
    height: 10,
    borderRadius: 5,
  },
  centerLine: {
    width: 2,
    height: 10,
    backgroundColor: '#D1D5DB',
  },
  scoreText: {
    width: 36,
    fontSize: 13,
    fontWeight: '700',
    textAlign: 'right',
  },
});
