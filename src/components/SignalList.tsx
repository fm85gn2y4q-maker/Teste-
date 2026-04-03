import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { SignalResult } from '../analysis/types';
import { schoolLabel, scoreColor } from '../analysis/convergence';

interface Props {
  schools: SignalResult[];
}

export function SignalList({ schools }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Sinais Detectados</Text>
      {schools.map((s) => {
        const color = scoreColor(s.score);
        const isOpen = expanded === s.school;
        return (
          <TouchableOpacity
            key={s.school}
            style={styles.item}
            onPress={() => setExpanded(isOpen ? null : s.school)}
            activeOpacity={0.7}
          >
            <View style={styles.itemHeader}>
              <View style={[styles.dot, { backgroundColor: color }]} />
              <Text style={styles.itemSchool}>{schoolLabel(s.school)}</Text>
              <Text style={[styles.itemScore, { color }]}>
                {s.score > 0 ? '+' : ''}{s.score}
              </Text>
              <Text style={styles.chevron}>{isOpen ? '▲' : '▼'}</Text>
            </View>
            {isOpen && s.signals.length > 0 && (
              <View style={styles.signalBox}>
                {s.signals.map((sig, i) => (
                  <Text key={i} style={styles.signalText}>• {sig}</Text>
                ))}
                <Text style={styles.confText}>
                  Confiança: {(s.confidence * 100).toFixed(0)}%
                </Text>
              </View>
            )}
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  item: {
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
    paddingVertical: 10,
  },
  itemHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  itemSchool: {
    flex: 1,
    fontSize: 14,
    color: '#374151',
    fontWeight: '500',
  },
  itemScore: {
    fontSize: 14,
    fontWeight: '700',
    marginRight: 8,
  },
  chevron: {
    fontSize: 10,
    color: '#9CA3AF',
  },
  signalBox: {
    marginTop: 8,
    paddingLeft: 16,
    backgroundColor: '#F9FAFB',
    borderRadius: 8,
    padding: 10,
  },
  signalText: {
    fontSize: 12,
    color: '#4B5563',
    lineHeight: 20,
  },
  confText: {
    fontSize: 11,
    color: '#9CA3AF',
    marginTop: 6,
  },
});
