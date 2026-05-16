// ============================================================
// TacticsScreen — Tactics Editor
// ============================================================
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  Alert,
} from 'react-native';
import { useGameStore, selectUserPlayers, selectUserClub } from '../store';
import { Formation, Tactic, TacticInstruction, Player } from '../types';
import { generateId } from '../database';

const FORMATIONS: Formation[] = ['4-4-2', '4-3-3', '4-5-1', '3-5-2', '5-3-2'];

// Pitch positions for each formation [x%, y%] (0,0 = top-left, goal at bottom)
const FORMATION_POSITIONS: Record<Formation, [number, number][]> = {
  '4-4-2': [
    [50, 90], // GK
    [20, 72], [38, 72], [62, 72], [80, 72], // DEF
    [20, 50], [38, 50], [62, 50], [80, 50], // MID
    [35, 28], [65, 28], // FWD
  ],
  '4-3-3': [
    [50, 90],
    [20, 72], [38, 72], [62, 72], [80, 72],
    [30, 50], [50, 50], [70, 50],
    [20, 28], [50, 28], [80, 28],
  ],
  '4-5-1': [
    [50, 90],
    [20, 72], [38, 72], [62, 72], [80, 72],
    [12, 50], [30, 50], [50, 50], [70, 50], [88, 50],
    [50, 25],
  ],
  '3-5-2': [
    [50, 90],
    [30, 72], [50, 72], [70, 72],
    [12, 52], [32, 50], [50, 48], [68, 50], [88, 52],
    [35, 28], [65, 28],
  ],
  '5-3-2': [
    [50, 90],
    [12, 72], [30, 72], [50, 72], [70, 72], [88, 72],
    [30, 50], [50, 50], [70, 50],
    [35, 28], [65, 28],
  ],
};

const POSITION_LABELS = [
  'GK', 'LD', 'DC', 'DC', 'LE', 'MC', 'MC', 'MC', 'MC', 'ATA', 'ATA',
];

type MentalityType = TacticInstruction['mentality'];
type TempoType = TacticInstruction['tempo'];
type PassStyleType = TacticInstruction['passingStyle'];
type PressingType = TacticInstruction['pressing'];
type WidthType = TacticInstruction['width'];
type FocusType = TacticInstruction['focus'];

