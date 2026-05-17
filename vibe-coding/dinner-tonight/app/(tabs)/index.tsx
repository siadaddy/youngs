import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, useColorScheme, StatusBar, Switch,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ConditionPicker } from '../../components/ConditionPicker';
import { MenuCard } from '../../components/MenuCard';
import { useFridgeStore } from '../../store/useFridgeStore';
import { useProfileStore } from '../../store/useProfileStore';
import { useHistoryStore } from '../../store/useHistoryStore';
import { getMenuRecommendation, MenuRecommendation } from '../../lib/groq';
import { colors, shadows } from '../../constants/theme';
import { FeedbackModal } from '../../components/FeedbackModal';

const CONDITIONS = {
  style: ['집밥', '배달', '외식'],
  cuisine: ['한식', '중식', '일식', '양식', '동남아', '분식', '디저트'],
  mood: ['집에서 쉬고 싶어', '기분 전환하고 싶어', '힘내고 싶어', '특별한 날이야'],
  who: ['혼자', '둘이서', '아이랑', '온 가족'],
  time: ['15분 이내', '30분', '여유있게'],
  spicy: ['순한맛', '보통', '매운맛'],
};

export default function HomeScreen() {
  const isDark = useColorScheme() === 'dark';
  const router = useRouter();

  const [style, setStyle] = useState<string | null>(null);
  const [cuisine, setCuisine] = useState<string | null>(null);
  const [mood, setMood] = useState<string | null>(null);
  const [who, setWho] = useState<string | null>(null);
  const [time, setTime] = useState<string | null>(null);
  const [spicy, setSpicy] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<MenuRecommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [useFridge, setUseFridge] = useState(true);
  const [showFeedback, setShowFeedback] = useState(false);
  const [showExtra, setShowExtra] = useState(false);

  const ingredients = useFridgeStore((s) => s.ingredients);
  const members = useProfileStore((s) => s.members);
  const { getThisWeekMenus, addEntry } = useHistoryStore();

  const hasCondition = !!(style || mood || who || time || cuisine || spicy);

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
        conditions: { style: style ?? '', cuisine: cuisine ?? '', mood: mood ?? '', who: who ?? '', time: time ?? '', spicy: spicy ?? '' },
        ingredients: useFridge ? ingredients : [],
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

  async function handleSelectAlternative(menuName: string) {
    setLoading(true);
    setError(null);
    setRecommendation(null);
    try {
      const result = await getMenuRecommendation({
        conditions: { style: style ?? '', cuisine: cuisine ?? '', mood: mood ?? '', who: who ?? '', time: time ?? '', spicy: spicy ?? '' },
        ingredients: useFridge ? ingredients : [],
        recentMenus: getThisWeekMenus(),
        familyProfile,
        requestedMenu: menuName,
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
    const id = addEntry({
      date: new Date().toISOString().split('T')[0],
      menu: recommendation.menu,
      emoji: recommendation.emoji,
      reason: recommendation.reason,
      ingredients: recommendation.ingredients,
      recipe: recommendation.recipe,
      tip: recommendation.tip,
    });
    setRecommendation(null);
    setStyle(null); setCuisine(null); setMood(null); setWho(null); setTime(null); setSpicy(null);
    setShowExtra(false);
    router.push('/recipe?id=' + id);
  }

  const bg = isDark ? colors.backgroundDark : colors.background;
  const cardBg = isDark ? colors.cardDark : colors.card;
  const textColor = isDark ? '#FFFFFF' : colors.dark;

  return (
    <View style={[styles.root, { backgroundColor: bg }]}>
      <StatusBar barStyle="light-content" />

      {/* Hero Header */}
      <View style={styles.header}>
        <SafeAreaView edges={['top']}>
          <View style={styles.headerRow}>
            <Text style={styles.headerTitle}>딱메 🍽️</Text>
            <TouchableOpacity
              style={styles.feedbackIconBtn}
              onPress={() => setShowFeedback(true)}
              activeOpacity={0.7}
            >
              <Text style={styles.feedbackIcon}>💬</Text>
            </TouchableOpacity>
          </View>
          <Text style={styles.headerDesc}>매일 저녁 "오늘 뭐 먹지?" 고민하는{'\n'}모든 분들에게 — AI가 <Text style={styles.headerAccent}>'딱'</Text> <Text style={styles.headerAccent}>'메'</Text>뉴를 골라드려요</Text>
          {ingredients.length > 0 && (
            <View style={styles.fridgeBadge}>
              <Text style={styles.fridgeBadgeText}>🧊 냉장고 재료 {ingredients.length}개</Text>
            </View>
          )}
        </SafeAreaView>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Condition card */}
        <View style={[styles.card, { backgroundColor: cardBg }, shadows.lg]}>
          {/* 카드 헤더 */}
          <View style={styles.cardHeader}>
            <Text style={[styles.cardHeaderText, { color: textColor }]}>조건 설정</Text>
            {hasCondition && (
              <TouchableOpacity
                style={[styles.resetBtn, { borderColor: isDark ? colors.borderDark : colors.border }]}
                onPress={() => { setStyle(null); setCuisine(null); setMood(null); setWho(null); setTime(null); setSpicy(null); setRecommendation(null); setError(null); }}
                activeOpacity={0.7}
              >
                <Text style={[styles.resetBtnText, { color: colors.textMuted }]}>↺  초기화</Text>
              </TouchableOpacity>
            )}
          </View>
          <ConditionPicker label="식사 스타일" options={CONDITIONS.style} value={style} onChange={setStyle} isDark={isDark} />
          <ConditionPicker label="인원" options={CONDITIONS.who} value={who} onChange={setWho} isDark={isDark} />

          {/* 추가 설정 토글 */}
          <TouchableOpacity
            style={[styles.extraToggle, { borderColor: isDark ? colors.borderDark : colors.border }]}
            onPress={() => setShowExtra(!showExtra)}
            activeOpacity={0.7}
          >
            <Text style={[styles.extraToggleText, { color: colors.primary }]}>
              {showExtra ? '▲  추가 설정 접기' : '▼  음식 종류·기분·맵기 더 설정하기'}
            </Text>
            {!showExtra && (cuisine || mood || spicy || time) && (
              <View style={styles.extraDot} />
            )}
          </TouchableOpacity>

          {showExtra && (
            <>
              <ConditionPicker label="음식 종류" options={CONDITIONS.cuisine} value={cuisine} onChange={setCuisine} isDark={isDark} />
              <ConditionPicker label="오늘의 상황" options={CONDITIONS.mood} value={mood} onChange={setMood} isDark={isDark} />
              {style !== '배달' && (
                <ConditionPicker label="조리 시간" options={CONDITIONS.time} value={time} onChange={setTime} isDark={isDark} />
              )}
              {cuisine !== '디저트' && (
                <ConditionPicker label="맵기" options={CONDITIONS.spicy} value={spicy} onChange={setSpicy} isDark={isDark} />
              )}
            </>
          )}

          {ingredients.length > 0 && (
            <View style={[styles.fridgeToggleRow, { borderTopColor: isDark ? colors.borderDark : colors.border }]}>
              <View>
                <Text style={[styles.fridgeToggleLabel, { color: textColor }]}>🧊 냉장고 재료 반영</Text>
                <Text style={[styles.fridgeToggleSub, { color: isDark ? colors.textMutedDark : colors.textMuted }]}>
                  {useFridge ? `${ingredients.length}가지 재료 활용` : '재료 무시하고 자유 추천'}
                </Text>
              </View>
              <Switch
                value={useFridge}
                onValueChange={setUseFridge}
                trackColor={{ false: isDark ? '#555' : '#DDD', true: colors.primary }}
                thumbColor="#FFF"
              />
            </View>
          )}
        </View>

        {/* CTA */}
        <TouchableOpacity
          style={[styles.recommendBtn, loading && styles.disabled, shadows.md]}
          onPress={handleRecommend}
          disabled={loading}
          activeOpacity={0.85}
        >
          <Text style={styles.recommendText}>
            {hasCondition ? '✨  AI 메뉴 추천받기' : '🎲  오늘의 랜덤 추천'}
          </Text>
        </TouchableOpacity>
        <Text style={styles.aiNotice}>🤖 무료 AI 사용 중 · 간혹 외국어가 섞일 수 있어요</Text>

        {(loading || recommendation || error) && (
          <MenuCard
            loading={loading}
            recommendation={recommendation}
            error={error}
            onConfirm={handleConfirm}
            onRetry={handleRecommend}
            onSelectAlternative={handleSelectAlternative}
            selectedStyle={style}
          />
        )}

        <View style={{ height: 40 }} />
      </ScrollView>

      <FeedbackModal visible={showFeedback} onClose={() => setShowFeedback(false)} />
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
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, marginBottom: 6 },
  headerTitle: { color: '#FFFFFF', fontSize: 38, fontWeight: '900', letterSpacing: -0.5 },
  feedbackIconBtn: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    width: 40, height: 40, borderRadius: 20,
    justifyContent: 'center', alignItems: 'center',
  },
  feedbackIcon: { fontSize: 20 },
  headerDesc: { color: 'rgba(255,255,255,0.8)', fontSize: 15, lineHeight: 22, marginBottom: 14 },
  headerAccent: { color: '#FFE082', fontWeight: '800' },
  fridgeBadge: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 20, paddingVertical: 6, paddingHorizontal: 14,
    alignSelf: 'flex-start', marginBottom: 4,
  },
  fridgeBadgeText: { color: '#FFFFFF', fontSize: 13, fontWeight: '600' },
  fridgeToggleRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    borderTopWidth: 1, marginTop: 16, paddingTop: 16,
  },
  fridgeToggleLabel: { fontSize: 15, fontWeight: '600', marginBottom: 3 },
  fridgeToggleSub: { fontSize: 12 },
  scroll: { paddingHorizontal: 20, paddingTop: 20 },
  card: { borderRadius: 24, padding: 24, marginBottom: 16 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  cardHeaderText: { fontSize: 16, fontWeight: '700' },
  resetBtn: {
    borderWidth: 1.5, borderRadius: 20,
    paddingVertical: 6, paddingHorizontal: 12,
  },
  resetBtnText: { fontSize: 13, fontWeight: '600' },
  recommendBtn: {
    backgroundColor: colors.primary,
    borderRadius: 18, paddingVertical: 18,
    alignItems: 'center', marginBottom: 4,
  },
  disabled: { opacity: 0.4 },
  recommendText: { color: '#FFFFFF', fontSize: 18, fontWeight: '800', letterSpacing: 0.3 },
  aiNotice: { textAlign: 'center', fontSize: 12, color: colors.textMuted, marginTop: 8, marginBottom: 4 },
  extraToggle: {
    borderWidth: 1, borderRadius: 16, borderStyle: 'dashed',
    paddingVertical: 10, paddingHorizontal: 16,
    alignItems: 'center', marginTop: 8, flexDirection: 'row', justifyContent: 'center',
  },
  extraToggleText: { fontSize: 13, fontWeight: '600' },
  extraDot: {
    width: 7, height: 7, borderRadius: 4,
    backgroundColor: colors.primary, marginLeft: 6,
  },
});
