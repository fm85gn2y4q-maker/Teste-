import React, { useMemo } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import { getProduct } from '../data/catalog';
import { getRegion, marketsInRegion } from '../data/markets';
import { compareRegion } from '../engine/planner';
import { useStore } from '../store/useStore';
import { COLORS } from '../theme';
import { MarketQuote, PlanStop } from '../types';
import { RootStackParamList } from '../types/navigation';
import { formatBRL } from '../utils/format';

type Props = NativeStackScreenProps<RootStackParamList, 'Results'>;

function QuoteRow({ quote, rank, isBest }: { quote: MarketQuote; rank: number; isBest: boolean }) {
  const incomplete = quote.missing.length > 0;
  return (
    <View style={[styles.quoteRow, isBest && styles.quoteRowBest]}>
      <Text style={[styles.quoteRank, isBest && { color: COLORS.primaryDark }]}>{rank}º</Text>
      <View style={{ flex: 1 }}>
        <Text style={styles.quoteName}>{quote.market.name}</Text>
        <Text style={styles.quoteMeta}>
          {quote.market.address}
          {incomplete ? ` · faltam ${quote.missing.length} item(ns)` : ' · lista completa'}
        </Text>
        {quote.totalSavedInPromos > 0.009 && (
          <Text style={styles.quotePromo}>
            {formatBRL(quote.totalSavedInPromos)} economizados em promoções
          </Text>
        )}
      </View>
      <Text style={[styles.quoteTotal, isBest && { color: COLORS.primaryDark }]}>
        {formatBRL(quote.availableTotal)}
      </Text>
    </View>
  );
}

function StopCard({ stop, index }: { stop: PlanStop; index: number }) {
  return (
    <View style={styles.stopCard}>
      <View style={styles.stopHeader}>
        <View style={styles.stopBadge}>
          <Text style={styles.stopBadgeText}>{index + 1}</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.stopName}>{stop.market.name}</Text>
          <Text style={styles.stopAddress}>{stop.market.address}</Text>
        </View>
        <Text style={styles.stopSubtotal}>{formatBRL(stop.subtotal)}</Text>
      </View>
      {stop.lines.map((line) => (
        <View key={line.productId} style={styles.lineRow}>
          <Text style={styles.lineQty}>{line.quantity}×</Text>
          <Text style={styles.lineName} numberOfLines={1}>
            {getProduct(line.productId).name}
          </Text>
          {line.discountPct > 0 && (
            <View style={styles.discountTag}>
              <Text style={styles.discountTagText}>-{line.discountPct}%</Text>
            </View>
          )}
          <Text style={styles.linePrice}>{formatBRL(line.lineTotal)}</Text>
        </View>
      ))}
    </View>
  );
}

