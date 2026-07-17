import React, { useMemo, useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { CompositeScreenProps } from '@react-navigation/native';
import { BottomTabScreenProps } from '@react-navigation/bottom-tabs';

import { CATALOG, getProduct } from '../data/catalog';
import { BAIRROS, getBairro } from '../data/bairros';
import { marketsNear } from '../data/markets';
import { parseShoppingList } from '../engine/parseList';
import { useStore } from '../store/useStore';
import { COLORS } from '../theme';
import { MainTabParamList, RootStackParamList } from '../types/navigation';

type Props = CompositeScreenProps<
  BottomTabScreenProps<MainTabParamList, 'Lista'>,
  NativeStackScreenProps<RootStackParamList>
>;

export function HomeScreen({ navigation }: Props) {
  const { bairroId, items, costPerKm, setBairro, addItem, removeItem, setQuantity, mergeItems, clearList } =
    useStore();
  const [search, setSearch] = useState('');
  const [pasteVisible, setPasteVisible] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [pasteFeedback, setPasteFeedback] = useState<string | null>(null);

  const suggestions = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return [];
    return CATALOG.filter((p) =>
      [p.name, ...(p.aliases ?? [])].some((n) => n.toLowerCase().includes(q)),
    ).slice(0, 6);
  }, [search]);

  const bairro = getBairro(bairroId);
  const nearby = marketsNear(bairroId, costPerKm);
  const neighborNames = bairro.adjacent.map((a) => getBairro(a.bairroId).name).join(', ');

  function handlePaste() {
    const { items: parsed, unmatched } = parseShoppingList(pasteText);
    mergeItems(parsed);
    setPasteText('');
    setPasteVisible(false);
    setPasteFeedback(
      unmatched.length === 0
        ? `${parsed.length} item(ns) adicionados à lista.`
        : `${parsed.length} item(ns) adicionados. Não encontrei: ${unmatched.join(', ')}.`,
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Feira Esperta · Rio</Text>
        <Text style={styles.subtitle}>
          Compare os supermercados perto de você e monte o plano de compra com melhor custo-benefício
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={styles.sectionLabel}>Seu bairro</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.regionRow}>
          {BAIRROS.map((b) => {
            const active = b.id === bairroId;
            return (
              <Pressable
                key={b.id}
                onPress={() => setBairro(b.id)}
                style={[styles.regionChip, active && styles.regionChipActive]}
              >
                <Text style={[styles.regionChipText, active && styles.regionChipTextActive]}>
                  {b.name}
                </Text>
                <Text style={[styles.regionChipZone, active && styles.regionChipTextActive]}>
                  {b.zone}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>
        <Text style={styles.regionInfo}>
          {nearby.length} mercados perto de você — em {bairro.name} e vizinhos ({neighborNames})
        </Text>

        <Text style={styles.sectionLabel}>Monte sua lista</Text>
        <View style={styles.searchRow}>
          <TextInput
            style={styles.searchInput}
            placeholder="Buscar produto (ex.: arroz, leite...)"
            placeholderTextColor={COLORS.textMuted}
            value={search}
            onChangeText={setSearch}
          />
          <Pressable style={styles.pasteButton} onPress={() => setPasteVisible(true)}>
            <Text style={styles.pasteButtonText}>Colar lista</Text>
          </Pressable>
        </View>

        {suggestions.map((product) => (
          <Pressable
            key={product.id}
            style={styles.suggestion}
            onPress={() => {
              addItem(product.id);
              setSearch('');
            }}
          >
            <View style={{ flex: 1 }}>
              <Text style={styles.suggestionName}>{product.name}</Text>
              <Text style={styles.suggestionMeta}>{product.category}</Text>
            </View>
            <Text style={styles.suggestionAdd}>+ adicionar</Text>
          </Pressable>
        ))}

        {pasteFeedback && <Text style={styles.pasteFeedback}>{pasteFeedback}</Text>}

        <View style={styles.listHeader}>
          <Text style={styles.sectionLabel}>
            Lista de compras ({items.length} {items.length === 1 ? 'item' : 'itens'})
          </Text>
          {items.length > 0 && (
            <Pressable onPress={clearList}>
              <Text style={styles.clearText}>Limpar</Text>
            </Pressable>
          )}
        </View>

        {items.length === 0 ? (
          <View style={styles.emptyBox}>
            <Text style={styles.emptyEmoji}>🛒</Text>
            <Text style={styles.emptyText}>
              Sua lista está vazia. Busque produtos acima ou cole sua lista pronta.
            </Text>
          </View>
        ) : (
          items.map((item) => {
            const product = getProduct(item.productId);
            return (
              <View key={item.productId} style={styles.itemRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.itemName}>{product.name}</Text>
                  <Text style={styles.itemMeta}>{product.category}</Text>
                </View>
                <View style={styles.qtyControls}>
                  <Pressable
                    style={styles.qtyButton}
                    onPress={() => setQuantity(item.productId, item.quantity - 1)}
                  >
                    <Text style={styles.qtyButtonText}>−</Text>
                  </Pressable>
                  <Text style={styles.qtyValue}>{item.quantity}</Text>
                  <Pressable
                    style={styles.qtyButton}
                    onPress={() => setQuantity(item.productId, item.quantity + 1)}
                  >
                    <Text style={styles.qtyButtonText}>+</Text>
                  </Pressable>
                </View>
                <Pressable onPress={() => removeItem(item.productId)} style={styles.removeButton}>
                  <Text style={styles.removeButtonText}>✕</Text>
                </Pressable>
              </View>
            );
          })
        )}

        <View style={{ height: 96 }} />
      </ScrollView>

      {items.length > 0 && (
        <View style={styles.footer}>
          <Pressable style={styles.cta} onPress={() => navigation.navigate('Results')}>
            <Text style={styles.ctaText}>Calcular melhor plano de compra</Text>
          </Pressable>
        </View>
      )}

      <Modal visible={pasteVisible} animationType="slide" transparent>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.modalBackdrop}
        >
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Colar lista de compras</Text>
            <Text style={styles.modalHint}>
              Um item por linha. Aceita quantidades: “2 arroz”, “leite x3”, “café”.
            </Text>
            <TextInput
              style={styles.modalInput}
              multiline
              placeholder={'2 arroz\nfeijão\nleite x3\npapel higiênico'}
              placeholderTextColor={COLORS.textMuted}
              value={pasteText}
              onChangeText={setPasteText}
            />
            <View style={styles.modalActions}>
              <Pressable
                style={[styles.modalButton, styles.modalCancel]}
                onPress={() => setPasteVisible(false)}
              >
                <Text style={styles.modalCancelText}>Cancelar</Text>
              </Pressable>
              <Pressable style={[styles.modalButton, styles.modalConfirm]} onPress={handlePaste}>
                <Text style={styles.modalConfirmText}>Adicionar itens</Text>
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
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
  title: { fontSize: 26, fontWeight: '800', color: '#fff' },
  subtitle: { fontSize: 13, color: '#DCFCE7', marginTop: 4, lineHeight: 18 },
  content: { padding: 20 },
  sectionLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: COLORS.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
    marginTop: 8,
  },
  regionRow: { marginBottom: 6 },
  regionChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: COLORS.card,
    borderWidth: 1,
    borderColor: COLORS.border,
    marginRight: 8,
  },
  regionChipActive: { backgroundColor: COLORS.primary, borderColor: COLORS.primary },
  regionChipText: { fontSize: 14, fontWeight: '600', color: COLORS.text },
  regionChipZone: { fontSize: 10, color: COLORS.textMuted, marginTop: 1 },
  regionChipTextActive: { color: '#fff' },
  regionInfo: { fontSize: 12, color: COLORS.textMuted, marginBottom: 12 },
  searchRow: { flexDirection: 'row', gap: 8 },
  searchInput: {
    flex: 1,
    backgroundColor: COLORS.card,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 15,
    color: COLORS.text,
  },
  pasteButton: {
    backgroundColor: COLORS.primarySoft,
    borderRadius: 12,
    paddingHorizontal: 14,
    justifyContent: 'center',
  },
  pasteButtonText: { color: COLORS.primaryDark, fontWeight: '700', fontSize: 13 },
  suggestion: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.card,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 12,
    padding: 12,
    marginTop: 8,
  },
  suggestionName: { fontSize: 15, fontWeight: '600', color: COLORS.text },
  suggestionMeta: { fontSize: 12, color: COLORS.textMuted, marginTop: 2 },
  suggestionAdd: { color: COLORS.primary, fontWeight: '700', fontSize: 13 },
  pasteFeedback: {
    marginTop: 10,
    fontSize: 13,
    color: COLORS.info,
    backgroundColor: '#EFF6FF',
    padding: 10,
    borderRadius: 10,
  },
  listHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 16,
  },
  clearText: { color: COLORS.danger, fontWeight: '600', fontSize: 13 },
  emptyBox: {
    alignItems: 'center',
    padding: 28,
    backgroundColor: COLORS.card,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  emptyEmoji: { fontSize: 34, marginBottom: 8 },
  emptyText: { textAlign: 'center', color: COLORS.textMuted, fontSize: 14, lineHeight: 20 },
  itemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.card,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  itemName: { fontSize: 15, fontWeight: '600', color: COLORS.text },
  itemMeta: { fontSize: 12, color: COLORS.textMuted, marginTop: 2 },
  qtyControls: { flexDirection: 'row', alignItems: 'center', marginRight: 8 },
  qtyButton: {
    width: 30,
    height: 30,
    borderRadius: 8,
    backgroundColor: COLORS.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  qtyButtonText: { fontSize: 18, fontWeight: '700', color: COLORS.primaryDark },
  qtyValue: {
    minWidth: 28,
    textAlign: 'center',
    fontSize: 15,
    fontWeight: '700',
    color: COLORS.text,
  },
  removeButton: { padding: 6 },
  removeButtonText: { color: COLORS.textMuted, fontSize: 14 },
  footer: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    padding: 16,
    backgroundColor: COLORS.bg,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
  },
  cta: {
    backgroundColor: COLORS.primary,
    borderRadius: 14,
    paddingVertical: 15,
    alignItems: 'center',
  },
  ctaText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(15,23,42,0.5)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: COLORS.card,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    paddingBottom: 32,
  },
  modalTitle: { fontSize: 18, fontWeight: '800', color: COLORS.text },
  modalHint: { fontSize: 13, color: COLORS.textMuted, marginTop: 4, marginBottom: 12 },
  modalInput: {
    minHeight: 120,
    maxHeight: 200,
    backgroundColor: COLORS.bg,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 12,
    padding: 12,
    fontSize: 15,
    color: COLORS.text,
    textAlignVertical: 'top',
  },
  modalActions: { flexDirection: 'row', gap: 10, marginTop: 14 },
  modalButton: {
    flex: 1,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  modalCancel: { backgroundColor: COLORS.bg, borderWidth: 1, borderColor: COLORS.border },
  modalCancelText: { color: COLORS.text, fontWeight: '600' },
  modalConfirm: { backgroundColor: COLORS.primary },
  modalConfirmText: { color: '#fff', fontWeight: '700' },
});
