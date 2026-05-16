// ============================================================
// SquadScreen — Squad Management
// ============================================================
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Modal,
  SafeAreaView,
  StatusBar,
  FlatList,
} from 'react-native';
import { useGameStore, selectUserPlayers } from '../store';
import { Player, PlayerCondition, Position } from '../types';

type TabType = 'GK' | 'DEF' | 'MEI' | 'ATA';
type SortType = 'rating' | 'position' | 'age' | 'value';

const POSITION_GROUPS: Record<TabType, Position[]> = {
  GK: ['GK'],
  DEF: ['SW', 'DC', 'DL', 'DR', 'WBL', 'WBR'],
  MEI: ['DM', 'MC', 'ML', 'MR', 'AMC', 'AML', 'AMR'],
  ATA: ['SC'],
};

const CONDITION_COLORS: Record<PlayerCondition, string> = {
  Fit: '#00ff88',
  'Carrying Knock': '#ffaa00',
  Injured: '#ff4444',
  Suspended: '#ff6600',
};

const CONDITION_LABELS: Record<PlayerCondition, string> = {
  Fit: 'FIT',
  'Carrying Knock': 'KNOCK',
  Injured: 'LESÃO',
  Suspended: 'SUSP',
};

const fmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });

function moraleStars(m: number): string {
  const stars = Math.round(m / 2);
  return '★'.repeat(stars) + '☆'.repeat(5 - stars);
}

function ratingColor(r: number): string {
  if (r >= 7.5) return '#00ff88';
  if (r >= 6.5) return '#ffaa00';
  return '#ff4444';
}

function attrAvg(attrs: Player['attributes'], keys: (keyof Player['attributes'])[]): number {
  return Math.round(keys.reduce((s, k) => s + attrs[k], 0) / keys.length);
}

interface PlayerDetailModalProps {
  player: Player | null;
  onClose: () => void;
  clubName: string;
}

