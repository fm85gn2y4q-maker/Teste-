import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { useStore } from '../store/useStore';
import { CandleChart } from '../components/CandleChart';
import { ConvergenceGauge } from '../components/ConvergenceGauge';
import { SchoolBars } from '../components/SchoolBars';
import { SignalList } from '../components/SignalList';
import { RiskRewardCard } from '../components/RiskRewardCard';
import { RootStackParamList } from '../types/navigation';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Detail'>;
  route: RouteProp<RootStackParamList, 'Detail'>;
};

const PURPLE = '#6C3DE8';
type TF = '1d' | '1wk';

export function DetailScreen({ navigation, route }: Props) {
  const { ticker } = route.params;
  const { watchlist, marketDataMap, loadingTickers, refreshTicker } = useStore();

  const asset = watchlist.find((a) => a.ticker === ticker);
  const marketData = marketDataMap[ticker];
  const isLoading = loadingTickers.has(ticker);
  const [timeframe, setTimeframe] = useState<TF>('1d');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!marketData) refreshTicker(ticker);
  }, [ticker]);

  const onRefresh = async () => {
    setRefreshing(true);
    await refreshTicker(ticker);
    setRefreshing(false);
  };

  const convergence = asset?.convergence;
  const candles = marketData?.candles ?? [];
  const changePositive = (asset?.change ?? 0) >= 0;

  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backText}>‹ Voltar</Text>
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTicker}>{ticker}</Text>
          {asset && asset.currentPrice > 0 && (
            <Text style={styles.headerPrice}>
              R$ {asset.currentPrice.toFixed(2)}{' '}
              <Text style={{ color: changePositive ? '#86EFAC' : '#FCA5A5' }}>
                {changePositive ? '+' : ''}{asset.change.toFixed(2)}%
              </Text>
            </Text>
          )}
        </View>
        <View style={styles.tfRow}>
          {(['1d', '1wk'] as TF[]).map((tf) => (
            <TouchableOpacity
              key={tf}
              style={[styles.tfBtn, timeframe === tf && styles.tfBtnActive]}
              onPress={() => setTimeframe(tf)}
            >
              <Text style={[styles.tfText, timeframe === tf && styles.tfTextActive]}>
                {tf === '1d' ? 'D' : 'W'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {isLoading && !marketData ? (
        <View style={styles.loadingBox}>
          <ActivityIndicator size="large" color={PURPLE} />
          <Text style={styles.loadingText}>Analisando {ticker}…</Text>
        </View>
      ) : (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={PURPLE} />
          }
        >
          {/* Gráfico de candlestick */}
          {candles.length > 0 && (
            <View style={styles.chartWrap}>
              <CandleChart candles={candles} visibleCount={timeframe === '1d' ? 60 : 52} />
            </View>
          )}

          {/* Gauge de convergência */}
          {convergence ? (
            <>
              <View style={styles.gaugeWrap}>
                <Text style={styles.sectionTitle}>Score de Convergência</Text>
                <View style={styles.gaugeCentered}>
                  <ConvergenceGauge score={convergence.overallScore} size={200} />
                </View>
                <Text style={styles.gaugeCaption}>
                  {convergence.schools.filter((s) => s.direction === convergence.direction).length} de{' '}
                  {convergence.schools.length} escolas alinhadas
                </Text>
              </View>

              <SchoolBars schools={convergence.schools} />
              <RiskRewardCard data={convergence} />
              <SignalList schools={convergence.schools} />
            </>
          ) : (
            <View style={styles.noConvBox}>
              <Text style={styles.noConvText}>
                Dados insuficientes para análise de convergência.{'\n'}
                São necessários pelo menos 30 candles.
              </Text>
            </View>
          )}

          {/* Nome completo do ativo */}
          {asset?.name && asset.name !== ticker && (
            <Text style={styles.assetName}>{asset.name}</Text>
          )}

          <Text style={styles.bottomDisc}>
            Dados fornecidos pela Brapi. Análise técnica automatizada para fins educacionais. Não constitui recomendação de investimento.
          </Text>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#F9FAFB' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: PURPLE,
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 8,
  },
  backBtn: { paddingVertical: 4, paddingRight: 8 },
  backText: { color: '#fff', fontSize: 16 },
  headerCenter: { flex: 1 },
  headerTicker: { fontSize: 18, fontWeight: '800', color: '#fff' },
  headerPrice: { fontSize: 12, color: 'rgba(255,255,255,0.85)', marginTop: 2 },
  tfRow: { flexDirection: 'row', gap: 4 },
  tfBtn: {
    width: 32, height: 28,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.15)',
  },
  tfBtnActive: { backgroundColor: '#fff' },
  tfText: { fontSize: 12, fontWeight: '700', color: 'rgba(255,255,255,0.7)' },
  tfTextActive: { color: PURPLE },

  scroll: { flex: 1 },
  scrollContent: { padding: 16, paddingBottom: 40 },

  chartWrap: { marginBottom: 12 },

  gaugeWrap: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    alignItems: 'center',
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    alignSelf: 'flex-start',
  },
  gaugeCentered: { alignItems: 'center', width: '100%' },
  gaugeCaption: { fontSize: 12, color: '#6B7280', marginTop: 4 },

  loadingBox: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  loadingText: { color: '#6B7280', marginTop: 12, fontSize: 14 },

  noConvBox: { alignItems: 'center', padding: 24 },
  noConvText: { color: '#9CA3AF', textAlign: 'center', lineHeight: 22, fontSize: 14 },

  assetName: { fontSize: 12, color: '#9CA3AF', textAlign: 'center', marginBottom: 8 },
  bottomDisc: { fontSize: 10, color: '#D1D5DB', textAlign: 'center', lineHeight: 16 },
});
