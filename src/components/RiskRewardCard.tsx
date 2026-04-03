import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ConvergenceResult } from '../analysis/types';

interface Props {
  data: ConvergenceResult;
}

function Row({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={[styles.rowValue, color ? { color } : undefined]}>{value}</Text>
    </View>
  );
}

export function RiskRewardCard({ data }: Props) {
  const { stopLoss, primaryTarget, secondaryTarget, riskRewardRatio, asymmetryScore } = data;
  const price = data.schools[0]?.stopLevel
    ? undefined
    : undefined; // usamos os dados do resultado

  const rrColor =
    riskRewardRatio >= 3 ? '#16A34A' : riskRewardRatio >= 2 ? '#65A30D' : riskRewardRatio >= 1 ? '#CA8A04' : '#DC2626';

  const asym = asymmetryScore;
  const asymColor = asym >= 2 ? '#16A34A' : asym >= 1 ? '#65A30D' : '#CA8A04';
  const asymLabel = asym >= 2 ? 'Excelente' : asym >= 1 ? 'Boa' : 'Marginal';

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Risco / Retorno</Text>

      <View style={styles.rr}>
        <View style={styles.rrBig}>
          <Text style={[styles.rrNum, { color: rrColor }]}>1 : {riskRewardRatio.toFixed(1)}</Text>
          <Text style={styles.rrSub}>Relação R:R</Text>
        </View>
        <View style={styles.rrBig}>
          <Text style={[styles.rrNum, { color: asymColor }]}>{asym.toFixed(1)}</Text>
          <Text style={styles.rrSub}>Assimetria ({asymLabel})</Text>
        </View>
      </View>

      <View style={styles.divider} />

      <Row
        label="Stop Loss"
        value={`R$ ${stopLoss.toFixed(2)}`}
        color="#DC2626"
      />
      <Row
        label="Alvo Primário"
        value={`R$ ${primaryTarget.toFixed(2)}`}
        color="#16A34A"
      />
      {secondaryTarget && (
        <Row
          label="Alvo Secundário"
          value={`R$ ${secondaryTarget.toFixed(2)}`}
          color="#65A30D"
        />
      )}

      <View style={styles.divider} />

      <Text style={styles.disclaimer}>
        ⚠️ Esta análise é meramente informacional e não constitui recomendação de investimento. Resultados passados não garantem resultados futuros. Decisões de investimento são de responsabilidade exclusiva do investidor.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 14,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  rr: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 12,
  },
  rrBig: { alignItems: 'center' },
  rrNum: { fontSize: 26, fontWeight: '800', letterSpacing: -0.5 },
  rrSub: { fontSize: 11, color: '#6B7280', marginTop: 2 },
  divider: { height: 1, backgroundColor: '#F3F4F6', marginVertical: 10 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 5,
  },
  rowLabel: { fontSize: 13, color: '#6B7280' },
  rowValue: { fontSize: 13, fontWeight: '700', color: '#111827' },
  disclaimer: {
    fontSize: 10,
    color: '#9CA3AF',
    lineHeight: 15,
    marginTop: 4,
  },
});
