import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, useColorScheme, SafeAreaView,
} from 'react-native';
import { ConditionPicker } from '../../components/ConditionPicker';
import { MenuCard } from '../../components/MenuCard';
import { useFridgeStore } from '../../store/useFridgeStore';
import { useProfileStore } from '../../store/useProfileStore';
import { useHistoryStore } from '../../store/useHistoryStore';
import { getMenuRecommendation, MenuRecommendation } from '../../lib/groq';
import { colors } from '../../constants/theme';

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
    ? members
        .map((m) => `${m.name}(${m.ageGroup}, 알레르기: ${m.allergies.join('/') || '없음'})`)
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

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: isDark ? colors.backgroundDark : '#F5F5F5' }]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={[styles.title, { color: isDark ? '#FFF' : colors.dark }]}>오늘 저녁 뭐 먹지? 🍽️</Text>

        <View style={[styles.card, { backgroundColor: isDark ? '#2d2d2d' : '#FFF' }]}>
          <ConditionPicker label="스타일" options={CONDITIONS.style} value={style} onChange={setStyle} />
          <ConditionPicker label="기분" options={CONDITIONS.mood} value={mood} onChange={setMood} />
          <ConditionPicker label="인원" options={CONDITIONS.who} value={who} onChange={setWho} />
          <ConditionPicker label="조리시간" options={CONDITIONS.time} value={time} onChange={setTime} />
          {ingredients.length > 0 && (
            <Text style={styles.fridgeNote}>🧊 냉장고 재료 {ingredients.length}개 반영됨</Text>
          )}
        </View>

        <TouchableOpacity
          style={[styles.recommendBtn, (!hasCondition || loading) && styles.disabled]}
          onPress={handleRecommend}
          disabled={!hasCondition || loading}
        >
          <Text style={styles.recommendText}>추천받기 ✨</Text>
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
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  scroll: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 26, fontWeight: '800', marginBottom: 20, marginTop: 8 },
  card: {
    borderRadius: 16, padding: 16, marginBottom: 16,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06, shadowRadius: 4, elevation: 2,
  },
  fridgeNote: { marginTop: 12, fontSize: 13, color: colors.primary, fontWeight: '500' },
  recommendBtn: {
    backgroundColor: colors.primary, borderRadius: 14,
    paddingVertical: 16, alignItems: 'center',
  },
  disabled: { opacity: 0.4 },
  recommendText: { color: '#FFFFFF', fontSize: 18, fontWeight: '700' },
});
