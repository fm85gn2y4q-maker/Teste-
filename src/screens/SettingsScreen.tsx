import React, { useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useStore } from '../store/useStore';

const PURPLE = '#6C3DE8';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.sectionBody}>{children}</View>
    </View>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

export function SettingsScreen() {
  const { apiToken, setApiToken, watchlist, refreshAll } = useStore();
  const [tokenInput, setTokenInput] = useState(apiToken);

  const saveToken = () => {
    setApiToken(tokenInput.trim());
    Alert.alert('Token salvo', 'Recarregando dados com o novo token…', [
      { text: 'OK', onPress: () => refreshAll() },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Configurações</Text>
      </View>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={styles.content}>

          <Section title="API de Dados (Brapi)">
            <Text style={styles.helpText}>
              O app usa a Brapi (brapi.dev) para dados da B3. Sem token, as requisições são limitadas. Crie uma conta grátis ou Pro para obter seu token.
            </Text>
            <TextInput
              style={styles.tokenInput}
              value={tokenInput}
              onChangeText={setTokenInput}
              placeholder="Cole seu token Brapi aqui..."
              placeholderTextColor="#9CA3AF"
              autoCapitalize="none"
              autoCorrect={false}
              secureTextEntry
            />
            <TouchableOpacity style={styles.saveBtn} onPress={saveToken}>
              <Text style={styles.saveBtnText}>Salvar e Recarregar</Text>
            </TouchableOpacity>
          </Section>

          <Section title="Análise Técnica">
            <InfoRow label="Escolas ativas" value="Indicadores · Candlestick · Price Action" />
            <InfoRow label="Timeframe padrão" value="Diário (6 meses)" />
            <InfoRow label="Score de convergência" value="Média ponderada (-100 a +100)" />
            <InfoRow label="Pesos" value="Indicadores 40% · Candle 30% · PA 30%" />
          </Section>

          <Section title="Sobre o Scoring">
            <View style={styles.scoreGuide}>
              {[
                { range: '+60 a +100', label: 'Forte Alta', color: '#16A34A' },
                { range: '+30 a +59', label: 'Alta Moderada', color: '#65A30D' },
                { range: '-29 a +29', label: 'Neutro', color: '#CA8A04' },
                { range: '-59 a -30', label: 'Baixa Moderada', color: '#EA580C' },
                { range: '-100 a -60', label: 'Forte Baixa', color: '#DC2626' },
              ].map((g) => (
                <View key={g.range} style={styles.guideRow}>
                  <View style={[styles.guideColor, { backgroundColor: g.color }]} />
                  <Text style={styles.guideRange}>{g.range}</Text>
                  <Text style={[styles.guideLabel, { color: g.color }]}>{g.label}</Text>
                </View>
              ))}
            </View>
          </Section>

          <Section title="Watchlist">
            <InfoRow label="Ativos monitorados" value={String(watchlist.length)} />
            <InfoRow label="Dados em tempo real" value="Não (atualização manual)" />
            <InfoRow label="Delay" value="Fim do pregão (EOD)" />
            <TouchableOpacity
              style={[styles.saveBtn, { backgroundColor: '#F3F4F6' }]}
              onPress={() => refreshAll()}
            >
              <Text style={[styles.saveBtnText, { color: PURPLE }]}>Atualizar todos os ativos</Text>
            </TouchableOpacity>
          </Section>

          <View style={styles.disclaimerBox}>
            <Text style={styles.disclaimerTitle}>⚠️ Aviso Legal</Text>
            <Text style={styles.disclaimerText}>
              Este aplicativo é uma ferramenta de visualização e análise técnica para fins educacionais e informativos. Não constitui recomendação de investimento, análise de valores mobiliários ou consultoria financeira. As métricas apresentadas não devem ser utilizadas isoladamente para decisões de investimento. Resultados passados não garantem resultados futuros. Invista com responsabilidade.
            </Text>
          </View>

          <Text style={styles.version}>Grafista B3 · MVP v1.0 · Expo React Native</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#F9FAFB' },
  header: {
    backgroundColor: PURPLE,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  headerTitle: { fontSize: 20, fontWeight: '800', color: '#fff' },
  content: { padding: 16, paddingBottom: 40 },

  section: { marginBottom: 16 },
  sectionTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: '#9CA3AF',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 8,
    marginLeft: 4,
  },
  sectionBody: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 14,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  helpText: { fontSize: 13, color: '#6B7280', lineHeight: 20, marginBottom: 12 },
  tokenInput: {
    height: 44,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 10,
    paddingHorizontal: 12,
    fontSize: 14,
    color: '#111827',
    marginBottom: 10,
  },
  saveBtn: {
    backgroundColor: PURPLE,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
  },
  saveBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },

  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  infoLabel: { fontSize: 13, color: '#6B7280' },
  infoValue: { fontSize: 13, color: '#374151', fontWeight: '500', flex: 1, textAlign: 'right' },

  scoreGuide: { gap: 6 },
  guideRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 3 },
  guideColor: { width: 10, height: 10, borderRadius: 5, marginRight: 10 },
  guideRange: { width: 100, fontSize: 12, color: '#6B7280' },
  guideLabel: { fontSize: 12, fontWeight: '700' },

  disclaimerBox: {
    backgroundColor: '#FEF9C3',
    borderRadius: 14,
    padding: 14,
    marginBottom: 16,
    borderLeftWidth: 3,
    borderLeftColor: '#CA8A04',
  },
  disclaimerTitle: { fontSize: 13, fontWeight: '700', color: '#92400E', marginBottom: 6 },
  disclaimerText: { fontSize: 12, color: '#78350F', lineHeight: 18 },
  version: { fontSize: 11, color: '#D1D5DB', textAlign: 'center' },
});
