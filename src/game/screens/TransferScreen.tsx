// ============================================================
// TransferScreen — Transfer Market
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
  TextInput,
  Modal,
  FlatList,
  Alert,
} from 'react-native';
import { useGameStore } from '../store';
import { Player, TransferOffer } from '../types';

type TabType = 'Mercado' | 'Ofertas';
type PosFilter = 'TODOS' | 'GK' | 'DEF' | 'MEI' | 'ATA';

const fmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
const fmtM = (v: number) => `R$ ${(v / 1000000).toFixed(1)}M`;

const STATUS_COLORS: Record<string, string> = {
  Pending: '#ffaa00',
  Accepted: '#00ff88',
  Rejected: '#ff4444',
  Countered: '#ff6600',
};

const STATUS_PT: Record<string, string> = {
  Pending: 'Pendente',
  Accepted: 'Aceita',
  Rejected: 'Recusada',
  Countered: 'Contra-proposta',
};

const POS_GROUPS: Record<PosFilter, string[]> = {
  TODOS: [],
  GK: ['GK'],
  DEF: ['SW', 'DC', 'DL', 'DR', 'WBL', 'WBR'],
  MEI: ['DM', 'MC', 'ML', 'MR', 'AMC', 'AML', 'AMR'],
  ATA: ['SC'],
};

interface OfferModalProps {
  player: Player | null;
  onClose: () => void;
  onOffer: (amount: number) => void;
  budget: number;
}