function PlayerDetailModal({ player, onClose, clubName }: PlayerDetailModalProps) {
  if (!player) return null;
  const a = player.attributes;

  const technicalKeys: (keyof Player['attributes'])[] = [
    'passing', 'crossing', 'dribbling', 'finishing', 'firstTouch', 'heading',
    'longShots', 'marking', 'tackling', 'technique', 'corners', 'freekicks', 'penalties', 'longPassing',
  ];
  const mentalKeys: (keyof Player['attributes'])[] = [
    'aggression', 'anticipation', 'bravery', 'composure', 'concentration', 'creativity',
    'decisions', 'determination', 'flair', 'influence', 'offTheBall', 'positioning', 'teamwork', 'workRate',
  ];
  const physicalKeys: (keyof Player['attributes'])[] = [
    'acceleration', 'agility', 'balance', 'jumping', 'naturalFitness', 'pace', 'stamina', 'strength',
  ];
  const gkKeys: (keyof Player['attributes'])[] = [
    'aerial', 'command', 'communication', 'eccentricity', 'handling', 'kicking', 'oneOnOnes', 'reflexes', 'throwing',
  ];

  const ATTR_PT: Partial<Record<keyof Player['attributes'], string>> = {
    passing: 'Passe', crossing: 'Cruzamento', dribbling: 'Drible', finishing: 'Finalização',
    firstTouch: 'Primeiro Toque', heading: 'Cabeçada', longShots: 'Chute Longo', marking: 'Marcação',
    tackling: 'Carrinho', technique: 'Técnica', corners: 'Escanteio', freekicks: 'Falta', penalties: 'Pênalti', longPassing: 'Passe Longo',
    aggression: 'Agressividade', anticipation: 'Antecipação', bravery: 'Bravura', composure: 'Compostura',
    concentration: 'Concentração', creativity: 'Criatividade', decisions: 'Decisões', determination: 'Determinação',
    flair: 'Genialidade', influence: 'Influência', offTheBall: 'Sem Bola', positioning: 'Posicionamento', teamwork: 'Trabalho Em Equipe', workRate: 'Empenho',
    acceleration: 'Aceleração', agility: 'Agilidade', balance: 'Equilíbrio', jumping: 'Salto',
    naturalFitness: 'Condição Física', pace: 'Velocidade', stamina: 'Resistência', strength: 'Força',
    aerial: 'Jogo Aéreo', command: 'Comando', communication: 'Comunicação', eccentricity: 'Excentricidade',
    handling: 'Pegada', kicking: 'Chute', oneOnOnes: 'Um p/ Um', reflexes: 'Reflexos', throwing: 'Arremesso',
  };

  function AttrRow({ attrKey }: { attrKey: keyof Player['attributes'] }) {
    const val = a[attrKey];
    const pct = (val / 20) * 100;
    const color = val >= 15 ? '#00ff88' : val >= 10 ? '#ffaa00' : '#666';
    return (
      <View style={modalStyles.attrRow}>
        <Text style={modalStyles.attrName}>{ATTR_PT[attrKey] ?? attrKey}</Text>
        <View style={modalStyles.attrBarBg}>
          <View style={[modalStyles.attrBarFill, { width: `${pct}%`, backgroundColor: color }]} />
        </View>
        <Text style={[modalStyles.attrVal, { color }]}>{val}</Text>
      </View>
    );
  }

  const contractExpiry = player.contractExpiry.slice(0, 7);
  const formDots = player.form.slice(0, 5);

  return (
    <Modal visible animationType="slide" transparent>
      <View style={modalStyles.overlay}>
        <SafeAreaView style={modalStyles.container}>
          <View style={modalStyles.header}>
            <View>
              <Text style={modalStyles.playerName}>{player.name}</Text>
              <Text style={modalStyles.playerInfo}>
                {player.position} · {player.age} anos · {player.nationality}
              </Text>
              <Text style={modalStyles.playerInfo}>{clubName}</Text>
            </View>
            <TouchableOpacity onPress={onClose} style={modalStyles.closeBtn}>
              <Text style={modalStyles.closeBtnText}>✕</Text>
            </TouchableOpacity>
          </View>

          {/* Form chart */}
          <View style={modalStyles.formRow}>
            <Text style={modalStyles.sectionLabel}>FORMA</Text>
            <View style={modalStyles.formDots}>
              {formDots.map((r, i) => (
                <View key={i} style={[modalStyles.formDot, { backgroundColor: ratingColor(r) }]}>
                  <Text style={modalStyles.formDotText}>{r.toFixed(1)}</Text>
                </View>
              ))}
            </View>
          </View>

          <ScrollView style={modalStyles.scroll}>
            {/* Quick stats */}
            <View style={modalStyles.statsRow}>
              <View style={modalStyles.statBlock}>
                <Text style={modalStyles.statVal}>{player.fitness}%</Text>
                <Text style={modalStyles.statLbl}>Condição</Text>
              </View>
              <View style={modalStyles.statBlock}>
                <Text style={modalStyles.statVal}>{moraleStars(player.morale)}</Text>
                <Text style={modalStyles.statLbl}>Moral</Text>
              </View>
              <View style={modalStyles.statBlock}>
                <Text style={modalStyles.statVal}>{player.goals}</Text>
                <Text style={modalStyles.statLbl}>Gols</Text>
              </View>
              <View style={modalStyles.statBlock}>
                <Text style={modalStyles.statVal}>{player.assists}</Text>
                <Text style={modalStyles.statLbl}>Assistências</Text>
              </View>
            </View>

            {/* Contract */}
            <View style={modalStyles.section}>
              <Text style={modalStyles.sectionLabel}>CONTRATO</Text>
              <Text style={modalStyles.contractText}>
                Expira: {contractExpiry} · Salário: {fmt.format(player.wage)}/sem
              </Text>
              <Text style={modalStyles.contractText}>
                Valor de mercado: {fmt.format(player.value)}
              </Text>
            </View>

            {/* Technical */}
            <View style={modalStyles.section}>
              <Text style={modalStyles.sectionLabel}>TÉCNICO</Text>
              {technicalKeys.map((k) => <AttrRow key={k} attrKey={k} />)}
            </View>

            {/* Mental */}
            <View style={modalStyles.section}>
              <Text style={modalStyles.sectionLabel}>MENTAL</Text>
              {mentalKeys.map((k) => <AttrRow key={k} attrKey={k} />)}
            </View>

            {/* Physical */}
            <View style={modalStyles.section}>
              <Text style={modalStyles.sectionLabel}>FÍSICO</Text>
              {physicalKeys.map((k) => <AttrRow key={k} attrKey={k} />)}
            </View>

            {/* GK */}
            {player.position === 'GK' && (
              <View style={modalStyles.section}>
                <Text style={modalStyles.sectionLabel}>GOLEIRO</Text>
                {gkKeys.map((k) => <AttrRow key={k} attrKey={k} />)}
              </View>
            )}

            {/* Hidden attributes */}
            <View style={modalStyles.section}>
              <Text style={modalStyles.sectionLabel}>ATRIBUTOS OCULTOS</Text>
              {Object.keys(player.hidden).map((k) => (
                <View key={k} style={modalStyles.attrRow}>
                  <Text style={modalStyles.attrName}>{k}</Text>
                  <Text style={modalStyles.attrVal}>???</Text>
                </View>
              ))}
            </View>
          </ScrollView>
        </SafeAreaView>
      </View>
    </Modal>
  );
}

