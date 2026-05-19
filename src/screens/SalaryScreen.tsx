import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { fetchSalariosServidor, SalarioServidor } from '../api/mesquita';

const NOME_SERVIDOR = 'Aline Tavares Neves';
const ANO_ATUAL = new Date().getFullYear();

function formatBRL(value: string): string {
  const num = parseFloat(value);
  if (isNaN(num)) return 'R$ --';
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatDate(value: string): string {
  if (!value) return '--';
  const d = new Date(value);
  if (isNaN(d.getTime())) return value;
  return d.toLocaleDateString('pt-BR');
}

function SalarioCard({ item }: { item: SalarioServidor }) {
  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.mesAno}>
          {item.MES}/{item.ANO}
        </Text>
        <Text style={styles.secretaria} numberOfLines={1}>
          {item.SECRETARIA}
        </Text>
      </View>

      <View style={styles.row}>
        <LabelValue label="Cargo" value={item.CARGO} />
        <LabelValue label="Regime" value={item.DESCRICAO_REGIME} />
      </View>

      <View style={styles.divider} />

      <View style={styles.row}>
        <LabelValue label="Base Salarial" value={formatBRL(item.BASE_SALARIAL)} accent />
        <LabelValue label="Bruto" value={formatBRL(item.BRUTO)} accent />
        <LabelValue label="Líquido" value={formatBRL(item.LIQUIDO)} accent />
      </View>

      <View style={styles.divider} />

      <View style={styles.row}>
        <LabelValue label="IR" value={formatBRL(item.IMPOSTODERENDA)} />
        <LabelValue label="Prev." value={formatBRL(item.Desconto_Previdenciario)} />
        <LabelValue label="Outros Desc." value={formatBRL(item.Outros_descontos)} />
      </View>

      <View style={styles.divider} />

      <View style={styles.row}>
        <LabelValue label="Admissão" value={formatDate(item.DATA_ADMISSAO)} />
        <LabelValue label="Concursado" value={item.Concursado} />
        <LabelValue label="Fonte" value={item.FONTE_RECURSOS} />
      </View>
    </View>
  );
}

function LabelValue({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <View style={styles.labelValue}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, accent && styles.accentValue]}>{value}</Text>
    </View>
  );
}

export function SalaryScreen() {
  const [ano, setAno] = useState(ANO_ATUAL);
  const [data, setData] = useState<SalarioServidor[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (year: number) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchSalariosServidor(NOME_SERVIDOR, year);
      if (result.length === 0) {
        setError(`Nenhum registro encontrado para ${year}.`);
      }
      setData(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erro ao buscar dados.');
      setData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(ano);
  }, [ano, load]);

  const sorted = [...data].sort((a, b) => {
    if (a.ANO !== b.ANO) return parseInt(b.ANO) - parseInt(a.ANO);
    return parseInt(b.MES) - parseInt(a.MES);
  });

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Remuneração</Text>
        <Text style={styles.subtitle}>{NOME_SERVIDOR}</Text>
        <View style={styles.yearSelector}>
          <TouchableOpacity
            onPress={() => setAno((y) => y - 1)}
            style={styles.yearBtn}
            disabled={loading}
          >
            <Text style={styles.yearBtnText}>{'‹'}</Text>
          </TouchableOpacity>
          <Text style={styles.yearText}>{ano}</Text>
          <TouchableOpacity
            onPress={() => setAno((y) => y + 1)}
            style={styles.yearBtn}
            disabled={loading || ano >= ANO_ATUAL}
          >
            <Text style={[styles.yearBtnText, ano >= ANO_ATUAL && styles.disabledBtn]}>
              {'›'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#6C3DE8" style={{ marginTop: 40 }} />
      ) : error ? (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity onPress={() => load(ano)} style={styles.retryBtn}>
            <Text style={styles.retryText}>Tentar novamente</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={loading}
              onRefresh={() => load(ano)}
              tintColor="#6C3DE8"
            />
          }
        >
          {sorted.map((item, i) => (
            <SalarioCard key={`${item.ANO}-${item.MES}-${i}`} item={item} />
          ))}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8F9FB' },
  header: {
    backgroundColor: '#6C3DE8',
    paddingTop: 56,
    paddingBottom: 20,
    paddingHorizontal: 20,
  },
  title: { color: '#fff', fontSize: 22, fontWeight: '700' },
  subtitle: { color: 'rgba(255,255,255,0.85)', fontSize: 13, marginTop: 2 },
  yearSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 24,
    paddingHorizontal: 4,
  },
  yearBtn: { paddingHorizontal: 16, paddingVertical: 6 },
  yearBtnText: { color: '#fff', fontSize: 22, fontWeight: '300' },
  disabledBtn: { opacity: 0.3 },
  yearText: { color: '#fff', fontSize: 16, fontWeight: '600', minWidth: 44, textAlign: 'center' },
  list: { padding: 16, gap: 12 },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  mesAno: { fontSize: 15, fontWeight: '700', color: '#6C3DE8' },
  secretaria: { fontSize: 11, color: '#6B7280', maxWidth: '60%', textAlign: 'right' },
  row: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  divider: { height: 1, backgroundColor: '#F3F4F6', marginVertical: 10 },
  labelValue: { flex: 1, minWidth: 80 },
  label: { fontSize: 10, color: '#9CA3AF', marginBottom: 2, textTransform: 'uppercase' },
  value: { fontSize: 13, color: '#111827', fontWeight: '500' },
  accentValue: { color: '#6C3DE8', fontWeight: '700' },
  errorContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  errorText: { color: '#EF4444', textAlign: 'center', marginBottom: 16, fontSize: 14 },
  retryBtn: {
    backgroundColor: '#6C3DE8',
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 8,
  },
  retryText: { color: '#fff', fontWeight: '600' },
});