function OptionPicker<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: T[];
  onChange: (v: T) => void;
}) {
  return (
    <View style={styles.pickerBlock}>
      <Text style={styles.pickerLabel}>{label}</Text>
      <View style={styles.pickerRow}>
        {options.map((opt) => (
          <TouchableOpacity
            key={opt}
            style={[styles.pill, value === opt && styles.pillActive]}
            onPress={() => onChange(opt)}
          >
            <Text style={[styles.pillText, value === opt && styles.pillTextActive]}>{opt}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

export default function TacticsScreen() {
  const userClub = useGameStore(selectUserClub);
  const players = useGameStore(selectUserPlayers);
  const setTactic = useGameStore((s) => s.setTactic);

  const initTactic = userClub?.tactics;

  const [formation, setFormation] = useState<Formation>(initTactic?.formation ?? '4-4-2');
  const [instructions, setInstructions] = useState<TacticInstruction>(
    initTactic?.instructions ?? {
      mentality: 'Normal', tempo: 'Normal', passingStyle: 'Mixed',
      pressing: 'Medium', width: 'Normal', focus: 'Mixed',
      cornerRoutine: 'Far Post', freeKickRoutine: 'Cross',
    }
  );
  const [lineupIds, setLineupIds] = useState<string[]>(
    initTactic ? Object.values(initTactic.lineup).slice(0, 11) : players.slice(0, 11).map((p) => p.id)
  );
  const [substitutes, setSubstitutes] = useState<string[]>(
    initTactic?.substitutes ?? players.slice(11, 18).map((p) => p.id)
  );

  useEffect(() => {
    if (initTactic) {
      setFormation(initTactic.formation);
      setInstructions(initTactic.instructions);
      const l = Object.values(initTactic.lineup).slice(0, 11);
      setLineupIds(l.length > 0 ? l : players.slice(0, 11).map((p) => p.id));
      setSubstitutes(initTactic.substitutes);
    }
  }, []);

  function updateInstruction<K extends keyof TacticInstruction>(key: K, val: TacticInstruction[K]) {
    setInstructions((prev) => ({ ...prev, [key]: val }));
  }

  function moveUp(idx: number) {
    if (idx <= 1) return; // GK stays
    const arr = [...lineupIds];
    [arr[idx], arr[idx - 1]] = [arr[idx - 1], arr[idx]];
    setLineupIds(arr);
  }

  function moveDown(idx: number) {
    if (idx === 0 || idx >= lineupIds.length - 1) return;
    const arr = [...lineupIds];
    [arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]];
    setLineupIds(arr);
  }

  function getPlayer(id: string): Player | undefined {
    return players.find((p) => p.id === id);
  }

  function handleSave() {
    if (!userClub) return;
    const lineupObj: { [pos: string]: string } = {};
    lineupIds.slice(0, 11).forEach((id, i) => {
      lineupObj[`slot_${i}`] = id;
    });
    const tactic: Tactic = {
      id: initTactic?.id ?? generateId('tac'),
      name: `${formation} Normal`,
      formation,
      instructions,
      lineup: lineupObj,
      substitutes: substitutes.slice(0, 7),
    };
    setTactic(tactic);
    Alert.alert('Tático salvo!', 'Sua tática foi salva com sucesso.');
  }

  const pitchPositions = FORMATION_POSITIONS[formation] ?? FORMATION_POSITIONS['4-4-2'];

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.screenTitle}>TÁTICAS</Text>

        {/* Formation picker */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>FORMAÇÃO</Text>
          <View style={styles.pillRow}>
            {FORMATIONS.map((f) => (
              <TouchableOpacity
                key={f}
                style={[styles.pill, formation === f && styles.pillActive]}
                onPress={() => setFormation(f)}
              >
                <Text style={[styles.pillText, formation === f && styles.pillTextActive]}>{f}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Pitch visualization */}
        <View style={styles.pitchContainer}>
          <View style={styles.pitch}>
            {/* Pitch markings */}
            <View style={styles.pitchHalfLine} />
            <View style={styles.pitchCenter} />
            {/* Players */}
            {pitchPositions.map((pos, idx) => {
              const playerId = lineupIds[idx];
              const player = playerId ? getPlayer(playerId) : undefined;
              const label = player ? player.name.split(' ').pop() ?? player.name : POSITION_LABELS[idx] ?? '?';
              return (
                <View
                  key={idx}
                  style={[
                    styles.playerDot,
                    {
                      left: `${pos[0]}%`,
                      top: `${pos[1]}%`,
                      transform: [{ translateX: -24 }, { translateY: -16 }],
                    },
                  ]}
                >
                  <View style={styles.playerDotCircle}>
                    <Text style={styles.playerDotNum}>{idx + 1}</Text>
                  </View>
                  <Text style={styles.playerDotName} numberOfLines={1}>{label}</Text>
                </View>
              );
            })}
          </View>
        </View>

        {/* Instructions */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>INSTRUÇÕES</Text>
          <OptionPicker
            label="Mentalidade"
            value={instructions.mentality}
            options={['Defensive', 'Normal', 'Attacking', 'Overloading']}
            onChange={(v) => updateInstruction('mentality', v as MentalityType)}
          />
          <OptionPicker
            label="Ritmo"
            value={instructions.tempo}
            options={['Slow', 'Normal', 'Fast']}
            onChange={(v) => updateInstruction('tempo', v as TempoType)}
          />
          <OptionPicker
            label="Estilo de Passe"
            value={instructions.passingStyle}
            options={['Short', 'Mixed', 'Long']}
            onChange={(v) => updateInstruction('passingStyle', v as PassStyleType)}
          />
          <OptionPicker
            label="Pressão"
            value={instructions.pressing}
            options={['Low', 'Medium', 'High']}
            onChange={(v) => updateInstruction('pressing', v as PressingType)}
          />
          <OptionPicker
            label="Largura"
            value={instructions.width}
            options={['Narrow', 'Normal', 'Wide']}
            onChange={(v) => updateInstruction('width', v as WidthType)}
          />
          <OptionPicker
            label="Foco"
            value={instructions.focus}
            options={['Left', 'Centre', 'Right', 'Mixed']}
            onChange={(v) => updateInstruction('focus', v as FocusType)}
          />
        </View>

        {/* Starting XI */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>ESCALAÇÃO (XI)</Text>
          {lineupIds.slice(0, 11).map((playerId, idx) => {
            const player = getPlayer(playerId);
            return (
              <View key={idx} style={styles.lineupRow}>
                <Text style={styles.lineupNum}>{idx + 1}</Text>
                <Text style={styles.lineupPos}>{POSITION_LABELS[idx] ?? '—'}</Text>
                <Text style={styles.lineupName} numberOfLines={1}>{player?.name ?? 'Vago'}</Text>
                <Text style={styles.lineupRating}>{player?.currentRating.toFixed(1) ?? '—'}</Text>
                <View style={styles.arrowBtns}>
                  <TouchableOpacity style={styles.arrowBtn} onPress={() => moveUp(idx)}>
                    <Text style={styles.arrowText}>▲</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.arrowBtn} onPress={() => moveDown(idx)}>
                    <Text style={styles.arrowText}>▼</Text>
                  </TouchableOpacity>
                </View>
              </View>
            );
          })}
        </View>

        {/* Bench */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>RESERVAS (7)</Text>
          {substitutes.slice(0, 7).map((playerId, idx) => {
            const player = getPlayer(playerId);
            return (
              <View key={idx} style={styles.lineupRow}>
                <Text style={styles.lineupNum}>{idx + 12}</Text>
                <Text style={styles.lineupPos}>{player?.position ?? '—'}</Text>
                <Text style={styles.lineupName} numberOfLines={1}>{player?.name ?? 'Vago'}</Text>
                <Text style={styles.lineupRating}>{player?.currentRating.toFixed(1) ?? '—'}</Text>
              </View>
            );
          })}
        </View>

        <TouchableOpacity style={styles.saveBtn} onPress={handleSave}>
          <Text style={styles.saveBtnText}>💾 SALVAR TÁTICA</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0a0a0f' },
  scroll: { padding: 12, paddingBottom: 32 },
  screenTitle: { color: '#00ff88', fontSize: 16, fontWeight: '900', letterSpacing: 1.5, marginBottom: 12 },
  card: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  cardLabel: { color: '#666', fontSize: 9, fontWeight: '700', letterSpacing: 1.5, marginBottom: 10 },
  pillRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  pill: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: '#2a2a3e',
    borderWidth: 1,
    borderColor: '#3a3a4e',
  },
  pillActive: { backgroundColor: '#0a2a1a', borderColor: '#00ff88' },
  pillText: { color: '#666', fontSize: 11, fontWeight: '700' },
  pillTextActive: { color: '#00ff88' },
  pitchContainer: {
    height: 300,
    marginBottom: 10,
    backgroundColor: '#1a3a1a',
    borderRadius: 8,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#2a5a2a',
  },
  pitch: {
    flex: 1,
    position: 'relative',
  },
  pitchHalfLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: '50%',
    height: 1,
    backgroundColor: 'rgba(255,255,255,0.3)',
  },
  pitchCenter: {
    position: 'absolute',
    width: 60,
    height: 60,
    borderRadius: 30,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.3)',
    left: '50%',
    top: '50%',
    transform: [{ translateX: -30 }, { translateY: -30 }],
  },
  playerDot: {
    position: 'absolute',
    alignItems: 'center',
    width: 48,
  },
  playerDotCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#00ff88',
    alignItems: 'center',
    justifyContent: 'center',
  },
  playerDotNum: { color: '#0a0a0f', fontSize: 11, fontWeight: '900' },
  playerDotName: { color: '#fff', fontSize: 8, fontWeight: '600', marginTop: 2, textAlign: 'center', width: 48 },
  pickerBlock: { marginBottom: 12 },
  pickerLabel: { color: '#888', fontSize: 10, fontWeight: '700', marginBottom: 6 },
  pickerRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  lineupRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a3e',
    gap: 8,
  },
  lineupNum: { color: '#555', fontSize: 11, width: 20, textAlign: 'center', fontVariant: ['tabular-nums'] },
  lineupPos: { color: '#00ff88', fontSize: 10, fontWeight: '700', width: 32 },
  lineupName: { color: '#ddd', fontSize: 12, flex: 1 },
  lineupRating: { color: '#aaa', fontSize: 11, fontVariant: ['tabular-nums'], width: 28, textAlign: 'right' },
  arrowBtns: { flexDirection: 'row', gap: 4 },
  arrowBtn: {
    backgroundColor: '#2a2a3e',
    borderRadius: 4,
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  arrowText: { color: '#aaa', fontSize: 10 },
  saveBtn: {
    backgroundColor: '#00ff88',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 6,
  },
  saveBtnText: { color: '#0a0a0f', fontSize: 14, fontWeight: '900', letterSpacing: 1 },
});
