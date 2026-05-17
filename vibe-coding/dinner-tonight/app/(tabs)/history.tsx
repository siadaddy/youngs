import React, { useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity, useColorScheme, Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useHistoryStore, HistoryEntry } from '../../store/useHistoryStore';
import { colors, shadows } from '../../constants/theme';

type FilterTab = 'all' | 'favorites';

function getThisWeekRange() {
  const now = new Date();
  const start = new Date(now);
  start.setDate(now.getDate() - now.getDay());
  start.setHours(0, 0, 0, 0);
  return start;
}

export default function HistoryScreen() {
  const isDark = useColorScheme() === 'dark';
  const router = useRouter();
  const { entries, removeEntry, favorites, toggleFavorite } = useHistoryStore();
  const [filter, setFilter] = useState<FilterTab>('all');

  const sorted = [...entries].sort((a, b) => b.date.localeCompare(a.date));
  const displayed = filter === 'favorites' ? sorted.filter((e) => favorites.includes(e.id)) : sorted;

  // 주간 통계
  const weekStart = getThisWeekRange();
  const thisWeek = entries.filter((e) => new Date(e.date) >= weekStart);
  const weekCount = thisWeek.length;
  const streakDays = (() => {
    const today = new Date().toISOString().split('T')[0];
    let streak = 0;
    const dateSet = new Set(entries.map((e) => e.date));
    let cursor = new Date();
    while (dateSet.has(cursor.toISOString().split('T')[0])) {
      streak++;
      cursor.setDate(cursor.getDate() - 1);
    }
    return streak;
  })();

  const bg = isDark ? colors.backgroundDark : colors.background;
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
    const prevItem = displayed[index - 1];
    const showDate = !prevItem || prevItem.date !== item.date;
    const isFav = favorites.includes(item.id);
    return (
      <>
        {showDate && (
          <Text style={[styles.dateHeader, { color: mutedColor }]}>{formatDate(item.date)}</Text>
        )}
        <TouchableOpacity
          style={[styles.item, { backgroundColor: cardBg }, shadows.sm]}
          onPress={() => item.recipe && router.push(`/recipe?id=${item.id}`)}
          activeOpacity={item.recipe ? 0.75 : 1}
        >
          <View style={[styles.emojiCircle, { backgroundColor: isDark ? '#2A2A3E' : colors.accent }]}>
            <Text style={styles.emoji}>{item.emoji}</Text>
          </View>
          <View style={styles.info}>
            <Text style={[styles.menuName, { color: textColor }]}>{item.menu}</Text>
            <Text style={[styles.dateSub, { color: mutedColor }]}>{formatDate(item.date)}</Text>
            {item.recipe && (
              <Text style={[styles.recipeHint, { color: colors.primary }]}>조리법 보기 →</Text>
            )}
          </View>
          <View style={styles.actions}>
            <TouchableOpacity onPress={() => toggleFavorite(item.id)} style={styles.favBtn}>
              <Text style={[styles.favIcon, { color: isFav ? '#FF9500' : mutedColor }]}>
                {isFav ? '★' : '☆'}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => handleDelete(item)} style={styles.deleteBtn}>
              <Text style={styles.deleteText}>✕</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
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

          {/* 주간 통계 카드 */}
          {sorted.length > 0 && (
            <View style={[styles.statsRow]}>
              <View style={[styles.statBox, { backgroundColor: isDark ? colors.surfaceDark : colors.accent }]}>
                <Text style={styles.statNum}>{weekCount}</Text>
                <Text style={[styles.statLabel, { color: mutedColor }]}>이번 주</Text>
              </View>
              <View style={[styles.statBox, { backgroundColor: isDark ? colors.surfaceDark : colors.accent }]}>
                <Text style={styles.statNum}>{favorites.length}</Text>
                <Text style={[styles.statLabel, { color: mutedColor }]}>즐겨찾기</Text>
              </View>
              <View style={[styles.statBox, { backgroundColor: isDark ? colors.surfaceDark : colors.accent }]}>
                <Text style={styles.statNum}>{streakDays > 0 ? `${streakDays}일` : '-'}</Text>
                <Text style={[styles.statLabel, { color: mutedColor }]}>연속 기록</Text>
              </View>
            </View>
          )}

          {/* 필터 탭 */}
          <View style={styles.filterRow}>
            {(['all', 'favorites'] as FilterTab[]).map((tab) => (
              <TouchableOpacity
                key={tab}
                style={[
                  styles.filterBtn,
                  filter === tab && { backgroundColor: colors.primary },
                  filter !== tab && { backgroundColor: isDark ? colors.surfaceDark : colors.surface },
                ]}
                onPress={() => setFilter(tab)}
                activeOpacity={0.8}
              >
                <Text style={[styles.filterText, { color: filter === tab ? '#FFF' : mutedColor }]}>
                  {tab === 'all' ? '전체' : `★ 즐겨찾기${favorites.length > 0 ? ` (${favorites.length})` : ''}`}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </SafeAreaView>
      </View>

      {displayed.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyEmoji}>{filter === 'favorites' ? '★' : '🍽️'}</Text>
          <Text style={[styles.emptyTitle, { color: textColor }]}>
            {filter === 'favorites' ? '즐겨찾기가 없어요' : '기록이 없어요'}
          </Text>
          <Text style={[styles.emptySub, { color: mutedColor }]}>
            {filter === 'favorites' ? '기록 옆 ☆를 탭해서 저장하세요' : '홈에서 메뉴를 결정하면\n여기에 기록돼요'}
          </Text>
        </View>
      ) : (
        <FlatList
          data={displayed}
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
  headerSub: { fontSize: 14, marginTop: 4, marginBottom: 10 },
  statsRow: { flexDirection: 'row', gap: 10, marginBottom: 12 },
  statBox: {
    flex: 1, borderRadius: 16, paddingVertical: 12, paddingHorizontal: 10, alignItems: 'center',
  },
  statNum: { fontSize: 22, fontWeight: '900', color: colors.primary },
  statLabel: { fontSize: 11, fontWeight: '600', marginTop: 2 },
  filterRow: { flexDirection: 'row', gap: 8, marginBottom: 4 },
  filterBtn: { paddingVertical: 7, paddingHorizontal: 16, borderRadius: 20 },
  filterText: { fontSize: 13, fontWeight: '600' },
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
  recipeHint: { fontSize: 12, fontWeight: '600', marginTop: 4 },
  actions: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  favBtn: {
    width: 32, height: 32, borderRadius: 16,
    justifyContent: 'center', alignItems: 'center',
  },
  favIcon: { fontSize: 20, fontWeight: '700' },
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