export function ResultsScreen({ navigation }: Props) {
  const { regionId, items, maxStops, extraStopCost } = useStore();

  const result = useMemo(
    () => compareRegion(marketsInRegion(regionId), items, { maxStops, extraStopCost }),
    [regionId, items, maxStops, extraStopCost],
  );

  const region = getRegion(regionId);
  const { quotes, bestSingle, worstComplete, plan } = result;

  const savingsVsWorst =
    bestSingle && worstComplete && worstComplete.market.id !== bestSingle.market.id
      ? worstComplete.availableTotal - bestSingle.availableTotal
      : null;

  const planWorthIt = plan !== null && plan.stops.length > 1 && plan.savingsVsBestSingle > 0.009;

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} hitSlop={12}>
          <Text style={styles.back}>‹ Voltar</Text>
        </Pressable>
        <Text style={styles.title}>Plano de compra · {region.name}</Text>
        <Text style={styles.subtitle}>
          {items.length} itens comparados em {quotes.length} mercados
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {bestSingle && (
          <View style={styles.heroCard}>
            <Text style={styles.heroLabel}>🏆 Melhor mercado único</Text>
            <Text style={styles.heroMarket}>{bestSingle.market.name}</Text>
            <Text style={styles.heroAddress}>{bestSingle.market.address}</Text>
            <Text style={styles.heroTotal}>{formatBRL(bestSingle.availableTotal)}</Text>
            {bestSingle.missing.length > 0 && (
              <Text style={styles.heroWarning}>
                ⚠️ Não tem: {bestSingle.missing.map((id) => getProduct(id).name).join(', ')}
              </Text>
            )}
            {savingsVsWorst !== null && savingsVsWorst > 0.009 && (
              <View style={styles.savingsPill}>
                <Text style={styles.savingsPillText}>
                  Você economiza {formatBRL(savingsVsWorst)} vs. {worstComplete!.market.name}
                </Text>
              </View>
            )}
          </View>
        )}

        {plan && (
          <View style={styles.planCard}>
            <Text style={styles.planTitle}>
              {planWorthIt ? '🧠 Plano inteligente: divida a compra' : '🧠 Plano inteligente'}
            </Text>
            {planWorthIt ? (
              <>
                <Text style={styles.planSummary}>
                  Comprando em {plan.stops.length} mercados você paga{' '}
                  <Text style={styles.planStrong}>{formatBRL(plan.effectiveTotal)}</Text> (já
                  contando {formatBRL(plan.stopCost)} de deslocamento) e economiza{' '}
                  <Text style={styles.planStrong}>{formatBRL(plan.savingsVsBestSingle)}</Text> em
                  relação ao melhor mercado único.
                </Text>
                {plan.stops.map((stop, i) => (
                  <StopCard key={stop.market.id} stop={stop} index={i} />
                ))}
              </>
            ) : (
              <Text style={styles.planSummary}>
                Para esta lista, dividir a compra entre mercados não compensa o deslocamento —
                comprar tudo no <Text style={styles.planStrong}>{bestSingle?.market.name}</Text> é o
                plano mais econômico.
              </Text>
            )}
            {plan.missing.length > 0 && (
              <Text style={styles.planMissing}>
                Nenhum mercado da região tem:{' '}
                {plan.missing.map((id) => getProduct(id).name).join(', ')}
              </Text>
            )}
          </View>
        )}

        <Text style={styles.sectionLabel}>Comparação completa</Text>
        {quotes.map((quote, i) => (
          <QuoteRow
            key={quote.market.id}
            quote={quote}
            rank={i + 1}
            isBest={bestSingle?.market.id === quote.market.id}
          />
        ))}

        <Text style={styles.disclaimer}>
          Preços simulados para demonstração. Ajuste o custo de deslocamento e o número máximo de
          mercados na aba Config.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.bg },
  header: {
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 16,
    backgroundColor: COLORS.primary,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
  },
  back: { color: '#DCFCE7', fontSize: 15, fontWeight: '600', marginBottom: 6 },
  title: { fontSize: 21, fontWeight: '800', color: '#fff' },
  subtitle: { fontSize: 13, color: '#DCFCE7', marginTop: 2 },
  content: { padding: 20, paddingBottom: 40 },
  heroCard: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 18,
    borderWidth: 2,
    borderColor: COLORS.primary,
  },
  heroLabel: { fontSize: 13, fontWeight: '700', color: COLORS.primaryDark },
  heroMarket: { fontSize: 22, fontWeight: '800', color: COLORS.text, marginTop: 6 },
  heroAddress: { fontSize: 13, color: COLORS.textMuted, marginTop: 2 },
  heroTotal: { fontSize: 30, fontWeight: '800', color: COLORS.primaryDark, marginTop: 10 },
  heroWarning: { fontSize: 13, color: COLORS.accent, marginTop: 8, lineHeight: 18 },
  savingsPill: {
    backgroundColor: COLORS.primarySoft,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
    alignSelf: 'flex-start',
    marginTop: 10,
  },
  savingsPillText: { color: COLORS.primaryDark, fontWeight: '700', fontSize: 13 },
  planCard: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: COLORS.border,
    marginTop: 14,
  },
  planTitle: { fontSize: 16, fontWeight: '800', color: COLORS.text, marginBottom: 8 },
  planSummary: { fontSize: 14, color: COLORS.text, lineHeight: 21 },
  planStrong: { fontWeight: '800', color: COLORS.primaryDark },
  planMissing: { fontSize: 13, color: COLORS.accent, marginTop: 10, lineHeight: 18 },
  stopCard: {
    backgroundColor: COLORS.bg,
    borderRadius: 12,
    padding: 12,
    marginTop: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  stopHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  stopBadge: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  stopBadgeText: { color: '#fff', fontWeight: '800', fontSize: 13 },
  stopName: { fontSize: 15, fontWeight: '700', color: COLORS.text },
  stopAddress: { fontSize: 12, color: COLORS.textMuted },
  stopSubtotal: { fontSize: 15, fontWeight: '800', color: COLORS.text },
  lineRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 4 },
  lineQty: { width: 32, fontSize: 13, fontWeight: '700', color: COLORS.textMuted },
  lineName: { flex: 1, fontSize: 13, color: COLORS.text, marginRight: 6 },
  discountTag: {
    backgroundColor: '#FEF3C7',
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    marginRight: 6,
  },
  discountTagText: { color: '#B45309', fontSize: 11, fontWeight: '800' },
  linePrice: { fontSize: 13, fontWeight: '700', color: COLORS.text },
  sectionLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: COLORS.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: 20,
    marginBottom: 10,
  },
  quoteRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 14,
    marginBottom: 8,
  },
  quoteRowBest: { borderColor: COLORS.primary, backgroundColor: '#F0FDF4' },
  quoteRank: { width: 34, fontSize: 15, fontWeight: '800', color: COLORS.textMuted },
  quoteName: { fontSize: 15, fontWeight: '700', color: COLORS.text },
  quoteMeta: { fontSize: 12, color: COLORS.textMuted, marginTop: 2 },
  quotePromo: { fontSize: 12, color: COLORS.primaryDark, marginTop: 2, fontWeight: '600' },
  quoteTotal: { fontSize: 16, fontWeight: '800', color: COLORS.text, marginLeft: 8 },
  disclaimer: {
    fontSize: 12,
    color: COLORS.textMuted,
    marginTop: 16,
    lineHeight: 17,
    textAlign: 'center',
  },
});
