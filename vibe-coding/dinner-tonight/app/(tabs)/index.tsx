import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, useColorScheme, StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ConditionPicker } from '../../components/ConditionPicker';
import { MenuCard } from '../../components/MenuCard';
import { useFridgeStore } from '../../store/useFridgeStore';
import { useProfileStore } from '../../store/useProfileStore';
import { useHistoryStore } from '../../store/useHistoryStore';
import { getMenuRecommendation, MenuRecommendation } from '../../lib/groq';
import { colors, shadows } from '../../constants/theme';

const CONDITIONS = {
  style: ['집밥', '배달', '외식'],
  mood: ['가볍게', '든든하게', '특별하게'],
  who: ['혼자', '둘이서', '온 가족'],
  time: ['15분 이내', '30분', '여유있게'],
};

export default function HomeScreen() {
  const isDark = useColorScheme() === 'dark';

  const [style, setStyle] = useState<string | null>(null);
  const [mood, setMood] = useState<string | null>(null);
  const [who, setWho] = useState<string | null>(null);
  const [time, setTime] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<MenuRecommendation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ingredients = useFridgeStore((s) => s.ingredients);
  const members = useProfileStore((s) => s.members);
  const { getThisWeekMenus, addEntry } = useHistoryStore();

  const hasCondition = !!(style || mood || who || time);

  const familyProfile = members.length > 0
    ? members.map((m) => `${m.name}(${m.ageGroup}, 알레르기: ${m.allergies.join('/') || '없음'})`)
        .join(', ')
    : '';

  async function handleRecommend() {
    setLoading(true);
    setError(null);
    setRecommendation(null);
    try {
      const result = await getMenuRecommendation({
        conditions: { style: style ?? '', mood: mood ?? '', who: who ?? '', time: time ?? '' },
        ingredients,
        recentMenus: getThisWeekMenus(),
        familyProfile,
      });
      setRecommendation(result);
    } catch (e: any) {
      setError(e.message ?? '다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  }

  function handleConfirm() {
    if (!recommendation) return;
    addEntry({
      date: new Date().toISOString().split('T')[0],
      menu: recommendation.menu,
      emoji: recommendation.emoji,
    });
    setRecommendation(null);
    setStyle(null); setMood(null); setWho(null); setTime(null);
  }

  const bg = isDark ? colors.backgroundDark : '#F5F6FA';
  const cardBg = isDark ? colors.cardDark : colors.card;
  const textColor = isDark ? '#FFFFFF' : colors.dark;

  return (
    <View style={[styles.root, { backgroundColor: bg }]}>
      <StatusBar barStyle="light-content" />

      {/* Hero Header */}
      <View style={styles.header}>
        <SafeAreaView edges={['top']}>
          <Text style={styles.headerSub}>오늘 저녁</Text>
          <Text style={styles.headerTitle}>뭐 먹지? 🍽️</Text>
          {ingredients.length > 0 && (
            <View style={styles.fridgeBadge}>
              <Text style={styles.fridgeBadgeText}>🧊 냉장고 재료 {ingredients.length}개 반영</Text>
            </View>
          )}
        </SafeAreaView>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Condition card */}
        <View style={[styles.card, { backgroundColor: cardBg }, shadows.lg]}>
          <ConditionPicker label="식사 스타일" options={CONDITIONS.style} value={style} onChange={setStyle} isDark={isDark} />
          <ConditionPicker label="기분" options={CONDITIONS.mood} value={mood} onChange={setMood} isDark={isDark} />
          <ConditionPicker label="인원" options={CONDITIONS.who} value={who} onChange={setWho} isDark={isDark} />
          <ConditionPicker label="조리 시간" options={CONDITIONS.time} value={time} onChange={setTime} isDark={isDark} />
        </View>

        {/* CTA */}
        <TouchableOpacity
          style={[styles.recommendBtn, (!hasCondition || loading) && styles.disabled, shadows.md]}
          onPress={handleRecommend}
          disabled={!hasCondition || loading}
          activeOpacity={0.85}
        >
          <Text style={styles.recommendText}>✨  AI 메뉴 추천받기</Text>
        </TouchableOpacity>

        {(loading || recommendation || error) && (
          <MenuCard
            loading={loading}
            recommendation={recommendation}
            error={error}
            onConfirm={handleConfirm}
            onRetry={handleRecommend}
          />
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: {
    backgroundColor: colors.primary,
    paddingHorizontal: 24,
    paddingBottom: 28,
  },
  headerSub: { color: 'rgba(255,255,255,0.75)', fontSize: 14, fontWeight: '600', marginTop: 12, letterSpacing: 1 },
  headerTitle: { color: '#FFFFFF', fontSize: 36, fontWeight: '900', marginTop: 4, marginBottom: 12 },
  fridgeBadge: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 20, paddingVertical: 6, paddingHorizontal: 14,
    alignSelf: 'flex-start', marginBottom: 4,
  },
  fridgeBadgeText: { color: '#FFFFFF', fontSize: 13, fontWeight: '600' },
  scroll: { paddingHorizontal: 20, paddingTop: 20 },
  card: {
    borderRadius: 24, padding: 24, marginBottom: 16,
  },
  recommendBtn: {
    backgroundColor: colors.primary,
    borderRadius: 18, paddingVertical: 18,
    alignItems: 'center', marginBottom: 4,
  },
  disabled: { opacity: 0.4 },
  recommendText: { color: '#FFFFFF', fontSize: 18, fontWeight: '800', letterSpacing: 0.3 },
});
