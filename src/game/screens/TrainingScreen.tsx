// ============================================================
// TrainingScreen — Weekly Training Schedule
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
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types/navigation';
import { useGameStore, selectUserPlayers } from '../store';
import { TrainingFocus, TrainingSchedule } from '../types';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Training'>;
};

const FOCUS_OPTIONS: TrainingFocus[] = [
  'Rest', 'Fitness', 'Tactics', 'Shooting', 'Defending', 'Set Pieces', 'Crossing', 'Passing',
];

const FOCUS_COLORS: Record<TrainingFocus, string> = {
  Rest: '#444',
  Fitness: '#00ff88',
  Tactics: '#0088ff',
  Shooting: '#ff4444',
  Defending: '#ffaa00',
  'Set Pieces': '#aa44ff',
  Crossing: '#ff6600',
  Passing: '#44ffaa',
};

const FOCUS_ICONS: Record<TrainingFocus, string> = {
  Rest: '😴',
  Fitness: '🏃',
  Tactics: '📋',
  Shooting: '⚽',
  Defending: '🛡️',
  'Set Pieces': '🎯',
  Crossing: '🔄',
  Passing: '🎽',
};

const FOCUS_DESC: Record<TrainingFocus, string> = {
  Rest: 'Descanso total. Recupera condição física e previne lesões.',
  Fitness: 'Treino físico intenso. Aumenta condição e resistência.',
  Tactics: 'Estudo tático. Melhora decisão, posicionamento e trabalho em equipe.',
  Shooting: 'Finalização e chutes. Melhora finalização e chutes de longa distância.',
  Defending: 'Treino defensivo. Melhora marcação e tackles.',
  'Set Pieces': 'Bolas paradas. Melhora cobranças de falta e escanteios.',
  Crossing: 'Cruzamentos. Melhora cruzamento e passes laterais.',
  Passing: 'Passes. Melhora passe curto e longo.',
};

const DAYS: (keyof TrainingSchedule)[] = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];
const DAY_PT: Record<keyof TrainingSchedule, string> = {
  monday: 'Segunda',
  tuesday: 'Terça',
  wednesday: 'Quarta',
  thursday: 'Quinta',
  friday: 'Sexta',
};

