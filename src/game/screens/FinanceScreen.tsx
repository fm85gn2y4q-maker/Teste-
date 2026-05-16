// ============================================================
// FinanceScreen — Club Finances
// ============================================================
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types/navigation';
import { useGameStore, selectUserClub, selectUserPlayers } from '../store';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Finance'>;
};

const fmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
const fmtM = (v: number) => `R$ ${(v / 1_000_000).toFixed(2)}M`;

function BarChart({
  income,
  expenditure,
}: {
  income: number;
  expenditure: number;
}) {
  const max = Math.max(income, expenditure, 1);
  const incPct = (income / max) * 100;
  const expPct = (expenditure / max) * 100;
  return (
    <View style={barStyles.container}>
      <View style={barStyles.row}>
        <Text style={barStyles.label}>Receitas</Text>
        <View style={barStyles.track}>
          <View style={[barStyles.fill, barStyles.fillGreen, { width: `${incPct}%` }]} />
        </View>
        <Text style={[barStyles.value, { color: '#00ff88' }]}>{fmtM(income)}</Text>
      </View>
      <View style={barStyles.row}>
        <Text style={barStyles.label}>Despesas</Text>
        <View style={barStyles.track}>
          <View style={[barStyles.fill, barStyles.fillRed, { width: `${expPct}%` }]} />
        </View>
        <Text style={[barStyles.value, { color: '#ff4444' }]}>{fmtM(expenditure)}</Text>
      </View>
    </View>
  );
}

