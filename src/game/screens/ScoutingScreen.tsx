// ============================================================
// ScoutingScreen — Scouting
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
  Alert,
  FlatList,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types/navigation';
import { useGameStore } from '../store';
import { Player, ScoutReport } from '../types';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Scouting'>;
};

const fmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });

function starDisplay(n: number): string {
  return '★'.repeat(n) + '☆'.repeat(5 - n);
}

interface AttrBarProps {
  label: string;
  value: number | undefined;
}

function AttrBar({ label, value }: AttrBarProps) {
  const isHidden = value === undefined;
  const pct = isHidden ? 0 : (value / 20) * 100;
  const color = isHidden ? '#333' : value >= 15 ? '#00ff88' : value >= 10 ? '#ffaa00' : '#666';
  return (
    <View style={attrStyles.row}>
      <Text style={attrStyles.label}>{label}</Text>
      <View style={attrStyles.track}>
        <View style={[attrStyles.fill, { width: `${pct}%`, backgroundColor: color }]} />
      </View>
      <Text style={[attrStyles.val, { color }]}>{isHidden ? '???' : value}</Text>
    </View>
  );
}

const attrStyles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', marginBottom: 4, gap: 6 },
  label: { color: '#888', fontSize: 10, width: 80 },
  track: { flex: 1, height: 4, backgroundColor: '#2a2a3e', borderRadius: 2, overflow: 'hidden' },
  fill: { height: 4, borderRadius: 2 },
  val: { width: 24, fontSize: 10, fontVariant: ['tabular-nums'], textAlign: 'right', fontWeight: '700' },
});