function OfferModal({ player, onClose, onOffer, budget }: OfferModalProps) {
  const [amountText, setAmountText] = useState('');
  if (!player) return null;

  function handleOffer() {
    const amount = parseFloat(amountText.replace(/[^0-9.]/g, '')) * 1000000;
    if (isNaN(amount) || amount <= 0) {
      Alert.alert('Valor inválido', 'Digite um valor válido em milhões.');
      return;
    }
    if (amount > budget) {
      Alert.alert('Orçamento insuficiente', `Seu orçamento é ${fmt.format(budget)}.`);
      return;
    }
    onOffer(Math.round(amount));
    onClose();
  }

  return (
    <Modal visible animationType="fade" transparent>
      <View style={modalStyles.overlay}>
        <View style={modalStyles.container}>
          <Text style={modalStyles.title}>FAZER PROPOSTA</Text>
          <Text style={modalStyles.playerName}>{player.name}</Text>
          <Text style={modalStyles.info}>
            {player.position} · {player.age} anos · Valor: {fmtM(player.value)}
          </Text>
          <Text style={modalStyles.budget}>Seu orçamento: {fmt.format(budget)}</Text>
          <View style={modalStyles.inputRow}>
            <Text style={modalStyles.inputPrefix}>R$ </Text>
            <TextInput
              style={modalStyles.input}
              value={amountText}
              onChangeText={setAmountText}
              keyboardType="decimal-pad"
              placeholder="Ex: 2.5 (milhões)"
              placeholderTextColor="#555"
            />
            <Text style={modalStyles.inputSuffix}>M</Text>
          </View>
          <View style={modalStyles.btnRow}>
            <TouchableOpacity style={modalStyles.cancelBtn} onPress={onClose}>
              <Text style={modalStyles.cancelText}>Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={modalStyles.offerBtn} onPress={handleOffer}>
              <Text style={modalStyles.offerText}>💰 FAZER OFERTA</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

export default function TransferScreen() {
  const allPlayers = useGameStore((s) => Object.values(s.players));
  const clubs = useGameStore((s) => s.clubs);
  const userClubId = useGameStore((s) => s.userClubId);
  const userClub = clubs[userClubId];
  const offers = useGameStore((s) => s.transferOffers);
  const makeTransferOffer = useGameStore((s) => s.makeTransferOffer);
  const respondToOffer = useGameStore((s) => s.respondToOffer);

  const [tab, setTab] = useState<TabType>('Mercado');
  const [search, setSearch] = useState('');
  const [posFilter, setPosFilter] = useState<PosFilter>('TODOS');
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);

  const marketPlayers = allPlayers
    .filter((p) => p.clubId !== userClubId)
    .filter((p) => {
      if (posFilter !== 'TODOS' && !POS_GROUPS[posFilter].includes(p.position)) return false;
      if (search && !p.name.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    })
    .sort((a, b) => b.currentRating - a.currentRating);

  function handleOffer(amount: number) {
    if (!selectedPlayer) return;
    makeTransferOffer(selectedPlayer.id, amount);
    Alert.alert('Proposta enviada!', `Proposta de ${fmtM(amount)} enviada por ${selectedPlayer.name}.`);
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
      <View style={styles.header}>
        <Text style={styles.screenTitle}>MERCADO DE TRANSFERÊNCIAS</Text>
        <Text style={styles.budget}>Orçamento: {fmt.format(userClub?.budget ?? 0)}</Text>
      </View>

      {/* Tab bar */}
      <View style={styles.tabBar}>
        {(['Mercado', 'Ofertas'] as TabType[]).map((t) => (
          <TouchableOpacity
            key={t}
            style={[styles.tab, tab === t && styles.tabActive]}
            onPress={() => setTab(t)}
          >
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>{t.toUpperCase()}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {tab === 'Mercado' ? (
        <View style={styles.flex}>
          {/* Search */}
          <View style={styles.searchRow}>
            <TextInput
              style={styles.searchInput}
              value={search}
              onChangeText={setSearch}
              placeholder="🔍 Buscar jogador..."
              placeholderTextColor="#555"
            />
          </View>

          {/* Position filter */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterScroll}>
            <View style={styles.filterRow}>
              {(['TODOS', 'GK', 'DEF', 'MEI', 'ATA'] as PosFilter[]).map((f) => (
                <TouchableOpacity
                  key={f}
                  style={[styles.filterBtn, posFilter === f && styles.filterBtnActive]}
                  onPress={() => setPosFilter(f)}
                >
                  <Text style={[styles.filterText, posFilter === f && styles.filterTextActive]}>{f}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>

          {/* Column header */}
          <View style={styles.colHeader}>
            <Text style={[styles.colText, { flex: 2 }]}>NOME</Text>
            <Text style={[styles.colText, { width: 36 }]}>CLUBE</Text>
            <Text style={[styles.colText, { width: 28 }]}>POS</Text>
            <Text style={[styles.colText, { width: 24 }]}>ID</Text>
            <Text style={[styles.colText, { width: 52 }]}>VALOR</Text>
            <Text style={[styles.colText, { width: 28 }]}>NOT</Text>
          </View>

          <FlatList
            data={marketPlayers}
            keyExtractor={(p) => p.id}
            renderItem={({ item: p }) => {
              const club = clubs[p.clubId];
              return (
                <TouchableOpacity
                  style={styles.playerRow}
                  onPress={() => setSelectedPlayer(p)}
                  activeOpacity={0.75}
                >
                  <Text style={[styles.playerName, { flex: 2 }]} numberOfLines={1}>{p.name}</Text>
                  <Text style={[styles.playerMono, { width: 36 }]} numberOfLines={1}>{club?.shortName ?? '?'}</Text>
                  <Text style={[styles.playerMono, { width: 28 }]}>{p.position}</Text>
                  <Text style={[styles.playerMono, { width: 24 }]}>{p.age}</Text>
                  <Text style={[styles.playerMono, { width: 52, color: '#00ff88' }]}>
                    {(p.value / 1000000).toFixed(1)}M
                  </Text>
                  <Text style={[styles.playerMono, { width: 28, color: p.currentRating >= 7 ? '#00ff88' : p.currentRating >= 6 ? '#ffaa00' : '#aaa' }]}>
                    {p.currentRating.toFixed(1)}
                  </Text>
                </TouchableOpacity>
              );
            }}
            ItemSeparatorComponent={() => <View style={styles.separator} />}
          />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.offersScroll}>
          {offers.length === 0 ? (
            <Text style={styles.emptyText}>Nenhuma oferta no momento.</Text>
          ) : (
            offers.map((offer) => {
              const player = allPlayers.find((p) => p.id === offer.playerId);
              const fromClub = clubs[offer.fromClubId];
              const toClub = clubs[offer.toClubId];
              const isIncoming = offer.toClubId === userClubId;
              return (
                <View key={offer.id} style={styles.offerCard}>
                  <View style={styles.offerTop}>
                    <Text style={styles.offerPlayerName}>{player?.name ?? '?'}</Text>
                    <View style={[styles.statusBadge, { backgroundColor: STATUS_COLORS[offer.status] + '22' }]}>
                      <Text style={[styles.statusText, { color: STATUS_COLORS[offer.status] }]}>
                        {STATUS_PT[offer.status]}
                      </Text>
                    </View>
                  </View>
                  <Text style={styles.offerInfo}>
                    {fromClub?.shortName} → {toClub?.shortName} · {fmtM(offer.amount)}
                  </Text>
                  {offer.counterAmount && (
                    <Text style={styles.offerCounter}>Contra-proposta: {fmtM(offer.counterAmount)}</Text>
                  )}
                  {isIncoming && offer.status === 'Pending' && (
                    <View style={styles.offerActions}>
                      <TouchableOpacity
                        style={styles.acceptBtn}
                        onPress={() => respondToOffer(offer.id, true)}
                      >
                        <Text style={styles.acceptBtnText}>✓ Aceitar</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={styles.rejectBtn}
                        onPress={() => respondToOffer(offer.id, false)}
                      >
                        <Text style={styles.rejectBtnText}>✕ Recusar</Text>
                      </TouchableOpacity>
                    </View>
                  )}
                </View>
              );
            })
          )}
        </ScrollView>
      )}

      <OfferModal
        player={selectedPlayer}
        onClose={() => setSelectedPlayer(null)}
        onOffer={handleOffer}
        budget={userClub?.budget ?? 0}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0a0a0f' },
  flex: { flex: 1 },
  header: {
    paddingHorizontal: 12,
    paddingTop: 12,
    paddingBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  screenTitle: { color: '#00ff88', fontSize: 13, fontWeight: '900', letterSpacing: 1, flex: 1 },
  budget: { color: '#00ff88', fontSize: 11, fontVariant: ['tabular-nums'] },
  tabBar: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a3e',
  },
  tab: { flex: 1, paddingVertical: 10, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderBottomColor: '#00ff88' },
  tabText: { color: '#555', fontSize: 11, fontWeight: '700' },
  tabTextActive: { color: '#00ff88' },
  searchRow: { paddingHorizontal: 12, paddingVertical: 8 },
  searchInput: {
    backgroundColor: '#1a1a2e',
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    color: '#fff',
    fontSize: 13,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  filterScroll: { maxHeight: 40 },
  filterRow: { flexDirection: 'row', paddingHorizontal: 12, paddingBottom: 8, gap: 6 },
  filterBtn: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
    backgroundColor: '#1a1a2e',
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  filterBtnActive: { backgroundColor: '#0a2a1a', borderColor: '#00ff88' },
  filterText: { color: '#666', fontSize: 10, fontWeight: '700' },
  filterTextActive: { color: '#00ff88' },
  colHeader: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#111',
  },
  colText: { color: '#444', fontSize: 8, fontWeight: '700', letterSpacing: 1 },
  playerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 2,
  },
  playerName: { color: '#ddd', fontSize: 12, fontWeight: '500' },
  playerMono: { color: '#aaa', fontSize: 11, fontVariant: ['tabular-nums'] },
  separator: { height: 1, backgroundColor: '#1a1a2e', marginHorizontal: 12 },
  offersScroll: { padding: 12, gap: 10 },
  emptyText: { color: '#555', textAlign: 'center', marginTop: 48, fontSize: 14 },
  offerCard: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 14,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  offerTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  offerPlayerName: { color: '#fff', fontSize: 14, fontWeight: '700', flex: 1 },
  statusBadge: { borderRadius: 4, paddingHorizontal: 8, paddingVertical: 3 },
  statusText: { fontSize: 10, fontWeight: '700', letterSpacing: 0.5 },
  offerInfo: { color: '#888', fontSize: 11, marginBottom: 4 },
  offerCounter: { color: '#ffaa00', fontSize: 11, marginBottom: 6 },
  offerActions: { flexDirection: 'row', gap: 8, marginTop: 8 },
  acceptBtn: {
    flex: 1,
    backgroundColor: '#0a2a1a',
    borderRadius: 6,
    paddingVertical: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#00ff88',
  },
  acceptBtnText: { color: '#00ff88', fontSize: 12, fontWeight: '700' },
  rejectBtn: {
    flex: 1,
    backgroundColor: '#2a0a0a',
    borderRadius: 6,
    paddingVertical: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#ff4444',
  },
  rejectBtnText: { color: '#ff4444', fontSize: 12, fontWeight: '700' },
});

const modalStyles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.85)', justifyContent: 'center', padding: 20 },
  container: {
    backgroundColor: '#1a1a2e',
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  title: { color: '#00ff88', fontSize: 12, fontWeight: '900', letterSpacing: 1.5, marginBottom: 12 },
  playerName: { color: '#fff', fontSize: 18, fontWeight: '900', marginBottom: 4 },
  info: { color: '#888', fontSize: 12, marginBottom: 4 },
  budget: { color: '#aaa', fontSize: 12, marginBottom: 12 },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0a0a0f',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#2a2a3e',
    paddingHorizontal: 10,
    marginBottom: 16,
  },
  inputPrefix: { color: '#00ff88', fontSize: 14, fontWeight: '700' },
  input: { flex: 1, color: '#fff', fontSize: 16, paddingVertical: 10, paddingHorizontal: 4 },
  inputSuffix: { color: '#666', fontSize: 14 },
  btnRow: { flexDirection: 'row', gap: 10 },
  cancelBtn: {
    flex: 1,
    backgroundColor: '#2a2a3e',
    borderRadius: 6,
    paddingVertical: 12,
    alignItems: 'center',
  },
  cancelText: { color: '#aaa', fontSize: 13, fontWeight: '700' },
  offerBtn: {
    flex: 2,
    backgroundColor: '#00ff88',
    borderRadius: 6,
    paddingVertical: 12,
    alignItems: 'center',
  },
  offerText: { color: '#0a0a0f', fontSize: 13, fontWeight: '900' },
});