const barStyles = StyleSheet.create({
  container: { gap: 10 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  label: { color: '#888', fontSize: 11, width: 64 },
  track: { flex: 1, height: 16, backgroundColor: '#2a2a3e', borderRadius: 4, overflow: 'hidden' },
  fill: { height: 16, borderRadius: 4 },
  fillGreen: { backgroundColor: '#00ff88' },
  fillRed: { backgroundColor: '#ff4444' },
  value: { fontSize: 10, fontVariant: ['tabular-nums'], width: 68, textAlign: 'right' },
});

export default function FinanceScreen({ navigation }: Props) {
  const userClub = useGameStore(selectUserClub);
  const players = useGameStore(selectUserPlayers);
  const news = useGameStore((s) => s.news);

  if (!userClub) return null;

  const fin = userClub.finances;
  const totalIncome = fin.transferIncome + fin.matchRevenue + fin.sponsorshipIncome;
  const totalExpenditure = fin.transferExpenditure + fin.weeklyWages * 4; // approx monthly

  const transferNews = news.filter((n) => n.category === 'Transfer').slice(0, 10);

  const topEarners = [...players]
    .sort((a, b) => b.wage - a.wage)
    .slice(0, 5);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backBtnText}>← Voltar</Text>
        </TouchableOpacity>
        <Text style={styles.screenTitle}>FINANÇAS DO CLUBE</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Summary cards */}
        <View style={styles.summaryGrid}>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>SALDO</Text>
            <Text style={[styles.summaryValue, { color: userClub.budget >= 0 ? '#00ff88' : '#ff4444' }]}>
              {fmt.format(userClub.budget)}
            </Text>
          </View>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>SALÁRIOS/SEM</Text>
            <Text style={[styles.summaryValue, { color: '#ff6600' }]}>
              {fmt.format(fin.weeklyWages)}
            </Text>
          </View>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>ORÇ. TRANSFERÊNCIAS</Text>
            <Text style={[styles.summaryValue, { color: '#00ff88' }]}>
              {fmt.format(userClub.budget)}
            </Text>
          </View>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>PATROCÍNIO</Text>
            <Text style={styles.summaryValue}>
              {fmt.format(fin.sponsorshipIncome)}
            </Text>
          </View>
        </View>

        {/* Income vs Expenditure chart */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>RECEITAS VS DESPESAS</Text>
          <BarChart income={totalIncome} expenditure={totalExpenditure} />
          <View style={styles.breakdown}>
            <View style={styles.breakdownRow}>
              <Text style={styles.breakLabel}>Renda de jogos</Text>
              <Text style={[styles.breakValue, { color: '#00ff88' }]}>{fmt.format(fin.matchRevenue)}</Text>
            </View>
            <View style={styles.breakdownRow}>
              <Text style={styles.breakLabel}>Patrocínio</Text>
              <Text style={[styles.breakValue, { color: '#00ff88' }]}>{fmt.format(fin.sponsorshipIncome)}</Text>
            </View>
            <View style={styles.breakdownRow}>
              <Text style={styles.breakLabel}>Venda de jogadores</Text>
              <Text style={[styles.breakValue, { color: '#00ff88' }]}>{fmt.format(fin.transferIncome)}</Text>
            </View>
            <View style={[styles.breakdownRow, styles.separator]}>
              <Text style={styles.breakLabel}>Folha salarial (aprox/mês)</Text>
              <Text style={[styles.breakValue, { color: '#ff4444' }]}>{fmt.format(fin.weeklyWages * 4)}</Text>
            </View>
            <View style={styles.breakdownRow}>
              <Text style={styles.breakLabel}>Compra de jogadores</Text>
              <Text style={[styles.breakValue, { color: '#ff4444' }]}>{fmt.format(fin.transferExpenditure)}</Text>
            </View>
          </View>
        </View>

        {/* Top 5 earners */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>MAIORES SALÁRIOS</Text>
          {topEarners.map((p, idx) => (
            <View key={p.id} style={styles.earnerRow}>
              <Text style={styles.earnerRank}>{idx + 1}.</Text>
              <Text style={styles.earnerName} numberOfLines={1}>{p.name}</Text>
              <Text style={styles.earnerPos}>{p.position}</Text>
              <Text style={styles.earnerWage}>{fmt.format(p.wage)}/sem</Text>
            </View>
          ))}
        </View>

        {/* Transfer history */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>HISTÓRICO DE TRANSFERÊNCIAS</Text>
          {transferNews.length === 0 ? (
            <Text style={styles.emptyText}>Nenhuma transferência registrada.</Text>
          ) : (
            transferNews.map((item) => (
              <View key={item.id} style={styles.newsItem}>
                <Text style={styles.newsDate}>{item.date}</Text>
                <Text style={styles.newsHead}>{item.headline}</Text>
                <Text style={styles.newsBody}>{item.body}</Text>
              </View>
            ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0a0a0f' },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingTop: 12,
    paddingBottom: 8,
    gap: 12,
  },
  backBtn: { paddingVertical: 4 },
  backBtnText: { color: '#00ff88', fontSize: 14, fontWeight: '600' },
  screenTitle: { color: '#00ff88', fontSize: 14, fontWeight: '900', letterSpacing: 1.5 },
  scroll: { padding: 12, paddingBottom: 32 },
  summaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 10,
  },
  summaryCard: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 14,
    borderWidth: 1,
    borderColor: '#2a2a3e',
    width: '47%',
  },
  summaryLabel: { color: '#555', fontSize: 8, fontWeight: '700', letterSpacing: 1, marginBottom: 6 },
  summaryValue: { color: '#fff', fontSize: 14, fontWeight: '900', fontVariant: ['tabular-nums'] },
  card: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  cardLabel: { color: '#666', fontSize: 9, fontWeight: '700', letterSpacing: 1.5, marginBottom: 12 },
  breakdown: { marginTop: 12, gap: 6 },
  breakdownRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  separator: { borderTopWidth: 1, borderTopColor: '#2a2a3e', paddingTop: 6, marginTop: 6 },
  breakLabel: { color: '#888', fontSize: 11 },
  breakValue: { fontSize: 11, fontVariant: ['tabular-nums'], fontWeight: '600' },
  earnerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a3e',
    gap: 8,
  },
  earnerRank: { color: '#555', fontSize: 12, width: 18 },
  earnerName: { color: '#ddd', fontSize: 13, flex: 1, fontWeight: '500' },
  earnerPos: { color: '#666', fontSize: 10, width: 32 },
  earnerWage: { color: '#ffaa00', fontSize: 11, fontVariant: ['tabular-nums'] },
  newsItem: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a3e',
  },
  newsDate: { color: '#555', fontSize: 9 },
  newsHead: { color: '#ddd', fontSize: 12, fontWeight: '600', marginTop: 2 },
  newsBody: { color: '#777', fontSize: 11, marginTop: 2, lineHeight: 16 },
  emptyText: { color: '#555', fontSize: 12, textAlign: 'center', paddingVertical: 12 },
});
