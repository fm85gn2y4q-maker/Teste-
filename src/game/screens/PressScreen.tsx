// ============================================================
// PressScreen — Press Conference
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
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../types/navigation';
import { useGameStore } from '../store';
import { PressAnswer } from '../types';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Press'>;
};

interface EffectSummary {
  moraleTotal: number;
  boardTotal: number;
  fanTotal: number;
}

export default function PressScreen({ navigation }: Props) {
  const pressQuestions = useGameStore((s) => s.pressQuestions);
  const pendingPress = useGameStore((s) => s.pendingPressConference);
  const answerPress = useGameStore((s) => s.answerPress);

  const [answered, setAnswered] = useState<Record<string, { answer: PressAnswer; index: number }>>({});
  const [effects, setEffects] = useState<EffectSummary>({ moraleTotal: 0, boardTotal: 0, fanTotal: 0 });
  const [allDone, setAllDone] = useState(false);

  const questions = pressQuestions.slice(0, 3);

  function handleAnswer(questionId: string, answer: PressAnswer, idx: number) {
    if (answered[questionId]) return;

    const newAnswered = { ...answered, [questionId]: { answer, index: idx } };
    setAnswered(newAnswered);

    const newEffects: EffectSummary = {
      moraleTotal: effects.moraleTotal + answer.moraleEffect,
      boardTotal: effects.boardTotal + answer.boardEffect,
      fanTotal: effects.fanTotal + answer.fanEffect,
    };
    setEffects(newEffects);

    answerPress(questionId, idx);

    // Check if all answered
    if (Object.keys(newAnswered).length >= questions.length) {
      setAllDone(true);
    }
  }

  function effectColor(val: number): string {
    if (val > 0) return '#00ff88';
    if (val < 0) return '#ff4444';
    return '#888';
  }

  function effectSign(val: number): string {
    if (val > 0) return `+${val}`;
    return `${val}`;
  }

  if (!pendingPress && !allDone) {
    return (
      <SafeAreaView style={styles.safe}>
        <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyTitle}>Nenhuma coletiva agendada</Text>
          <Text style={styles.emptyText}>A próxima coletiva será convocada em breve.</Text>
          <TouchableOpacity style={styles.closeBtn} onPress={() => navigation.goBack()}>
            <Text style={styles.closeBtnText}>← Voltar</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
      <View style={styles.topBar}>
        <Text style={styles.screenTitle}>🎤 COLETIVA DE IMPRENSA</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {!allDone ? (
          <>
            <Text style={styles.instructions}>
              Responda às perguntas da imprensa. Suas respostas afetam moral do elenco, confiança da diretoria e satisfação dos torcedores.
            </Text>

            {questions.map((q, qIdx) => {
              const isAnswered = Boolean(answered[q.id]);
              const selectedAnswer = answered[q.id];
              return (
                <View key={q.id} style={[styles.questionCard, isAnswered && styles.questionCardDone]}>
                  <View style={styles.questionHeader}>
                    <View style={[styles.questionNum, isAnswered && styles.questionNumDone]}>
                      <Text style={[styles.questionNumText, isAnswered && styles.questionNumTextDone]}>
                        {isAnswered ? '✓' : `${qIdx + 1}`}
                      </Text>
                    </View>
                    <Text style={styles.questionText}>{q.question}</Text>
                  </View>

                  <View style={styles.answersBlock}>
                    {q.options.map((opt, idx) => {
                      const isSelected = selectedAnswer?.index === idx;
                      return (
                        <TouchableOpacity
                          key={idx}
                          style={[
                            styles.answerBtn,
                            isAnswered && !isSelected && styles.answerBtnFaded,
                            isSelected && styles.answerBtnSelected,
                          ]}
                          onPress={() => handleAnswer(q.id, opt, idx)}
                          disabled={isAnswered}
                          activeOpacity={0.75}
                        >
                          <Text style={[styles.answerText, isSelected && styles.answerTextSelected]}>
                            {opt.text}
                          </Text>
                          {isSelected && (
                            <View style={styles.effectRow}>
                              <Text style={[styles.effectText, { color: effectColor(opt.moraleEffect) }]}>
                                Moral {effectSign(opt.moraleEffect)}
                              </Text>
                              <Text style={[styles.effectText, { color: effectColor(opt.boardEffect) }]}>
                                Dir. {effectSign(opt.boardEffect)}
                              </Text>
                              <Text style={[styles.effectText, { color: effectColor(opt.fanEffect) }]}>
                                Torç. {effectSign(opt.fanEffect)}
                              </Text>
                            </View>
                          )}
                        </TouchableOpacity>
                      );
                    })}
                  </View>
                </View>
              );
            })}
          </>
        ) : (
          <View style={styles.summaryContainer}>
            <Text style={styles.summaryTitle}>COLETIVA CONCLUÍDA</Text>
            <Text style={styles.summarySubtitle}>Resumo dos efeitos das suas respostas:</Text>

            <View style={styles.effectCards}>
              <View style={styles.effectCard}>
                <Text style={styles.effectCardLabel}>MORAL DO ELENCO</Text>
                <Text style={[styles.effectCardValue, { color: effectColor(effects.moraleTotal) }]}>
                  {effectSign(effects.moraleTotal)}
                </Text>
              </View>
              <View style={styles.effectCard}>
                <Text style={styles.effectCardLabel}>CONFIANÇA DIRETORIA</Text>
                <Text style={[styles.effectCardValue, { color: effectColor(effects.boardTotal) }]}>
                  {effectSign(effects.boardTotal)}
                </Text>
              </View>
              <View style={styles.effectCard}>
                <Text style={styles.effectCardLabel}>SATISFAÇÃO TORCIDA</Text>
                <Text style={[styles.effectCardValue, { color: effectColor(effects.fanTotal) }]}>
                  {effectSign(effects.fanTotal)}
                </Text>
              </View>
            </View>

            {/* Answered questions recap */}
            {questions.map((q) => {
              const ans = answered[q.id];
              if (!ans) return null;
              return (
                <View key={q.id} style={styles.recapCard}>
                  <Text style={styles.recapQuestion}>{q.question}</Text>
                  <Text style={styles.recapAnswer}>"{ans.answer.text}"</Text>
                </View>
              );
            })}

            <TouchableOpacity style={styles.closeConferenceBtn} onPress={() => navigation.goBack()}>
              <Text style={styles.closeConferenceBtnText}>✓ FECHAR COLETIVA</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0a0a0f' },
  topBar: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a2e',
  },
  screenTitle: { color: '#fff', fontSize: 18, fontWeight: '900' },
  scroll: { padding: 16, paddingBottom: 40 },
  instructions: {
    color: '#888',
    fontSize: 12,
    lineHeight: 18,
    marginBottom: 16,
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  questionCard: {
    backgroundColor: '#1a1a2e',
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  questionCardDone: { borderColor: '#00ff8844', opacity: 0.9 },
  questionHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 12 },
  questionNum: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#2a2a3e',
    alignItems: 'center',
    justifyContent: 'center',
  },
  questionNumDone: { backgroundColor: '#00ff8822' },
  questionNumText: { color: '#888', fontSize: 13, fontWeight: '900' },
  questionNumTextDone: { color: '#00ff88' },
  questionText: { color: '#ddd', fontSize: 14, flex: 1, lineHeight: 20, fontWeight: '500' },
  answersBlock: { gap: 8 },
  answerBtn: {
    backgroundColor: '#0d0d1e',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  answerBtnFaded: { opacity: 0.4 },
  answerBtnSelected: {
    borderColor: '#00ff88',
    backgroundColor: '#0a1a0f',
  },
  answerText: { color: '#ccc', fontSize: 13, lineHeight: 18 },
  answerTextSelected: { color: '#fff' },
  effectRow: { flexDirection: 'row', gap: 12, marginTop: 8 },
  effectText: { fontSize: 11, fontWeight: '700' },
  summaryContainer: { alignItems: 'stretch' },
  summaryTitle: {
    color: '#00ff88',
    fontSize: 22,
    fontWeight: '900',
    textAlign: 'center',
    marginBottom: 6,
  },
  summarySubtitle: { color: '#888', fontSize: 13, textAlign: 'center', marginBottom: 20 },
  effectCards: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 20,
  },
  effectCard: {
    flex: 1,
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  effectCardLabel: { color: '#555', fontSize: 8, fontWeight: '700', letterSpacing: 1, textAlign: 'center', marginBottom: 6 },
  effectCardValue: { fontSize: 28, fontWeight: '900' },
  recapCard: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  recapQuestion: { color: '#888', fontSize: 11, marginBottom: 4 },
  recapAnswer: { color: '#ddd', fontSize: 13, fontStyle: 'italic' },
  closeConferenceBtn: {
    backgroundColor: '#00ff88',
    borderRadius: 8,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 12,
  },
  closeConferenceBtnText: { color: '#0a0a0f', fontSize: 15, fontWeight: '900', letterSpacing: 1 },
  emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  emptyTitle: { color: '#fff', fontSize: 18, fontWeight: '900', marginBottom: 8 },
  emptyText: { color: '#888', fontSize: 13, textAlign: 'center', marginBottom: 24 },
  closeBtn: {
    backgroundColor: '#1a1a2e',
    borderRadius: 8,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: '#2a2a3e',
  },
  closeBtnText: { color: '#00ff88', fontSize: 14, fontWeight: '700' },
});
