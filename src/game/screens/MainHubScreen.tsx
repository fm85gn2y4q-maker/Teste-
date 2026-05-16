// ============================================================
// MainHubScreen — Main Dashboard
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
import { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { CompositeNavigationProp } from '@react-navigation/native';
import { RootStackParamList, MainTabParamList } from '../../types/navigation';
import {
  useGameStore,
  selectUserClub,
  selectUpcomingFixtures,
  selectRecentResults,
  selectSortedLeagueTable,
} from '../store';

type Props = {
  navigation: CompositeNavigationProp<
    BottomTabNavigationProp<MainTabParamList, 'Hub'>,
    NativeStackNavigationProp<RootStackParamList>
  >;
};

const fmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });

function fmtDate(d: string): string {
  const [y, m, day] = d.split('-');
  return `${day}/${m}/${y}`;
}

function ordinal(n: number): string {
  return `${n}º`;
}

export default function MainHubScreen({ navigation }: Props) {
  const state = useGameStore((s) => s);
  const userClub = useGameStore(selectUserClub);
  const upcoming = useGameStore((s) => selectUpcomingFixtures(s, 3));
  const recent = useGameStore((s) => selectRecentResults(s, 1));
  const table = useGameStore(selectSortedLeagueTable);
  const advanceDay = useGameStore((s) => s.advanceDay);
  const pendingPress = useGameStore((s) => s.pendingPressConference);
  const clubs = useGameStore((s) => s.clubs);
  const news = useGameStore((s) => s.news);

  if (!userClub) return null;

  const userPos = table.findIndex((r) => r.clubId === userClub.id) + 1;
  const userRow = table.find((r) => r.clubId === userClub.id);
  const nextFixture = upcoming[0];
  const lastResult = recent[0];
  const squadSize = userClub.playerIds.length;
  const players = state.players;
  const wageBill = userClub.playerIds.reduce((sum, id) => sum + (players[id]?.wage ?? 0), 0);

  function getOpponent(fixture: typeof nextFixture) {
    if (!fixture) return null;
    const isHome = fixture.homeClubId === userClub!.id;
    const oppId = isHome ? fixture.awayClubId : fixture.homeClubId;
    return { club: clubs[oppId], isHome };
  }

  const nextOpp = nextFixture ? getOpponent(nextFixture) : null;

  function getLastResultText() {
    if (!lastResult) return '—';
    const isHome = lastResult.homeClubId === userClub!.id;
    const oppId = isHome ? lastResult.awayClubId : lastResult.homeClubId;
    const opp = clubs[oppId]?.shortName ?? '?';
    const myGoals = isHome ? lastResult.homeGoals : lastResult.awayGoals;
    const oppGoals = isHome ? lastResult.awayGoals : lastResult.homeGoals;
    const result = myGoals! > oppGoals! ? 'V' : myGoals! < oppGoals! ? 'D' : 'E';
    const color = result === 'V' ? '#00ff88' : result === 'D' ? '#ff4444' : '#ffaa00';
    return { text: `${result} ${myGoals}-${oppGoals} vs ${opp}`, color };
  }

  const lastResultData = getLastResultText();

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.clubTitle}>{userClub.name}</Text>
            <Text style={styles.dateText}>
              {fmtDate(state.currentDate)} · Semana {state.gameWeek} · {state.season}
            </Text>
          </View>
          {pendingPress && (
            <View style={styles.pressBadge}>
              <Text style={styles.pressBadgeText}>COLETIVA</Text>
            </View>
          )}
        </View>

        {/* Board Confidence */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>CONFIANÇA DA DIRETORIA</Text>
          <View style={styles.barBg}>
            <View style={[styles.barFill, { width: `${(userClub.boardConfidence / 10) * 100}%` }]} />
          </View>
          <Text style={styles.cardValue}>{userClub.boardConfidence}/10</Text>
        </View>

        {/* League Position */}
        <View style={[styles.card, styles.rowCard]}>
          <View style={styles.statBox}>
            <Text style={styles.cardLabel}>POSIÇÃO</Text>
            <Text style={styles.bigStat}>{ordinal(userPos)}</Text>
            <Text style={styles.smallStat}>{userRow?.points ?? 0} pts</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.cardLabel}>SALDO DE GOLS</Text>
            <Text style={styles.bigStat}>{(userRow?.goalsFor ?? 0) - (userRow?.goalsAgainst ?? 0)}</Text>
            <Text style={styles.smallStat}>{userRow?.goalsFor}GP · {userRow?.goalsAgainst}GC</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.cardLabel}>JOGOS</Text>
            <Text style={styles.bigStat}>{userRow?.played ?? 0}</Text>
            <Text style={styles.smallStat}>{userRow?.won}V {userRow?.drawn}E {userRow?.lost}D</Text>
          </View>
        </View>

        {/* Next Fixture */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>PRÓXIMO JOGO</Text>
          {nextFixture && nextOpp ? (
            <View>
              <Text style={styles.fixtureTeams}>
                {nextOpp.isHome ? `${userClub.shortName} x ${nextOpp.club?.shortName}` : `${nextOpp.club?.shortName} x ${userClub.shortName}`}
              </Text>
              <View style={styles.rowBetween}>
                <Text style={styles.smallGray}>{fmtDate(nextFixture.date)} · Rodada {nextFixture.round}</Text>
                <Text style={styles.locationBadge}>{nextOpp.isHome ? 'CASA' : 'FORA'}</Text>
              </View>
              <TouchableOpacity
                style={styles.matchBtn}
                onPress={() => navigation.navigate('MatchDay', { fixtureId: nextFixture.id })}
              >
                <Text style={styles.matchBtnText}>▶ JOGAR PARTIDA</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <Text style={styles.smallGray}>Nenhum jogo agendado</Text>
          )}
        </View>

        {/* Last Result */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>ÚLTIMO RESULTADO</Text>
          {typeof lastResultData === 'object' ? (
            <Text style={[styles.resultText, { color: lastResultData.color }]}>{lastResultData.text}</Text>
          ) : (
            <Text style={styles.smallGray}>{lastResultData}</Text>
          )}
        </View>

        {/* Quick Stats */}
        <View style={[styles.card, styles.rowCard]}>
          <View style={styles.statBox}>
            <Text style={styles.cardLabel}>ELENCO</Text>
            <Text style={styles.bigStat}>{squadSize}</Text>
            <Text style={styles.smallStat}>jogadores</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.cardLabel}>SALÁRIOS</Text>
            <Text style={styles.bigStatGreen}>{fmt.format(wageBill)}</Text>
            <Text style={styles.smallStat}>/semana</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.cardLabel}>ORÇAMENTO</Text>
            <Text style={styles.bigStatGreen}>{fmt.format(userClub.budget)}</Text>
            <Text style={styles.smallStat}>disponível</Text>
          </View>
        </View>

        {/* Quick Links */}
        <View style={styles.quickLinks}>
          <TouchableOpacity style={styles.quickBtn} onPress={() => navigation.navigate('Training')}>
            <Text style={styles.quickBtnText}>🏋️ TREINO</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.quickBtn} onPress={() => navigation.navigate('Finance')}>
            <Text style={styles.quickBtnText}>💰 FINANÇAS</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.quickBtn} onPress={() => navigation.navigate('Scouting')}>
            <Text style={styles.quickBtnText}>🔭 SCOUTING</Text>
          </TouchableOpacity>
          {pendingPress && (
            <TouchableOpacity style={[styles.quickBtn, styles.quickBtnAccent]} onPress={() => navigation.navigate('Press')}>
              <Text style={styles.quickBtnText}>🎤 COLETIVA</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* News Feed */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>ÚLTIMAS NOTÍCIAS</Text>
          {news.slice(0, 5).map((item) => (
            <View key={item.id} style={styles.newsItem}>
              <Text style={styles.newsDate}>{fmtDate(item.date)}</Text>
              <Text style={styles.newsHeadline}>{item.headline}</Text>
            </View>
          ))}
        </View>

        {/* Advance Day */}
        <TouchableOpacity
          style={[styles.advanceBtn, pendingPress && styles.advanceBtnDisabled]}
          onPress={() => { if (!pendingPress) advanceDay(); }}
          disabled={pendingPress}
          activeOpacity={0.8}
        >
          <Text style={styles.advanceBtnText}>
            {pendingPress ? '🎤 RESPONDA À COLETIVA PRIMEIRO' : '⏩ AVANÇAR DIA'}
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0a0a0f' },
  scroll: { padding: 12, paddingBottom: 32 },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  clubTitle: { color: '#00ff88', fontSize: 22, fontWeight: '900', letterSpacing: 1 },
  dateText: { color: '#888', fontSize: 11, marginTop: 2 },
  pressBadge: {
    backgroundColor: '#ff6600',
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  pressBadgeText: { color: '#fff', fontSize: 10, fontWeight: '900', letterSpacing: 1 },
  card: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  rowCard: { flexDirection: 'row', justifyContent: 'space-around' },
  cardLabel: { color: '#666', fontSize: 9, fontWeight: '700', letterSpacing: 1.5, marginBottom: 8 },
  cardValue: { color: '#aaa', fontSize: 12, marginTop: 4 },
  barBg: { height: 6, backgroundColor: '#2a2a3e', borderRadius: 3, overflow: 'hidden' },
  barFill: { height: 6, backgroundColor: '#00ff88', borderRadius: 3 },
  statBox: { alignItems: 'center', flex: 1 },
  bigStat: { color: '#fff', fontSize: 24, fontWeight: '900', fontVariant: ['tabular-nums'] },
  bigStatGreen: { color: '#00ff88', fontSize: 14, fontWeight: '700', fontVariant: ['tabular-nums'] },
  smallStat: { color: '#666', fontSize: 10, marginTop: 2 },
  fixtureTeams: { color: '#fff', fontSize: 18, fontWeight: '900', marginBottom: 6 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  smallGray: { color: '#666', fontSize: 11 },
  locationBadge: {
    backgroundColor: '#2a2a3e',
    color: '#00ff88',
    fontSize: 10,
    fontWeight: '700',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 3,
  },
  matchBtn: {
    marginTop: 10,
    backgroundColor: '#00ff88',
    borderRadius: 6,
    paddingVertical: 10,
    alignItems: 'center',
  },
  matchBtnText: { color: '#0a0a0f', fontSize: 13, fontWeight: '900', letterSpacing: 1 },
  resultText: { fontSize: 16, fontWeight: '700' },
  quickLinks: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 10 },
  quickBtn: {
    backgroundColor: '#1a1a2e',
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  quickBtnAccent: { borderColor: '#ff6600', backgroundColor: '#2a1a0e' },
  quickBtnText: { color: '#ccc', fontSize: 11, fontWeight: '700' },
  newsItem: {
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a3e',
  },
  newsDate: { color: '#555', fontSize: 10, fontVariant: ['tabular-nums'] },
  newsHeadline: { color: '#ddd', fontSize: 12, marginTop: 2, fontWeight: '500' },
  advanceBtn: {
    backgroundColor: '#00ff88',
    borderRadius: 8,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 6,
  },
  advanceBtnDisabled: { backgroundColor: '#333', opacity: 0.7 },
  advanceBtnText: { color: '#0a0a0f', fontSize: 15, fontWeight: '900', letterSpacing: 1 },
});