export default function ScoutingScreen({ navigation }: Props) {
  const allPlayers = useGameStore((s) => Object.values(s.players));
  const clubs = useGameStore((s) => s.clubs);
  const userClubId = useGameStore((s) => s.userClubId);
  const userClub = clubs[userClubId];
  const scoutReports = useGameStore((s) => s.scoutReports);
  const scoutPlayer = useGameStore((s) => s.scoutPlayer);

  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Players not in user's club
  const otherPlayers = allPlayers.filter((p) => p.clubId !== userClubId);
  const knownPlayers = otherPlayers.filter((p) => p.isScoutKnown);
  const unknownPlayers = otherPlayers.filter((p) => !p.isScoutKnown);

  function getLatestReport(playerId: string): ScoutReport | undefined {
    return scoutReports
      .filter((r) => r.playerId === playerId)
      .sort((a, b) => b.date.localeCompare(a.date))[0];
  }

  function handleScout(player: Player) {
    if (!userClub || userClub.budget < 50000) {
      Alert.alert('Orçamento insuficiente', 'Você precisa de R$ 50.000 para enviar um scout.');
      return;
    }
    scoutPlayer(player.id);
    Alert.alert('Scout enviado!', `Um scout foi enviado para observar ${player.name}. Custo: R$ 50.000`);
  }

  const knownData = knownPlayers.sort((a, b) => {
    const ra = getLatestReport(a.id)?.starRating ?? 0;
    const rb = getLatestReport(b.id)?.starRating ?? 0;
    return rb - ra;
  });

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backBtnText}>← Voltar</Text>
        </TouchableOpacity>
        <Text style={styles.screenTitle}>DEPARTAMENTO DE SCOUTING</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Budget info */}
        <View style={styles.infoCard}>
          <Text style={styles.infoText}>
            Orçamento disponível: <Text style={styles.budgetText}>{fmt.format(userClub?.budget ?? 0)}</Text>
          </Text>
          <Text style={styles.infoSub}>Custo por scout: R$ 50.000</Text>
        </View>

        {/* Known players */}
        {knownData.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>JOGADORES SCOUTADOS ({knownData.length})</Text>
            {knownData.map((player) => {
              const report = getLatestReport(player.id);
              const club = clubs[player.clubId];
              const isExpanded = expandedId === player.id;
              return (
                <View key={player.id} style={styles.playerCard}>
                  <TouchableOpacity
                    style={styles.playerCardHeader}
                    onPress={() => setExpandedId(isExpanded ? null : player.id)}
                    activeOpacity={0.8}
                  >
                    <View style={styles.playerHeaderLeft}>
                      <Text style={styles.playerCardName}>{player.name}</Text>
                      <Text style={styles.playerCardInfo}>
                        {player.position} · {player.age} anos · {club?.shortName ?? '?'}
                      </Text>
                      {report && (
                        <Text style={styles.stars}>{starDisplay(report.starRating)}</Text>
                      )}
                    </View>
                    <View style={styles.playerHeaderRight}>
                      <Text style={styles.playerValue}>{(player.value / 1000000).toFixed(1)}M</Text>
                      <Text style={styles.expandChevron}>{isExpanded ? '▼' : '▶'}</Text>
                    </View>
                  </TouchableOpacity>

                  {isExpanded && report && (
                    <View style={styles.reportPanel}>
                      <Text style={styles.reportDesc}>{report.description}</Text>
                      <Text style={styles.reportDate}>Relatório: {report.date}</Text>
                      <View style={styles.attrSection}>
                        <Text style={styles.attrSectionLabel}>ATRIBUTOS REVELADOS</Text>
                        {Object.entries(report.attributesRevealed).map(([key, val]) => (
                          <AttrBar key={key} label={key} value={val as number} />
                        ))}
                      </View>
                    </View>
                  )}
                </View>
              );
            })}
          </View>
        )}

        {/* Unknown players (first 30 for performance) */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>JOGADORES DESCONHECIDOS ({unknownPlayers.length})</Text>
          {unknownPlayers.slice(0, 40).map((player) => {
            const club = clubs[player.clubId];
            return (
              <View key={player.id} style={styles.unknownRow}>
                <View style={styles.unknownInfo}>
                  <Text style={styles.unknownName}>{player.name}</Text>
                  <Text style={styles.unknownMeta}>
                    {player.position} · {player.age} anos · {club?.shortName ?? '?'}
                  </Text>
                  <Text style={styles.unknownAttrs}>Atributos: ??? ??? ???</Text>
                </View>
                <TouchableOpacity
                  style={styles.scoutBtn}
                  onPress={() => handleScout(player)}
                  activeOpacity={0.8}
                >
                  <Text style={styles.scoutBtnText}>🔭 SCOUT</Text>
                </TouchableOpacity>
              </View>
            );
          })}
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
  screenTitle: { color: '#00ff88', fontSize: 13, fontWeight: '900', letterSpacing: 1, flex: 1 },
  scroll: { padding: 12, paddingBottom: 32 },
  infoCard: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  infoText: { color: '#aaa', fontSize: 12 },
  budgetText: { color: '#00ff88', fontWeight: '700' },
  infoSub: { color: '#555', fontSize: 10, marginTop: 4 },
  section: { marginBottom: 12 },
  sectionTitle: { color: '#666', fontSize: 9, fontWeight: '700', letterSpacing: 1.5, marginBottom: 8 },
  playerCard: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#2a2a3e',
    overflow: 'hidden',
  },
  playerCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 12,
  },
  playerHeaderLeft: { flex: 1 },
  playerHeaderRight: { alignItems: 'flex-end', gap: 4 },
  playerCardName: { color: '#fff', fontSize: 14, fontWeight: '700' },
  playerCardInfo: { color: '#888', fontSize: 11, marginTop: 2 },
  stars: { color: '#f4c430', fontSize: 12, marginTop: 4, letterSpacing: 2 },
  playerValue: { color: '#00ff88', fontSize: 12, fontVariant: ['tabular-nums'] },
  expandChevron: { color: '#555', fontSize: 10 },
  reportPanel: {
    backgroundColor: '#111',
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: '#2a2a3e',
  },
  reportDesc: { color: '#aaa', fontSize: 12, lineHeight: 18, marginBottom: 4 },
  reportDate: { color: '#555', fontSize: 10, marginBottom: 10 },
  attrSection: {},
  attrSectionLabel: { color: '#00ff88', fontSize: 8, fontWeight: '700', letterSpacing: 1.5, marginBottom: 6 },
  unknownRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 12,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: '#2a2a3e',
    gap: 10,
  },
  unknownInfo: { flex: 1 },
  unknownName: { color: '#ddd', fontSize: 13, fontWeight: '600' },
  unknownMeta: { color: '#888', fontSize: 11, marginTop: 2 },
  unknownAttrs: { color: '#555', fontSize: 10, marginTop: 2 },
  scoutBtn: {
    backgroundColor: '#0a2a1a',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: '#00ff88',
  },
  scoutBtnText: { color: '#00ff88', fontSize: 11, fontWeight: '700' },
});