export default function TrainingScreen({ navigation }: Props) {
  const schedule = useGameStore((s) => s.trainingSchedule);
  const setTraining = useGameStore((s) => s.setTraining);
  const players = useGameStore(selectUserPlayers);

  const [local, setLocal] = useState<TrainingSchedule>({ ...schedule });
  const [expandedDay, setExpandedDay] = useState<keyof TrainingSchedule | null>(null);

  function setDay(day: keyof TrainingSchedule, focus: TrainingFocus) {
    setLocal((prev) => ({ ...prev, [day]: focus }));
    setExpandedDay(null);
  }

  function handleSave() {
    setTraining(local);
    Alert.alert('Treino salvo!', 'O plano de treino da semana foi atualizado.');
    navigation.goBack();
  }

  const avgFitness = players.length > 0
    ? Math.round(players.reduce((s, p) => s + p.fitness, 0) / players.length)
    : 0;
  const avgMorale = players.length > 0
    ? (players.reduce((s, p) => s + p.morale, 0) / players.length).toFixed(1)
    : '0';
  const injured = players.filter((p) => p.condition === 'Injured' || p.condition === 'Carrying Knock').length;

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backBtnText}>← Voltar</Text>
        </TouchableOpacity>
        <Text style={styles.screenTitle}>PLANO DE TREINO</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Squad fitness summary */}
        <View style={styles.summaryCard}>
          <Text style={styles.cardLabel}>RESUMO DO ELENCO</Text>
          <View style={styles.summaryRow}>
            <View style={styles.summaryBlock}>
              <Text style={styles.summaryVal}>{avgFitness}%</Text>
              <Text style={styles.summaryLbl}>Condição média</Text>
            </View>
            <View style={styles.summaryBlock}>
              <Text style={styles.summaryVal}>{avgMorale}/10</Text>
              <Text style={styles.summaryLbl}>Moral média</Text>
            </View>
            <View style={styles.summaryBlock}>
              <Text style={[styles.summaryVal, injured > 0 && { color: '#ff4444' }]}>{injured}</Text>
              <Text style={styles.summaryLbl}>Lesionados</Text>
            </View>
            <View style={styles.summaryBlock}>
              <Text style={styles.summaryVal}>{players.length}</Text>
              <Text style={styles.summaryLbl}>Jogadores</Text>
            </View>
          </View>
        </View>

        {/* Training grid */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>SEMANA DE TREINOS (SEG–SEX)</Text>
          {DAYS.map((day) => {
            const focus = local[day];
            const color = FOCUS_COLORS[focus];
            const isExpanded = expandedDay === day;
            return (
              <View key={day}>
                <TouchableOpacity
                  style={styles.dayRow}
                  onPress={() => setExpandedDay(isExpanded ? null : day)}
                  activeOpacity={0.8}
                >
                  <Text style={styles.dayName}>{DAY_PT[day]}</Text>
                  <View style={[styles.focusBadge, { backgroundColor: color + '22', borderColor: color }]}>
                    <Text style={styles.focusIcon}>{FOCUS_ICONS[focus]}</Text>
                    <Text style={[styles.focusText, { color }]}>{focus}</Text>
                  </View>
                  <Text style={styles.chevron}>{isExpanded ? '▼' : '▶'}</Text>
                </TouchableOpacity>

                {isExpanded && (
                  <View style={styles.expandPanel}>
                    <Text style={styles.expandDesc}>{FOCUS_DESC[focus]}</Text>
                    <View style={styles.optionsGrid}>
                      {FOCUS_OPTIONS.map((opt) => (
                        <TouchableOpacity
                          key={opt}
                          style={[
                            styles.optBtn,
                            focus === opt && { backgroundColor: FOCUS_COLORS[opt] + '22', borderColor: FOCUS_COLORS[opt] },
                          ]}
                          onPress={() => setDay(day, opt)}
                        >
                          <Text style={styles.optIcon}>{FOCUS_ICONS[opt]}</Text>
                          <Text style={[styles.optText, focus === opt && { color: FOCUS_COLORS[opt] }]}>{opt}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                )}
              </View>
            );
          })}
        </View>

        {/* Legend */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>EFEITOS DO TREINO</Text>
          {FOCUS_OPTIONS.map((opt) => (
            <View key={opt} style={styles.legendRow}>
              <Text style={styles.legendIcon}>{FOCUS_ICONS[opt]}</Text>
              <Text style={[styles.legendName, { color: FOCUS_COLORS[opt] }]}>{opt}</Text>
              <Text style={styles.legendDesc}>{FOCUS_DESC[opt]}</Text>
            </View>
          ))}
        </View>

        <TouchableOpacity style={styles.saveBtn} onPress={handleSave}>
          <Text style={styles.saveBtnText}>💾 SALVAR TREINO</Text>
        </TouchableOpacity>
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
  card: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  summaryCard: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  cardLabel: { color: '#666', fontSize: 9, fontWeight: '700', letterSpacing: 1.5, marginBottom: 10 },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-around' },
  summaryBlock: { alignItems: 'center' },
  summaryVal: { color: '#00ff88', fontSize: 22, fontWeight: '900' },
  summaryLbl: { color: '#555', fontSize: 9, marginTop: 2 },
  dayRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a3e',
    gap: 10,
  },
  dayName: { color: '#ddd', fontSize: 13, fontWeight: '700', width: 64 },
  focusBadge: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderWidth: 1,
    gap: 6,
  },
  focusIcon: { fontSize: 14 },
  focusText: { fontSize: 12, fontWeight: '700' },
  chevron: { color: '#555', fontSize: 10 },
  expandPanel: {
    backgroundColor: '#111',
    padding: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a3e',
  },
  expandDesc: { color: '#888', fontSize: 11, marginBottom: 10, lineHeight: 16 },
  optionsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  optBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: '#2a2a3e',
    backgroundColor: '#1a1a2e',
    gap: 4,
  },
  optIcon: { fontSize: 12 },
  optText: { color: '#888', fontSize: 11, fontWeight: '600' },
  legendRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 8,
    gap: 8,
  },
  legendIcon: { fontSize: 14, width: 20 },
  legendName: { fontSize: 11, fontWeight: '700', width: 72 },
  legendDesc: { color: '#666', fontSize: 10, flex: 1, lineHeight: 14 },
  saveBtn: {
    backgroundColor: '#00ff88',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
  },
  saveBtnText: { color: '#0a0a0f', fontSize: 14, fontWeight: '900', letterSpacing: 1 },
});
