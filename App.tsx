import { StatusBar } from 'expo-status-bar';
import React, { useState } from 'react';
import {
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

interface Task {
  id: string;
  text: string;
  done: boolean;
  createdAt: Date;
}

type Filter = 'all' | 'active' | 'done';

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([
    { id: '1', text: 'Comprar leite', done: false, createdAt: new Date() },
    { id: '2', text: 'Ligar para o médico', done: true, createdAt: new Date() },
    { id: '3', text: 'Estudar React Native', done: false, createdAt: new Date() },
  ]);
  const [inputText, setInputText] = useState('');
  const [filter, setFilter] = useState<Filter>('all');

  const filteredTasks = tasks.filter((t) => {
    if (filter === 'active') return !t.done;
    if (filter === 'done') return t.done;
    return true;
  });

  const addTask = () => {
    const text = inputText.trim();
    if (!text) return;
    setTasks((prev) => [
      { id: Date.now().toString(), text, done: false, createdAt: new Date() },
      ...prev,
    ]);
    setInputText('');
  };

  const toggleTask = (id: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, done: !t.done } : t))
    );
  };

  const deleteTask = (id: string) => {
    Alert.alert('Remover tarefa', 'Deseja remover esta tarefa?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Remover',
        style: 'destructive',
        onPress: () => setTasks((prev) => prev.filter((t) => t.id !== id)),
      },
    ]);
  };

  const clearCompleted = () => {
    setTasks((prev) => prev.filter((t) => !t.done));
  };

  const activeCount = tasks.filter((t) => !t.done).length;

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Minhas Tarefas</Text>
          <Text style={styles.headerSub}>
            {activeCount} {activeCount === 1 ? 'tarefa pendente' : 'tarefas pendentes'}
          </Text>
        </View>

        {/* Input */}
        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            placeholder="Adicionar nova tarefa..."
            placeholderTextColor="#aaa"
            value={inputText}
            onChangeText={setInputText}
            onSubmitEditing={addTask}
            returnKeyType="done"
          />
          <TouchableOpacity style={styles.addBtn} onPress={addTask}>
            <Text style={styles.addBtnText}>+</Text>
          </TouchableOpacity>
        </View>

        {/* Filter tabs */}
        <View style={styles.filterRow}>
          {(['all', 'active', 'done'] as Filter[]).map((f) => (
            <TouchableOpacity
              key={f}
              style={[styles.filterTab, filter === f && styles.filterTabActive]}
              onPress={() => setFilter(f)}
            >
              <Text style={[styles.filterTabText, filter === f && styles.filterTabTextActive]}>
                {f === 'all' ? 'Todas' : f === 'active' ? 'Pendentes' : 'Concluidas'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Task list */}
        <FlatList
          data={filteredTasks}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <View style={styles.emptyBox}>
              <Text style={styles.emptyText}>Nenhuma tarefa aqui.</Text>
            </View>
          }
          renderItem={({ item }) => (
            <View style={styles.taskCard}>
              <TouchableOpacity
                style={[styles.checkbox, item.done && styles.checkboxDone]}
                onPress={() => toggleTask(item.id)}
              >
                {item.done && <Text style={styles.checkmark}>✓</Text>}
              </TouchableOpacity>
              <Text style={[styles.taskText, item.done && styles.taskTextDone]}>
                {item.text}
              </Text>
              <TouchableOpacity
                style={styles.deleteBtn}
                onPress={() => deleteTask(item.id)}
              >
                <Text style={styles.deleteBtnText}>✕</Text>
              </TouchableOpacity>
            </View>
          )}
        />

        {/* Footer */}
        {tasks.some((t) => t.done) && (
          <TouchableOpacity style={styles.clearBtn} onPress={clearCompleted}>
            <Text style={styles.clearBtnText}>Limpar concluidas</Text>
          </TouchableOpacity>
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const PURPLE = '#6C3DE8';
const LIGHT_PURPLE = '#EDE8FD';

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: PURPLE },
  flex: { flex: 1 },

  header: {
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 16,
    backgroundColor: PURPLE,
  },
  headerTitle: {
    fontSize: 32,
    fontWeight: '700',
    color: '#fff',
    letterSpacing: 0.5,
  },
  headerSub: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
    marginTop: 4,
  },

  inputRow: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 12,
    gap: 8,
  },
  input: {
    flex: 1,
    height: 50,
    backgroundColor: '#fff',
    borderRadius: 14,
    paddingHorizontal: 16,
    fontSize: 16,
    color: '#222',
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  addBtn: {
    width: 50,
    height: 50,
    backgroundColor: '#fff',
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  addBtnText: { fontSize: 28, color: PURPLE, lineHeight: 32 },

  filterRow: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 8,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 12,
    padding: 4,
  },
  filterTab: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 10,
    alignItems: 'center',
  },
  filterTabActive: { backgroundColor: '#fff' },
  filterTabText: { fontSize: 13, color: 'rgba(255,255,255,0.8)', fontWeight: '500' },
  filterTabTextActive: { color: PURPLE, fontWeight: '700' },

  list: { paddingHorizontal: 16, paddingTop: 8, paddingBottom: 24 },

  taskCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  checkbox: {
    width: 26,
    height: 26,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: PURPLE,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
  },
  checkboxDone: { backgroundColor: PURPLE, borderColor: PURPLE },
  checkmark: { color: '#fff', fontSize: 14, fontWeight: '700' },
  taskText: { flex: 1, fontSize: 16, color: '#222' },
  taskTextDone: { textDecorationLine: 'line-through', color: '#aaa' },
  deleteBtn: { paddingLeft: 12, paddingVertical: 4 },
  deleteBtnText: { fontSize: 16, color: '#ccc' },

  emptyBox: { alignItems: 'center', marginTop: 40 },
  emptyText: { color: 'rgba(255,255,255,0.6)', fontSize: 16 },

  clearBtn: {
    margin: 16,
    padding: 14,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 14,
    alignItems: 'center',
  },
  clearBtnText: { color: '#fff', fontWeight: '600', fontSize: 15 },
});
