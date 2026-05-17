import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, useColorScheme, Share,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useHistoryStore } from '../store/useHistoryStore';
import { colors, shadows } from '../constants/theme';

export default function RecipeScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const isDark = useColorScheme() === 'dark';
  const entry = useHistoryStore((s) => s.getEntryById(id));
  const savedChecked = useHistoryStore((s) => s.checkedSteps[id]);
  const setCheckedSteps = useHistoryStore((s) => s.setCheckedSteps);

  const checked: boolean[] = savedChecked ?? Array(entry?.recipe?.length ?? 0).fill(false);

  function toggleCheck(i: number) {
    const next = checked.map((v, idx) => (idx === i ? !v : v));
    setCheckedSteps(id, next);
  }

  async function handleShare() {
    if (!entry) return;
    const ingredientText = entry.ingredients && entry.ingredients.length > 0
      ? `\n\n🛒 재료\n${entry.ingredients.join(', ')}` : '';
    const recipeText = entry.recipe?.map((s, i) => `${i + 1}. ${s}`).join('\n') ?? '';
    const tipText = entry.tip ? `\n\n💡 꿀팁: ${entry.tip}` : '';
    await Share.share({
      message: `${entry.emoji} ${entry.menu}${ingredientText}\n\n📋 조리법\n${recipeText}${tipText}\n\n— 딱메 앱으로 추천받았어요`,
    });
  }

  if (!entry) {
    return (
      <View style={[styles.root, { backgroundColor: isDark ? colors.backgroundDark : colors.background }]}>
        <SafeAreaView>
          <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
            <Text style={[styles.backText, { color: colors.primary }]}>← 돌아가기</Text>
          </TouchableOpacity>
          <Text style={{ textAlign: 'center', marginTop: 60, color: colors.textMuted }}>조리법 정보가 없어요.</Text>
        </SafeAreaView>
      </View>
    );
  }

  const bg = isDark ? colors.backgroundDark : colors.background;
  const cardBg = isDark ? colors.cardDark : colors.card;
  const textColor = isDark ? '#FFFFFF' : colors.dark;
  const mutedColor = isDark ? colors.textMutedDark : colors.textMuted;
  const allDone = checked.length > 0 && checked.every(Boolean);

  return (
    <View style={[styles.root, { backgroundColor: bg }]}>
      {/* 헤더 */}
      <View style={[styles.header, { backgroundColor: colors.primary }]}>
        <SafeAreaView edges={['top']}>
          <View style={styles.topRow}>
            <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
              <Text style={styles.backTextWhite}>← 뒤로</Text>
            </TouchableOpacity>
            {entry.recipe && entry.recipe.length > 0 && (
              <TouchableOpacity style={styles.shareBtn} onPress={handleShare}>
                <Text style={styles.shareText}>공유 ↗</Text>
              </TouchableOpacity>
            )}
          </View>
          <View style={styles.heroRow}>
            <Text style={styles.heroEmoji}>{entry.emoji}</Text>
            <View style={styles.heroInfo}>
              <Text style={styles.heroMenu}>{entry.menu}</Text>
              <Text style={styles.heroDate}>{entry.date}</Text>
            </View>
          </View>
        </SafeAreaView>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* 추천 이유 */}
        {entry.reason && (
          <View style={[styles.card, { backgroundColor: cardBg }, shadows.sm]}>
            <Text style={[styles.sectionTitle, { color: mutedColor }]}>추천 이유</Text>
            <Text style={[styles.reasonText, { color: textColor }]}>{entry.reason}</Text>
          </View>
        )}

        {/* 재료 */}
        {entry.ingredients && entry.ingredients.length > 0 && (
          <View style={[styles.card, { backgroundColor: cardBg }, shadows.sm]}>
            <Text style={[styles.sectionTitle, { color: mutedColor }]}>재료</Text>
            <View style={styles.ingredientGrid}>
              {entry.ingredients.map((ing, i) => (
                <View key={i} style={[styles.ingredientChip, { backgroundColor: isDark ? colors.surfaceDark : colors.accent }]}>
                  <Text style={[styles.ingredientText, { color: isDark ? '#FFD580' : '#8B5000' }]}>{ing}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* 조리법 */}
        {entry.recipe && entry.recipe.length > 0 && (
          <View style={[styles.card, { backgroundColor: cardBg }, shadows.sm]}>
            <Text style={[styles.sectionTitle, { color: mutedColor }]}>조리법</Text>
            <Text style={[styles.checkGuide, { color: mutedColor }]}>단계를 완료하면 탭해서 체크하세요</Text>
            {entry.recipe.map((step, i) => (
              <TouchableOpacity
                key={i}
                style={[
                  styles.stepRow,
                  { backgroundColor: checked[i] ? (isDark ? '#1A2E1A' : '#F0FFF0') : 'transparent' },
                ]}
                onPress={() => toggleCheck(i)}
                activeOpacity={0.7}
              >
                <View style={[styles.stepBadge, { backgroundColor: checked[i] ? colors.success : colors.primary }]}>
                  <Text style={styles.stepNum}>{checked[i] ? '✓' : i + 1}</Text>
                </View>
                <Text style={[styles.stepText, { color: textColor, opacity: checked[i] ? 0.5 : 1 }]}>
                  {step}
                </Text>
              </TouchableOpacity>
            ))}

            {allDone && (
              <View style={styles.doneBox}>
                <Text style={styles.doneText}>🎉 완성! 맛있게 드세요!</Text>
              </View>
            )}
          </View>
        )}

        {/* 꿀팁 */}
        {entry.tip && (
          <View style={[styles.tipBox, { backgroundColor: isDark ? '#2A1F00' : colors.accent }]}>
            <Text style={styles.tipIcon}>💡</Text>
            <Text style={[styles.tipText, { color: isDark ? '#FFD580' : '#8B5000' }]}>{entry.tip}</Text>
          </View>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: { paddingHorizontal: 24, paddingBottom: 24 },
  topRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, marginBottom: 12 },
  backBtn: {},
  backTextWhite: { color: 'rgba(255,255,255,0.85)', fontSize: 15, fontWeight: '600' },
  backText: { fontSize: 15, fontWeight: '600' },
  shareBtn: { backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: 16, paddingVertical: 6, paddingHorizontal: 14 },
  shareText: { color: '#FFF', fontSize: 13, fontWeight: '700' },
  heroRow: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  heroEmoji: { fontSize: 52 },
  heroInfo: { flex: 1 },
  heroMenu: { color: '#FFFFFF', fontSize: 26, fontWeight: '900' },
  heroDate: { color: 'rgba(255,255,255,0.7)', fontSize: 13, marginTop: 4 },
  scroll: { padding: 20 },
  card: { borderRadius: 24, padding: 20, marginBottom: 16 },
  sectionTitle: { fontSize: 12, fontWeight: '700', letterSpacing: 0.8, textTransform: 'uppercase', marginBottom: 12 },
  reasonText: { fontSize: 15, lineHeight: 24 },
  checkGuide: { fontSize: 12, marginBottom: 14 },
  stepRow: {
    flexDirection: 'row', alignItems: 'flex-start',
    borderRadius: 14, padding: 12, marginBottom: 8,
  },
  stepBadge: {
    width: 28, height: 28, borderRadius: 14,
    justifyContent: 'center', alignItems: 'center',
    marginRight: 12, marginTop: 1,
  },
  stepNum: { color: '#FFF', fontSize: 13, fontWeight: '800' },
  stepText: { flex: 1, fontSize: 15, lineHeight: 23 },
  doneBox: {
    backgroundColor: colors.success,
    borderRadius: 14, padding: 14,
    alignItems: 'center', marginTop: 8,
  },
  doneText: { color: '#FFF', fontSize: 16, fontWeight: '800' },
  tipBox: {
    flexDirection: 'row', alignItems: 'flex-start',
    borderRadius: 20, padding: 16, marginBottom: 16,
  },
  tipIcon: { fontSize: 18, marginRight: 10, marginTop: 1 },
  tipText: { flex: 1, fontSize: 15, lineHeight: 22, fontWeight: '500' },
  ingredientGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  ingredientChip: { borderRadius: 20, paddingVertical: 6, paddingHorizontal: 14 },
  ingredientText: { fontSize: 13, fontWeight: '600' },
});