export default function SquadScreen() {
  const players = useGameStore(selectUserPlayers);
  const clubs = useGameStore((s) => s.clubs);
  const userClubId = useGameStore((s) => s.userClubId);
  const userClub = clubs[userClubId];

  const [activeTab, setActiveTab] = useState<TabType>('DEF');
  const [sort, setSort] = useState<SortType>('rating');
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);

  const tabs: TabType[] = ['GK', 'DEF', 'MEI', 'ATA'];

  const filteredPlayers = players
    .filter((p) => POSITION_GROUPS[activeTab].includes(p.position))
    .sort((a, b) => {
      if (sort === 'rating') return b.currentRating - a.currentRating;
      if (sort === 'age') return a.age - b.age;
      if (sort === 'value') return b.value - a.value;
      return a.position.localeCompare(b.position);
    });

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
      <View style={styles.headerRow}>
        <Text style={styles.screenTitle}>ELENCO</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View style={styles.sortRow}>
            {(['rating', 'position', 'age', 'value'] as SortType[]).map((s) => (
              <TouchableOpacity
                key={s}
                style={[styles.sortBtn, sort === s && styles.sortBtnActive]}
                onPress={() => setSort(s)}
              >
                <Text style={[styles.sortBtnText, sort === s && styles.sortBtnTextActive]}>
                  {s === 'rating' ? 'NOTA' : s === 'position' ? 'POS' : s === 'age' ? 'IDADE' : 'VALOR'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </ScrollView>
      </View>

      {/* Tab bar */}
      <View style={styles.tabBar}>
        {tabs.map((tab) => {
          const count = players.filter((p) => POSITION_GROUPS[tab].includes(p.position)).length;
          return (
            <TouchableOpacity
              key={tab}
              style={[styles.tab, activeTab === tab && styles.tabActive]}
              onPress={() => setActiveTab(tab)}
            >
              <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>
                {tab} ({count})
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Column headers */}
      <View style={styles.colHeader}>
        <Text style={[styles.colHeaderText, { flex: 3 }]}>NOME</Text>
        <Text style={[styles.colHeaderText, { width: 32 }]}>POS</Text>
        <Text style={[styles.colHeaderText, { width: 28 }]}>ID</Text>
        <Text style={[styles.colHeaderText, { width: 40 }]}>FIT</Text>
        <Text style={[styles.colHeaderText, { width: 44 }]}>MORAL</Text>
        <Text style={[styles.colHeaderText, { width: 36 }]}>G/A</Text>
        <Text style={[styles.colHeaderText, { width: 32 }]}>NOT</Text>
      </View>

      <FlatList
        data={filteredPlayers}
        keyExtractor={(p) => p.id}
        renderItem={({ item: p }) => (
          <TouchableOpacity style={styles.playerRow} onPress={() => setSelectedPlayer(p)} activeOpacity={0.7}>
            <View style={[styles.condDot, { backgroundColor: CONDITION_COLORS[p.condition] }]} />
            <Text style={[styles.playerName, { flex: 3 }]} numberOfLines={1}>{p.name}</Text>
            <Text style={[styles.playerMono, { width: 32 }]}>{p.position}</Text>
            <Text style={[styles.playerMono, { width: 28 }]}>{p.age}</Text>
            <Text style={[styles.playerMono, { width: 40, color: p.fitness >= 80 ? '#00ff88' : p.fitness >= 60 ? '#ffaa00' : '#ff4444' }]}>
              {p.fitness}%
            </Text>
            <Text style={[styles.playerMono, { width: 44, color: '#f4c430', fontSize: 10 }]}>
              {'★'.repeat(Math.round(p.morale / 2))}
            </Text>
            <Text style={[styles.playerMono, { width: 36 }]}>{p.goals}/{p.assists}</Text>
            <Text style={[styles.playerMono, { width: 32, color: ratingColor(p.currentRating) }]}>
              {p.currentRating.toFixed(1)}
            </Text>
          </TouchableOpacity>
        )}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        style={styles.list}
      />

      {selectedPlayer && (
        <PlayerDetailModal
          player={selectedPlayer}
          onClose={() => setSelectedPlayer(null)}
          clubName={userClub?.name ?? ''}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0a0a0f' },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingTop: 12,
    paddingBottom: 8,
    justifyContent: 'space-between',
  },
  screenTitle: { color: '#00ff88', fontSize: 16, fontWeight: '900', letterSpacing: 1.5, marginRight: 8 },
  sortRow: { flexDirection: 'row', gap: 6 },
  sortBtn: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    backgroundColor: '#1a1a2e',
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  sortBtnActive: { borderColor: '#00ff88', backgroundColor: '#0a2a1a' },
  sortBtnText: { color: '#666', fontSize: 9, fontWeight: '700', letterSpacing: 1 },
  sortBtnTextActive: { color: '#00ff88' },
  tabBar: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: '#2a2a3e' },
  tab: { flex: 1, paddingVertical: 10, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderBottomColor: '#00ff88' },
  tabText: { color: '#555', fontSize: 11, fontWeight: '700' },
  tabTextActive: { color: '#00ff88' },
  colHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#111',
  },
  colHeaderText: { color: '#444', fontSize: 8, fontWeight: '700', letterSpacing: 1 },
  list: { flex: 1 },
  playerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 2,
  },
  condDot: { width: 6, height: 6, borderRadius: 3, marginRight: 6 },
  playerName: { color: '#ddd', fontSize: 12, fontWeight: '500' },
  playerMono: { color: '#aaa', fontSize: 11, fontVariant: ['tabular-nums'] },
  separator: { height: 1, backgroundColor: '#1a1a2e', marginHorizontal: 12 },
});

const modalStyles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.85)' },
  container: { flex: 1, backgroundColor: '#0a0a0f', margin: 0 },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a3e',
    backgroundColor: '#1a1a2e',
  },
  playerName: { color: '#00ff88', fontSize: 20, fontWeight: '900' },
  playerInfo: { color: '#888', fontSize: 12, marginTop: 2 },
  closeBtn: {
    backgroundColor: '#2a2a3e',
    borderRadius: 16,
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
  closeBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  formRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a2e',
    gap: 8,
  },
  formDots: { flexDirection: 'row', gap: 6 },
  formDot: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  formDotText: { color: '#000', fontSize: 10, fontWeight: '900' },
  scroll: { flex: 1 },
  statsRow: {
    flexDirection: 'row',
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a2e',
    gap: 8,
  },
  statBlock: { flex: 1, alignItems: 'center' },
  statVal: { color: '#fff', fontSize: 14, fontWeight: '700' },
  statLbl: { color: '#555', fontSize: 9, marginTop: 2 },
  section: { padding: 12, borderBottomWidth: 1, borderBottomColor: '#1a1a2e' },
  sectionLabel: { color: '#00ff88', fontSize: 9, fontWeight: '700', letterSpacing: 1.5, marginBottom: 8 },
  attrRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
    gap: 6,
  },
  attrName: { color: '#888', fontSize: 11, width: 120 },
  attrBarBg: { flex: 1, height: 4, backgroundColor: '#2a2a3e', borderRadius: 2, overflow: 'hidden' },
  attrBarFill: { height: 4, borderRadius: 2 },
  attrVal: { width: 22, fontSize: 11, fontVariant: ['tabular-nums'], textAlign: 'right', fontWeight: '700' },
  contractText: { color: '#aaa', fontSize: 12, marginBottom: 4 },
});
