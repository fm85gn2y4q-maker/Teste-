import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useStore } from '../store/useStore';
import { COLORS } from '../theme';
import { formatBRL } from '../utils/format';

function Stepper({
  value,
  onChange,
  step,
  min,
  max,
  format,
}: {
  value: number;
  onChange: (value: number) => void;
  step: number;
  min: number;
  max: number;
  format: (value: number) => string;
}) {
  return (
    <View style={styles.stepper}>
      <Pressable
        style={[styles.stepButton, value <= min && styles.stepButtonDisabled]}
        onPress={() => onChange(Math.max(min, value - step))}
      >
        <Text style={styles.stepButtonText}>−</Text>
      </Pressable>
      <Text style={styles.stepValue}>{format(value)}</Text>
      <Pressable
        style={[styles.stepButton, value >= max && styles.stepButtonDisabled]}
        onPress={() => onChange(Math.min(max, value + step))}
      >
        <Text style={styles.stepButtonText}>+</Text>
      </Pressable>
    </View>
  );
}

export function SettingsScreen() {
  const { maxStops, extraStopCost, setMaxStops, setExtraStopCost } = useStore();

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Configurações do plano</Text>
        <Text style={styles.subtitle}>Ajuste como o plano inteligente é calculado</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Máximo de mercados por plano</Text>
          <Text style={styles.cardHint}>
            Quantos mercados diferentes você aceita visitar em uma mesma compra.
          </Text>
          <Stepper
            value={maxStops}
            onChange={setMaxStops}
            step={1}
            min={1}
            max={4}
            format={(v) => `${v} ${v === 1 ? 'mercado' : 'mercados'}`}
          />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Custo de deslocamento</Text>
          <Text style={styles.cardHint}>
            Custo estimado (combustível/tempo) por mercado adicional visitado. O plano só divide a
            compra quando a economia supera esse custo.
          </Text>
          <Stepper
            value={extraStopCost}
            onChange={setExtraStopCost}
            step={2}
            min={0}
            max={40}
            format={formatBRL}
          />
        </View>

        <View style={styles.aboutCard}>
          <Text style={styles.aboutTitle}>Como funciona</Text>
          <Text style={styles.aboutText}>
            O app compara sua lista em todos os mercados da região escolhida, aplicando as
            promoções de cada um. Depois testa todas as combinações de mercados (até o limite
            configurado) e atribui cada item ao mercado mais barato, descontando o custo de
            deslocamento — assim ele só recomenda dividir a compra quando realmente compensa.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.bg },
  header: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 16,
    backgroundColor: COLORS.primary,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
  },
  title: { fontSize: 22, fontWeight: '800', color: '#fff' },
  subtitle: { fontSize: 13, color: '#DCFCE7', marginTop: 4 },
  content: { padding: 20 },
  card: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 18,
    marginBottom: 14,
  },
  cardTitle: { fontSize: 16, fontWeight: '800', color: COLORS.text },
  cardHint: { fontSize: 13, color: COLORS.textMuted, marginTop: 4, lineHeight: 19 },
  stepper: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 14,
    backgroundColor: COLORS.bg,
    borderRadius: 12,
    padding: 8,
  },
  stepButton: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: COLORS.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepButtonDisabled: { opacity: 0.35 },
  stepButtonText: { fontSize: 22, fontWeight: '800', color: COLORS.primaryDark },
  stepValue: { fontSize: 17, fontWeight: '800', color: COLORS.text },
  aboutCard: {
    backgroundColor: '#EFF6FF',
    borderRadius: 16,
    padding: 18,
  },
  aboutTitle: { fontSize: 15, fontWeight: '800', color: COLORS.info, marginBottom: 6 },
  aboutText: { fontSize: 13, color: '#1E3A8A', lineHeight: 20 },
});
