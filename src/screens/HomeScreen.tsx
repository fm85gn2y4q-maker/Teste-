import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  FlatList,
  RefreshControl,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useStore } from '../store/useStore';
import { AssetCard } from '../components/AssetCard';
import { WatchlistAsset } from '../analysis/types';
import { searchTicker } from '../api/brapi';
import { RootStackParamList, MainTabParamList } from '../types/navigation';
import { CompositeNavigationProp } from '@react-navigation/native';
import { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';

type Props = {
  navigation: CompositeNavigationProp<
    BottomTabNavigationProp<MainTabParamList, 'Home'>,
    NativeStackNavigationProp<RootStackParamList>
  >;
};

const PURPLE = '#6C3DE8';

export function HomeScreen({ navigation }: Props) {
  const { watchlist, loadingTickers, refreshAll, addTicker, removeTicker } = useStore();
  const [refreshing, setRefreshing] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState<{ stock: string; name: string }[]>([]);

  useEffect(() => {
    useStore.getState().initWatchlist();
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await refreshAll();
    setRefreshing(false);
  }, [refreshAll]);

  const onSearch = async (text: string) => {
    setSearchText(text);
    if (text.length < 2) { setSearchResults([]); return; }
    try {
      const results = await searchTicker(text);
      setSearchResults(results.slice(0, 8));
    } catch {
      setSearchResults([]);
    }
  };

  const onAdd = (ticker: string) => {
    addTicker(ticker.toUpperCase());
    setSearchText('');
    setSearchResults([]);
  };

  const onRemove = (ticker: string) => {
    Alert.alert('Remover ativo', `Remover ${ticker} da watchlist?`, [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Remover', style: 'destructive', onPress: () => removeTicker(ticker) },
    ]);
  };

  const bullish = watchlist.filter((a) => (a.convergence?.overallScore ?? 0) >= 30).length;
  const bearish = watchlist.filter((a) => (a.convergence?.overallScore ?? 0) <= -30).length;

  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Grafista B3</Text>
          <Text style={styles.headerSub}>Convergência Multi-Escola</Text>
        </View>
        <View style={styles.headerStats}>
          <View style={[styles.statPill, { backgroundColor: '#DCFCE7' }]}>
            <Text style={[styles.statText, { color: '#16A34A' }]}>↑ {bullish}</Text>
          </View>
          <View style={[styles.statPill, { backgroundColor: '#FEE2E2' }]}>
            <Text style={[styles.statText, { color: '#DC2626' }]}>↓ {bearish}</Text>
          </View>
        </View>
      </View>

      {/* Busca */}
      <View style={styles.searchBox}>
        <TextInput
          style={styles.searchInput}
          placeholder="Buscar ativo (ex: PETR4)..."
          placeholderTextColor="#9CA3AF"
          value={searchText}
          onChangeText={onSearch}
          autoCapitalize="characters"
        />
        {searchText.length > 0 && (
          <TouchableOpacity style={styles.clearBtn} onPress={() => { setSearchText(''); setSearchResults([]); }}>
            <Text style={styles.clearBtnText}>✕</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Resultados de busca */}
      {searchResults.length > 0 && (
        <View style={styles.searchResults}>
          {searchResults.map((r) => (
            <TouchableOpacity key={r.stock} style={styles.searchResultItem} onPress={() => onAdd(r.stock)}>
              <Text style={styles.resultTicker}>{r.stock}</Text>
              <Text style={styles.resultName} numberOfLines={1}>{r.name}</Text>
              <Text style={styles.resultAdd}>+</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Lista */}
      <FlatList
        data={watchlist}
        keyExtractor={(item) => item.ticker}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={PURPLE} />
        }
        ListHeaderComponent={
          <Text style={styles.listHeader}>Watchlist — {watchlist.length} ativos</Text>
        }
        renderItem={({ item }: { item: WatchlistAsset }) => (
          <AssetCard
            asset={item}
            loading={loadingTickers.has(item.ticker)}
            onPress={() => navigation.navigate('Detail', { ticker: item.ticker })}
            onLongPress={() => onRemove(item.ticker)}
          />
        )}
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Text style={styles.emptyText}>Watchlist vazia.{'\n'}Busque um ativo para adicionar.</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#F9FAFB' },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
    backgroundColor: PURPLE,
  },
  headerTitle: { fontSize: 22, fontWeight: '800', color: '#fff' },
  headerSub: { fontSize: 12, color: 'rgba(255,255,255,0.7)', marginTop: 2 },
  headerStats: { flexDirection: 'row', gap: 6 },
  statPill: { borderRadius: 20, paddingHorizontal: 10, paddingVertical: 4 },
  statText: { fontSize: 13, fontWeight: '700' },

  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
    marginTop: 12,
    marginBottom: 4,
    backgroundColor: '#fff',
    borderRadius: 12,
    paddingHorizontal: 12,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  searchInput: { flex: 1, height: 44, fontSize: 15, color: '#111827' },
  clearBtn: { padding: 8 },
  clearBtnText: { color: '#9CA3AF', fontSize: 14 },

  searchResults: {
    marginHorizontal: 16,
    backgroundColor: '#fff',
    borderRadius: 12,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 3,
    marginBottom: 4,
    overflow: 'hidden',
  },
  searchResultItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  resultTicker: { fontSize: 14, fontWeight: '700', color: '#111827', width: 60 },
  resultName: { flex: 1, fontSize: 12, color: '#6B7280', marginHorizontal: 8 },
  resultAdd: { fontSize: 20, color: PURPLE, fontWeight: '700' },

  list: { padding: 16 },
  listHeader: { fontSize: 12, color: '#9CA3AF', marginBottom: 8, fontWeight: '600', letterSpacing: 0.5 },
  emptyBox: { alignItems: 'center', marginTop: 60 },
  emptyText: { color: '#9CA3AF', fontSize: 15, textAlign: 'center', lineHeight: 24 },
});
