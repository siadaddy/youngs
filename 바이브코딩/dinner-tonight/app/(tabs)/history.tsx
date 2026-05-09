import React from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  useColorScheme, SafeAreaView, Alert,
} from 'react-native';
import { useHistoryStore, HistoryEntry } from '../../store/useHistoryStore';
import { colors } from '../../constants/theme';

export default function HistoryScreen() {
  const isDark = useColorScheme() === 'dark';
  const { entries, removeEntry } = useHistoryStore();
  const sorted = [...entries].sort((a, b) => b.date.localeCompare(a.date));

  function handleDelete(entry: HistoryEntry) {
    Alert.alert('삭제', `"${entry.menu}" 기록을 삭제할까요?`, [
      { text: '취소', style: 'cancel' },
      { text: '삭제', style: 'destructive', onPress: () => removeEntry(entry.id) },
    ]);
  }

  function renderItem({ item }: { item: HistoryEntry }) {
    return (
      <View style={[styles.item, { backgroundColor: isDark ? '#2d2d2d' : '#FFF' }]}>
        <Text style={styles.emoji}>{item.emoji}</Text>
        <View style={styles.info}>
          <Text style={[styles.menuName, { color: isDark ? '#FFF' : colors.dark }]}>{item.menu}</Text>
          <Text style={styles.date}>{item.date}</Text>
        </View>
        <TouchableOpacity onPress={() => handleDelete(item)} style={styles.deleteBtn}>
          <Text style={styles.deleteText}>삭제</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: isDark ? colors.backgroundDark : '#F5F5F5' }]}>
      <Text style={[styles.title, { color: isDark ? '#FFF' : colors.dark }]}>📅 먹은 메뉴 기록</Text>
      {sorted.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyText}>아직 기록이 없어요.</Text>
          <Text style={styles.emptyText}>홈에서 메뉴를 결정해보세요!</Text>
        </View>
      ) : (
        <FlatList
          data={sorted}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  title: { fontSize: 24, fontWeight: '800', margin: 16 },
  list: { padding: 16, paddingTop: 0 },
  item: {
    flexDirection: 'row', alignItems: 'center', borderRadius: 14,
    padding: 14, marginBottom: 10,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 2,
  },
  emoji: { fontSize: 32, marginRight: 12 },
  info: { flex: 1 },
  menuName: { fontSize: 17, fontWeight: '600', marginBottom: 4 },
  date: { fontSize: 13, color: '#888' },
  deleteBtn: { padding: 8 },
  deleteText: { color: '#e74c3c', fontSize: 13, fontWeight: '600' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', marginTop: 100 },
  emptyText: { fontSize: 16, color: '#888', marginBottom: 6 },
});
