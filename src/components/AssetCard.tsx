import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { WatchlistAsset } from '../analysis/types';
import { scoreColor, scoreLabel } from '../analysis/convergence';

interface Props {
  asset: WatchlistAsset;
  loading?: boolean;
  onPress: () => void;
  onLongPress?: () => void;
}

export function AssetCard({ asset, loading, onPress, onLongPress }: Props) {
  const convergence = asset.convergence;
  const hasData = asset.currentPrice > 0;
  const changePositive = asset.change >= 0;

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={onPress}
      onLongPress={onLongPress}
      activeOpacity={0.75}
    >
      {/* Esquerda: ticker + nome */}
      <View style={styles.left}>
        <Text style={styles.ticker}>{asset.ticker}</Text>
        <Text style={styles.name} numberOfLines={1}>{asset.name}</Text>
      </View>

      {/* Centro: preço + variação */}
      <View style={styles.center}>
        {hasData ? (
          <>
            <Text style={styles.price}>R$ {asset.currentPrice.toFixed(2)}</Text>
            <View style={[styles.changePill, changePositive ? styles.pillGreen : styles.pillRed]}>
              <Text style={[styles.changeText, changePositive ? styles.textGreen : styles.textRed]}>
                {changePositive ? '+' : ''}{asset.change.toFixed(2)}%
              </Text>
            </View>
          </>
        ) : loading ? (
          <ActivityIndicator size="small" color="#6C3DE8" />
        ) : (
          <Text style={styles.noData}>—</Text>
        )}
      </View>

      {/* Direita: score de convergência */}
      <View style={styles.right}>
        {convergence ? (
          <>
            <View style={[styles.scoreBadge, { backgroundColor: scoreColor(convergence.overallScore) + '22' }]}>
              <Text style={[styles.scoreNum, { color: scoreColor(convergence.overallScore) }]}>
                {convergence.overallScore > 0 ? '+' : ''}{convergence.overallScore}
              </Text>
            </View>
            <Text style={[styles.scoreLabel, { color: scoreColor(convergence.overallScore) }]} numberOfLines={1}>
              {scoreLabel(convergence.overallScore)}
            </Text>
          </>
        ) : (
          <Text style={styles.noData}>—</Text>
        )}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  left: { flex: 2 },
  ticker: { fontSize: 15, fontWeight: '700', color: '#111827' },
  name: { fontSize: 11, color: '#6B7280', marginTop: 2 },
  center: { flex: 2, alignItems: 'flex-end' },
  price: { fontSize: 14, fontWeight: '600', color: '#111827' },
  changePill: { borderRadius: 20, paddingHorizontal: 6, paddingVertical: 2, marginTop: 3 },
  pillGreen: { backgroundColor: '#DCFCE7' },
  pillRed: { backgroundColor: '#FEE2E2' },
  changeText: { fontSize: 11, fontWeight: '600' },
  textGreen: { color: '#16A34A' },
  textRed: { color: '#DC2626' },
  right: { flex: 2, alignItems: 'flex-end' },
  scoreBadge: { borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3 },
  scoreNum: { fontSize: 14, fontWeight: '800' },
  scoreLabel: { fontSize: 10, fontWeight: '600', marginTop: 2, textAlign: 'right' },
  noData: { color: '#D1D5DB', fontSize: 18 },
});
