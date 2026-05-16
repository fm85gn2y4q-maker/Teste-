// ============================================================
// LeagueScreen — League Table + Fixtures
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
} from 'react-native';
import { useGameStore, selectSortedLeagueTable } from '../store';
import { Fixture } from '../types';

type TabType = 'Tabela' | 'Jogos';

function fmtDate(d: string): string {
  const [y, m, day] = d.split('-');
  return `${day}/${m}`;
}

function zoneColor(pos: number, total: number): string {
  if (pos <= 4) return '#00ff8833'; // Libertadores
  if (pos <= 6) return '#ffaa0022'; // Sul-Americana
  if (pos > total - 4) return '#ff444422'; // Relegation
  return 'transparent';
}

function zoneBorderColor(pos: number, total: number): string {
  if (pos <= 4) return '#00ff8866';
  if (pos <= 6) return '#ffaa0066';
  if (pos > total - 4) return '#ff444466';
  return 'transparent';
}

export default function LeagueScreen() {
  const table = useGameStore(selectSortedLeagueTable);
  const clubs = useGameStore((s) => s.clubs);
  const fixtures = useGameStore((s) => s.fixtures);
  const userClubId = useGameStore((s) => s.userClubId);

  const [tab, setTab] = useState<TabType>('Tabela');

  const total = table.length;

  // Group fixtures by round
  const rounds = fixtures.reduce<Record<number, Fixture[]>>((acc, f) => {
    if (!acc[f.round]) acc[f.round] = [];
    acc[f.round].push(f);
    return acc;
  }, {});
  const sortedRounds = Object.keys(rounds)
    .map(Number)
    .sort((a, b) => a - b);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
      <View style={styles.header}>
        <Text style={styles.screenTitle}>CAMPEONATO BRASILEIRO</Text>
        <Text style={styles.headerSub}>SÉRIE A 2003</Text>
      </View>

      {/* Tab bar */}
      <View style={styles.tabBar}>
        {(['Tabela', 'Jogos'] as TabType[]).map((t) => (
          <TouchableOpacity
            key={t}
            style={[styles.tab, tab === t && styles.tabActive]}
            onPress={() => setTab(t)}
          >
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>{t.toUpperCase()}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {tab === 'Tabela' ? (
        <ScrollView>
          {/* Column headers */}
          <View style={styles.colHeader}>
            <Text style={[styles.colText, { width: 24 }]}>POS</Text>
            <Text style={[styles.colText, { flex: 1 }]}>CLUBE</Text>
            <Text style={[styles.colText, { width: 22 }]}>P</Text>
            <Text style={[styles.colText, { width: 22 }]}>V</Text>
            <Text style={[styles.colText, { width: 22 }]}>E</Text>
            <Text style={[styles.colText, { width: 22 }]}>D</Text>
            <Text style={[styles.colText, { width: 28 }]}>GP</Text>
            <Text style={[styles.colText, { width: 28 }]}>GC</Text>
            <Text style={[styles.colText, { width: 28 }]}>SG</Text>
            <Text style={[styles.colText, { width: 28 }]}>PTS</Text>
          </View>

          {table.map((row, idx) => {
            const pos = idx + 1;
            const club = clubs[row.clubId];
            const isUser = row.clubId === userClubId;
            const bg = zoneColor(pos, total);
            const border = zoneBorderColor(pos, total);

            return (
              <View
                key={row.clubId}
                style={[
                  styles.tableRow,
                  isUser && styles.tableRowUser,
                  { backgroundColor: isUser ? '#0a2a1a' : bg },
                  { borderColor: isUser ? '#00ff88' : border },
                  { borderWidth: (isUser || border !== 'transparent') ? 1 : 0 },
                ]}
              >
                <Text style={[styles.cell, { width: 24 }, isUser && styles.cellUser]}>{pos}</Text>
                <Text style={[styles.clubCell, { flex: 1 }, isUser && styles.cellUser]} numberOfLines={1}>
                  {club?.shortName ?? '?'}
                </Text>
                <Text style={[styles.cell, { width: 22 }]}>{row.played}</Text>
                <Text style={[styles.cell, { width: 22, color: '#00ff88' }]}>{row.won}</Text>
                <Text style={[styles.cell, { width: 22, color: '#ffaa00' }]}>{row.drawn}</Text>
                <Text style={[styles.cell, { width: 22, color: '#ff4444' }]}>{row.lost}</Text>
                <Text style={[styles.cell, { width: 28 }]}>{row.goalsFor}</Text>
                <Text style={[styles.cell, { width: 28 }]}>{row.goalsAgainst}</Text>
                <Text style={[styles.cell, { width: 28 }]}>
                  {row.goalsFor - row.goalsAgainst > 0 ? '+' : ''}{row.goalsFor - row.goalsAgainst}
                </Text>
                <Text style={[styles.cell, { width: 28, fontWeight: '900', color: isUser ? '#00ff88' : '#fff' }]}>
                  {row.points}
                </Text>
              </View>
            );
          })}

          {/* Zone legend */}
          <View style={styles.legend}>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#00ff88' }]} />
              <Text style={styles.legendText}>Libertadores (1-4)</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#ffaa00' }]} />
              <Text style={styles.legendText}>Sul-Americana (5-6)</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#ff4444' }]} />
              <Text style={styles.legendText}>Rebaixamento (últimos 4)</Text>
            </View>
          </View>
        </ScrollView>
      ) : (
        <ScrollView contentContainerStyle={styles.fixturesScroll}>
          {sortedRounds.map((round) => {
            const roundFixtures = rounds[round].sort((a, b) => a.date.localeCompare(b.date));
            return (
              <View key={round} style={styles.roundBlock}>
                <Text style={styles.roundTitle}>RODADA {round}</Text>
                {roundFixtures.map((f) => {
                  const homeClub = clubs[f.homeClubId];
                  const awayClub = clubs[f.awayClubId];
                  const isUserFixture = f.homeClubId === userClubId || f.awayClubId === userClubId;
                  return (
                    <View
                      key={f.id}
                      style={[
                        styles.fixtureRow,
                        isUserFixture && styles.fixtureRowUser,
                      ]}
                    >
                      <Text style={styles.fixtureDate}>{fmtDate(f.date)}</Text>
                      <Text style={[styles.fixtureTeam, { textAlign: 'right' }]} numberOfLines={1}>
                        {homeClub?.shortName ?? '?'}
                      </Text>
                      {f.played ? (
                        <Text style={styles.fixtureScore}>
                          {f.homeGoals} × {f.awayGoals}
                        </Text>
                      ) : (
                        <Text style={styles.fixtureVs}>vs</Text>
                      )}
                      <Text style={styles.fixtureTeam} numberOfLines={1}>
                        {awayClub?.shortName ?? '?'}
                      </Text>
                    </View>
                  );
                })}
              </View>
            );
          })}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0a0a0f' },
  header: {
    paddingHorizontal: 12,
    paddingTop: 12,
    paddingBottom: 8,
  },
  screenTitle: { color: '#00ff88', fontSize: 14, fontWeight: '900', letterSpacing: 1.5 },
  headerSub: { color: '#555', fontSize: 10, marginTop: 2 },
  tabBar: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a3e',
  },
  tab: { flex: 1, paddingVertical: 10, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderBottomColor: '#00ff88' },
  tabText: { color: '#555', fontSize: 11, fontWeight: '700' },
  tabTextActive: { color: '#00ff88' },
  colHeader: {
    flexDirection: 'row',
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: '#111',
    alignItems: 'center',
  },
  colText: { color: '#444', fontSize: 8, fontWeight: '700', letterSpacing: 0.5, textAlign: 'center' },
  tableRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a2e',
    marginHorizontal: 4,
    marginVertical: 1,
    borderRadius: 4,
  },
  tableRowUser: {
    borderRadius: 4,
  },
  cell: {
    color: '#aaa',
    fontSize: 11,
    fontVariant: ['tabular-nums'],
    textAlign: 'center',
  },
  cellUser: { color: '#00ff88', fontWeight: '700' },
  clubCell: {
    color: '#ddd',
    fontSize: 12,
    fontWeight: '500',
    paddingLeft: 2,
  },
  legend: {
    padding: 12,
    gap: 6,
    borderTopWidth: 1,
    borderTopColor: '#1a1a2e',
    marginTop: 8,
  },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendText: { color: '#666', fontSize: 11 },
  fixturesScroll: { padding: 12, paddingBottom: 32 },
  roundBlock: { marginBottom: 16 },
  roundTitle: {
    color: '#00ff88',
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 1.5,
    marginBottom: 6,
  },
  fixtureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a2e',
    borderRadius: 6,
    paddingVertical: 8,
    paddingHorizontal: 10,
    marginBottom: 4,
    borderWidth: 1,
    borderColor: '#2a2a3e',
    gap: 6,
  },
  fixtureRowUser: {
    borderColor: '#00ff8844',
    backgroundColor: '#0a1a0f',
  },
  fixtureDate: { color: '#555', fontSize: 10, width: 32, fontVariant: ['tabular-nums'] },
  fixtureTeam: { color: '#ddd', fontSize: 12, fontWeight: '600', flex: 1 },
  fixtureScore: {
    color: '#00ff88',
    fontSize: 14,
    fontWeight: '900',
    fontVariant: ['tabular-nums'],
    width: 48,
    textAlign: 'center',
  },
  fixtureVs: { color: '#555', fontSize: 11, width: 28, textAlign: 'center' },
});
