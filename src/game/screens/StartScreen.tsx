// ============================================================
// StartScreen — Club Selection
// ============================================================
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types/navigation';
import { useGameStore } from '../store';
import { CLUBS } from '../database';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Start'>;
};

const fmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });

function reputationStars(rep: number): string {
  const stars = Math.round((rep / 20) * 5);
  return '★'.repeat(Math.max(1, Math.min(5, stars))) + '☆'.repeat(5 - Math.max(1, Math.min(5, stars)));
}

export default function StartScreen({ navigation }: Props) {
  const initGame = useGameStore((s) => s.initGame);

  function handleSelect(clubId: string) {
    initGame(clubId);
    navigation.replace('Main');
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
      <View style={styles.header}>
        <Text style={styles.title}>CHAMPIONSHIP MANAGER</Text>
        <Text style={styles.subtitle}>BRASILEIRÃO SÉRIE A — 2003</Text>
        <Text style={styles.prompt}>Selecione seu clube</Text>
      </View>
      <ScrollView contentContainerStyle={styles.list}>
        {CLUBS.map((club) => (
          <TouchableOpacity
            key={club.id}
            style={styles.card}
            onPress={() => handleSelect(club.id)}
            activeOpacity={0.75}
          >
            <View style={styles.cardTop}>
              <Text style={styles.clubName}>{club.name}</Text>
              <Text style={styles.stars}>{reputationStars(club.reputation)}</Text>
            </View>
            <View style={styles.cardBottom}>
              <Text style={styles.city}>{club.city} · {club.stadium}</Text>
              <Text style={styles.budget}>Orçamento: {fmt.format(club.budget)}</Text>
            </View>
            <View style={styles.repBar}>
              <View style={[styles.repFill, { width: `${(club.reputation / 20) * 100}%` }]} />
            </View>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: '#0a0a0f',
  },
  header: {
    paddingHorizontal: 16,
    paddingTop: 24,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a2e',
  },
  title: {
    color: '#00ff88',
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 2,
    fontVariant: ['tabular-nums'],
  },
  subtitle: {
    color: '#aaa',
    fontSize: 12,
    letterSpacing: 1,
    marginTop: 2,
  },
  prompt: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
    marginTop: 12,
  },
  list: {
    padding: 12,
    gap: 10,
  },
  card: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 14,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  clubName: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
    flex: 1,
  },
  stars: {
    color: '#f4c430',
    fontSize: 14,
    letterSpacing: 2,
  },
  cardBottom: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  city: {
    color: '#888',
    fontSize: 11,
    flex: 1,
  },
  budget: {
    color: '#00ff88',
    fontSize: 11,
    fontVariant: ['tabular-nums'],
  },
  repBar: {
    height: 3,
    backgroundColor: '#2a2a3e',
    borderRadius: 2,
    overflow: 'hidden',
  },
  repFill: {
    height: 3,
    backgroundColor: '#00ff88',
    borderRadius: 2,
  },
});
