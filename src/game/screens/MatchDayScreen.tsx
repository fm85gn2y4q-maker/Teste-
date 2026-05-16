// ============================================================
// MatchDayScreen — Match Simulation View
// ============================================================
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  ActivityIndicator,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../../types/navigation';
import { useGameStore } from '../store';
import { MatchEvent, Fixture } from '../types';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'MatchDay'>;
  route: RouteProp<RootStackParamList, 'MatchDay'>;
};

function fmtDate(d: string): string {
  const [y, m, day] = d.split('-');
  return `${day}/${m}/${y}`;
}

function eventIcon(type: MatchEvent['type']): string {
  switch (type) {
    case 'Goal': return '⚽';
    case 'YellowCard': return '🟨';
    case 'RedCard': return '🔴';
    case 'Injury': return '🏥';
    case 'Substitution': return '🔄';
    default: return '·';
  }
}

function eventLabel(type: MatchEvent['type']): string {
  switch (type) {
    case 'Goal': return 'Gol';
    case 'YellowCard': return 'Cartão Amarelo';
    case 'RedCard': return 'Expulsão';
    case 'Injury': return 'Lesão';
    case 'Substitution': return 'Substituição';
    default: return type;
  }
}

export default function MatchDayScreen({ navigation, route }: Props) {
  const { fixtureId } = route.params;
  const simulateMatch = useGameStore((s) => s.simulateMatch);
  const fixtures = useGameStore((s) => s.fixtures);
  const clubs = useGameStore((s) => s.clubs);
  const players = useGameStore((s) => s.players);
  const userClubId = useGameStore((s) => s.userClubId);

  const [simulating, setSimulating] = useState(false);
  const [done, setDone] = useState(false);

  const fixture = fixtures.find((f) => f.id === fixtureId);

  if (!fixture) {
    return (
      <SafeAreaView style={styles.safe}>
        <Text style={styles.errorText}>Partida não encontrada.</Text>
        <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
          <Text style={styles.backBtnText}>← Voltar</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  const homeClub = clubs[fixture.homeClubId];
  const awayClub = clubs[fixture.awayClubId];

  function handleSimulate() {
    setSimulating(true);
    setTimeout(() => {
      simulateMatch(fixtureId);
      setSimulating(false);
      setDone(true);
    }, 1500);
  }

  // Get updated fixture after simulation
  const updatedFixture = fixtures.find((f) => f.id === fixtureId) as Fixture;
  const events = updatedFixture?.events ?? [];

  const homeGoals = updatedFixture?.homeGoals ?? 0;
  const awayGoals = updatedFixture?.awayGoals ?? 0;

  const isUserHome = fixture.homeClubId === userClubId;
  const userWon = isUserHome ? homeGoals > awayGoals : awayGoals > homeGoals;
  const userDraw = homeGoals === awayGoals;

  const homeLineupIds = Object.values(homeClub?.tactics?.lineup ?? {}).slice(0, 11);
  const awayLineupIds = Object.values(awayClub?.tactics?.lineup ?? {}).slice(0, 11);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtnSmall}>
            <Text style={styles.backBtnSmallText}>← Voltar</Text>
          </TouchableOpacity>
          <Text style={styles.headerDate}>Rodada {fixture.round} · {fmtDate(fixture.date)}</Text>
        </View>

        {/* Scoreline */}
        <View style={styles.scoreCard}>
          <View style={styles.teamBlock}>
            <Text style={styles.teamName} numberOfLines={2}>{homeClub?.name ?? '?'}</Text>
            <Text style={styles.teamType}>CASA</Text>
          </View>
          {updatedFixture?.played ? (
            <Text style={styles.scoreline}>{homeGoals} × {awayGoals}</Text>
          ) : (
            <Text style={styles.scorelineVs}>VS</Text>
          )}
          <View style={[styles.teamBlock, styles.teamBlockRight]}>
            <Text style={[styles.teamName, styles.teamNameRight]} numberOfLines={2}>{awayClub?.name ?? '?'}</Text>
            <Text style={styles.teamType}>FORA</Text>
          </View>
        </View>

        {/* Result message */}
        {done && updatedFixture?.played && (
          <View style={[styles.resultBanner, { backgroundColor: userWon ? '#0a2a1a' : userDraw ? '#2a2a0a' : '#2a0a0a' }]}>
            <Text style={[styles.resultBannerText, { color: userWon ? '#00ff88' : userDraw ? '#ffaa00' : '#ff4444' }]}>
              {userWon ? '✓ VITÓRIA!' : userDraw ? '= EMPATE' : '✕ DERROTA'}
            </Text>
          </View>
        )}

        {/* Simulate button */}
        {!updatedFixture?.played && (
          <View style={styles.simBlock}>
            {simulating ? (
              <View style={styles.simLoading}>
                <ActivityIndicator color="#00ff88" size="large" />
                <Text style={styles.simLoadingText}>Simulando...</Text>
              </View>
            ) : (
              <TouchableOpacity style={styles.simBtn} onPress={handleSimulate} activeOpacity={0.8}>
                <Text style={styles.simBtnText}>▶ SIMULAR PARTIDA</Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        {/* Events Timeline */}
        {events.length > 0 && (
          <View style={styles.card}>
            <Text style={styles.cardLabel}>LANCES DA PARTIDA</Text>
            {events.map((ev, idx) => {
              const player = ev.playerId ? players[ev.playerId] : null;
              const isHome = ev.clubId === fixture.homeClubId;
              return (
                <View key={idx} style={[styles.eventRow, !isHome && styles.eventRowAway]}>
                  {isHome && <Text style={styles.eventMin}>{ev.minute}'</Text>}
                  <Text style={styles.eventIcon}>{eventIcon(ev.type)}</Text>
                  <View style={styles.eventInfo}>
                    <Text style={styles.eventPlayer}>{player?.name ?? 'Jogador'}</Text>
                    <Text style={styles.eventType}>{eventLabel(ev.type)}</Text>
                  </View>
                  {!isHome && <Text style={styles.eventMinRight}>{ev.minute}'</Text>}
                </View>
              );
            })}
          </View>
        )}

        {/* Lineups */}
        {updatedFixture?.played && (
          <View style={styles.card}>
            <Text style={styles.cardLabel}>ESCALAÇÕES</Text>
            <View style={styles.lineupsRow}>
              <View style={styles.lineupCol}>
                <Text style={styles.lineupClub}>{homeClub?.shortName}</Text>
                {homeLineupIds.map((id, i) => {
                  const p = players[id];
                  return (
                    <Text key={i} style={styles.lineupPlayer} numberOfLines={1}>
                      {i + 1}. {p?.name ?? '—'}
                    </Text>
                  );
                })}
              </View>
              <View style={styles.lineupDivider} />
              <View style={styles.lineupCol}>
                <Text style={styles.lineupClub}>{awayClub?.shortName}</Text>
                {awayLineupIds.map((id, i) => {
                  const p = players[id];
                  return (
                    <Text key={i} style={styles.lineupPlayer} numberOfLines={1}>
                      {i + 1}. {p?.name ?? '—'}
                    </Text>
                  );
                })}
              </View>
            </View>
          </View>
        )}

        <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
          <Text style={styles.backBtnText}>← Voltar ao Hub</Text>
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
    alignItems: 'center',
    marginBottom: 16,
  },
  backBtnSmall: { paddingVertical: 4 },
  backBtnSmallText: { color: '#00ff88', fontSize: 14, fontWeight: '600' },
  headerDate: { color: '#666', fontSize: 11 },
  scoreCard: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  teamBlock: { flex: 1 },
  teamBlockRight: { alignItems: 'flex-end' },
  teamName: { color: '#fff', fontSize: 16, fontWeight: '900', lineHeight: 20 },
  teamNameRight: { textAlign: 'right' },
  teamType: { color: '#555', fontSize: 9, fontWeight: '700', marginTop: 4 },
  scoreline: { color: '#00ff88', fontSize: 40, fontWeight: '900', fontVariant: ['tabular-nums'], marginHorizontal: 8 },
  scorelineVs: { color: '#555', fontSize: 24, fontWeight: '700', marginHorizontal: 16 },
  resultBanner: {
    borderRadius: 6,
    paddingVertical: 10,
    alignItems: 'center',
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#2a2a2e',
  },
  resultBannerText: { fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  simBlock: { marginBottom: 10 },
  simLoading: { alignItems: 'center', paddingVertical: 24, gap: 12 },
  simLoadingText: { color: '#aaa', fontSize: 14 },
  simBtn: {
    backgroundColor: '#00ff88',
    borderRadius: 8,
    paddingVertical: 16,
    alignItems: 'center',
  },
  simBtnText: { color: '#0a0a0f', fontSize: 16, fontWeight: '900', letterSpacing: 1 },
  card: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  cardLabel: { color: '#666', fontSize: 9, fontWeight: '700', letterSpacing: 1.5, marginBottom: 10 },
  eventRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a3e',
    gap: 8,
  },
  eventRowAway: { flexDirection: 'row-reverse' },
  eventMin: { color: '#555', fontSize: 11, width: 28, fontVariant: ['tabular-nums'] },
  eventMinRight: { color: '#555', fontSize: 11, width: 28, fontVariant: ['tabular-nums'], textAlign: 'right' },
  eventIcon: { fontSize: 16, width: 24, textAlign: 'center' },
  eventInfo: { flex: 1 },
  eventPlayer: { color: '#ddd', fontSize: 12, fontWeight: '600' },
  eventType: { color: '#666', fontSize: 10 },
  lineupsRow: { flexDirection: 'row', gap: 8 },
  lineupCol: { flex: 1 },
  lineupDivider: { width: 1, backgroundColor: '#2a2a3e' },
  lineupClub: { color: '#00ff88', fontSize: 11, fontWeight: '900', marginBottom: 6, letterSpacing: 1 },
  lineupPlayer: { color: '#aaa', fontSize: 10, marginBottom: 2, fontVariant: ['tabular-nums'] },
  backBtn: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#2a2a3e',
    marginTop: 6,
  },
  backBtnText: { color: '#00ff88', fontSize: 13, fontWeight: '700' },
  errorText: { color: '#ff4444', padding: 20, fontSize: 14 },
});
