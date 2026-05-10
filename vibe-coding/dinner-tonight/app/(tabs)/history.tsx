import React from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity, useColorScheme, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useHistoryStore, HistoryEntry } from '../../store/useHistoryStore';
import { colors, shadows } from '../../constants/theme';

export default function HistoryScreen() {
  const isDark = useColorScheme() === 'dark';
  const { entries, removeEntry } = useHistoryStore();
  const sorted = [...entries].sort((a, b) => b.date.localeCompare(a.date));

  const bg = isDark ? colors.backgroundDark : '#F5F6FA';
  const cardBg = isDark ? colors.cardDark : colors.card;
  const textColor = isDark ? '#FFFFFF' : colors.dark;
  const mutedColor = isDark ? colors.textMutedDark : colors.textMuted;

  function handleDelete(entry: HistoryEntry) {
    Alert.alert('기록 삭제', `"${entry.menu}" 기록을 삭제할까요?`, [
      { text: '취소', style: 'cancel' },
      { text: '삭제', style: 'destructive', onPress: () => removeEntry(entry.id) },
    ]);
  }

  function formatDate(dateStr: string) {
    const d = new Date(dateStr);
    const days = ['일', '월', '화', '수', '목', '금', '토'];
    return `${d.getMonth() + 1}월 ${d.getDate()}일 (${days[d.getDay()]})`;
  }

  function renderItem({ item, index }: { item: HistoryEntry; index: number }) {
    const prevItem = sorted[index - 1];
    const showDate = !prevItem || prevItem.date !== item.date;
    return (
      <>
        {showDate && (
          <Text style={[styles.dateHeader, { color: mutedColor }]}>{formatDate(item.date)}</Text>
        )}
        <View style={[styles.item, { backgroundColor: cardBg }, shadows.sm]}>
          <View style={[styles.emojiCircle, { backgroundColor: isDark ? '#2A2A3E' : colors.accent }]}>
            <Text style={styles.emoji}>{item.emoji}</Text>
          </View>
          <View style={styles.info}>
            <Text style={[styles.menuName, { color: textColor }]}>{item.menu}</Text>
            <Text style={[styles.dateSub, { color: mutedColor }]}>{formatDate(item.date)}</Text>
          </View>
          <TouchableOpacity onPress={() => handleDelete(item)} style={styles.deleteBtn}>
            <Text style={styles.deleteText}>✕</Text>
          </TouchableOpacity>
        </View>
      </>
    );
  }

  return (
    <View style={[styles.root, { backgroundColor: bg }]}>
      <View style={[styles.header, { backgroundColor: isDark ? colors.cardDark : '#FFF' }, shadows.sm]}>
        <SafeAreaView edges={['top']}>
          <Text style={[styles.headerTitle, { color: textColor }]}>먹은 기록 📅</Text>
          <Text style={[styles.headerSub, { color: mutedColor }]}>
            {sorted.length > 0 ? `총 ${sorted.length}끼 기록됨` : '아직 기록이 없어요'}
          </Text>
        </SafeAreaView>
      </View>

      {sorted.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyEmoji}>🍽️</Text>
          <Text style={[styles.emptyTitle, { color: textColor }]}>기록이 없어요</Text>
          <Text style={[styles.emptySub, { color: mutedColor }]}>홈에서 메뉴를 결정하면{'\n'}여기에 기록돼요</Text>
        </View>
      ) : (
        <FlatList
          data={sorted}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: { paddingHorizontal: 24, paddingBottom: 16 },
  headerTitle: { fontSize: 28, fontWeight: '800', marginTop: 8 },
  headerSub: { fontSize: 14, marginTop: 4, marginBottom: 4 },
  list: { padding: 20, paddingTop: 12 },
  dateHeader: { fontSize: 12, fontWeight: '700', letterSpacing: 0.8, textTransform: 'uppercase', marginTop: 16, marginBottom: 8 },
  item: {
    flexDirection: 'row', alignItems: 'center',
    borderRadius: 20, padding: 16, marginBottom: 10,
  },
  emojiCircle: {
    width: 52, height: 52, borderRadius: 26,
    justifyContent: 'center', alignItems: 'center', marginRight: 14,
  },
  emoji: { fontSize: 28 },
  info: { flex: 1 },
  menuName: { fontSize: 17, fontWeight: '700', marginBottom: 4 },
  dateSub: { fontSize: 13 },
  deleteBtn: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: 'rgba(255,82,82,0.1)',
    justifyContent: 'center', alignItems: 'center',
  },
  deleteText: { color: colors.error, fontSize: 13, fontWeight: '700' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingBottom: 80 },
  emptyEmoji: { fontSize: 64, marginBottom: 16 },
  emptyTitle: { fontSize: 20, fontWeight: '700', marginBottom: 8 },
  emptySub: { fontSize: 15, textAlign: 'center', lineHeight: 22 },
});
