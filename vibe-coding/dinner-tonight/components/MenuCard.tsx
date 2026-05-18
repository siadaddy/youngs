import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, useColorScheme } from 'react-native';
import { colors, shadows } from '../constants/theme';
import { MenuRecommendation } from '../lib/groq';
import { ActionLinks } from './ActionLinks';

interface Props {
  loading: boolean;
  recommendation: MenuRecommendation | null;
  error: string | null;
  onConfirm: () => void;
  onRetry: () => void;
  onSelectAlternative: (menu: string) => void;
  selectedStyle: string | null;
}

export function MenuCard({ loading, recommendation, error, onConfirm, onRetry, onSelectAlternative, selectedStyle }: Props) {
  const isDark = useColorScheme() === 'dark';
  const cardBg = isDark ? colors.cardDark : colors.card;
  const textColor = isDark ? '#FFFFFF' : colors.dark;
  const mutedColor = isDark ? colors.textMutedDark : colors.textMuted;
  const [showAllSteps, setShowAllSteps] = useState(false);

  const isDeliveryOrDineOut = selectedStyle === '배달' || selectedStyle === '외식';

  if (loading) {
    return (
      <View style={[styles.card, { backgroundColor: cardBg }, shadows.lg]}>
        <View style={styles.loadingInner}>
          <ActivityIndicator testID="loading-indicator" size="large" color={colors.primary} />
          <Text style={[styles.loadingTitle, { color: textColor }]}>AI가 고민 중이에요</Text>
          <Text style={[styles.loadingSub, { color: mutedColor }]}>딱 맞는 메뉴를 찾고 있어요 ✨</Text>
        </View>
      </View>
    );
  }

  if (error) {
    return (
      <View style={[styles.card, { backgroundColor: cardBg }, shadows.sm]}>
        <Text style={styles.errorEmoji}>😢</Text>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryBtnFilled} onPress={onRetry}>
          <Text style={styles.retryBtnFilledText}>다시 시도하기</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!recommendation) return null;

  const { menu, emoji, reason, trendReason, recipe, tip, alternatives } = recommendation;

  return (
    <View style={[styles.card, { backgroundColor: cardBg }, shadows.lg]}>
      {/* Hero */}
      <View style={styles.hero}>
        <View style={styles.emojiCircle}>
          <Text style={styles.emoji}>{emoji}</Text>
        </View>
        <Text style={[styles.menuName, { color: textColor }]}>{menu}</Text>
        {trendReason && (
          <View style={styles.trendBadge}>
            <Text style={styles.trendText}>🔥 {trendReason}</Text>
          </View>
        )}
        <Text style={[styles.reason, { color: mutedColor }]}>{reason}</Text>
      </View>

      <View style={[styles.divider, { backgroundColor: isDark ? colors.borderDark : colors.border }]} />

      {/* 배달/외식: 딥링크 먼저 */}
      {isDeliveryOrDineOut && (
        <ActionLinks menu={menu} selectedStyle={selectedStyle} />
      )}

      {/* 집밥: 조리법 먼저 */}
      {!isDeliveryOrDineOut && recipe.length > 0 && (
        <>
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: textColor }]}>조리법 미리보기</Text>
            {(showAllSteps ? recipe : recipe.slice(0, 2)).map((step, i) => (
              <View key={i} style={styles.stepRow}>
                <View style={styles.stepBadge}>
                  <Text style={styles.stepNum}>{i + 1}</Text>
                </View>
                <Text style={[styles.stepText, { color: textColor }]}>{step}</Text>
              </View>
            ))}
            {recipe.length > 2 && (
              <TouchableOpacity onPress={() => setShowAllSteps(!showAllSteps)} style={styles.showMoreBtn}>
                <Text style={[styles.showMoreText, { color: colors.primary }]}>
                  {showAllSteps ? '▲  접기' : `▼  전체 ${recipe.length}단계 보기`}
                </Text>
              </TouchableOpacity>
            )}
          </View>
          <View style={[styles.tipBox, { backgroundColor: isDark ? '#2A1F00' : colors.accent }]}>
            <Text style={styles.tipIcon}>💡</Text>
            <Text style={[styles.tipText, { color: isDark ? '#FFD580' : '#8B5000' }]}>{tip}</Text>
          </View>
          <ActionLinks menu={menu} selectedStyle={selectedStyle} />
        </>
      )}

      {/* 다른 메뉴 */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: textColor }]}>다른 메뉴도 볼까요?</Text>
        <View style={styles.altRow}>
          {alternatives.map((alt) => (
            <TouchableOpacity
              key={alt}
              style={[styles.altTag, { backgroundColor: isDark ? colors.surfaceDark : colors.surface }]}
              onPress={() => onSelectAlternative(alt)}
              activeOpacity={0.7}
            >
              <Text style={[styles.altText, { color: colors.primary }]}>{alt}</Text>
              <Text style={[styles.altArrow, { color: colors.primary }]}> →</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* CTAs */}
      <TouchableOpacity style={styles.confirmBtn} onPress={onConfirm} activeOpacity={0.85}>
        <Text style={styles.confirmText}>🎉  이 메뉴로 결정!</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={[styles.retryBtn, { borderColor: isDark ? colors.borderDark : colors.border }]}
        onPress={onRetry}
        activeOpacity={0.7}
      >
        <Text style={[styles.retryText, { color: mutedColor }]}>🔄  다시 추천받기</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 24, overflow: 'hidden', marginTop: 20 },
  hero: { alignItems: 'center', paddingTop: 32, paddingBottom: 24, paddingHorizontal: 24 },
  emojiCircle: {
    width: 100, height: 100, borderRadius: 50,
    backgroundColor: colors.accent,
    justifyContent: 'center', alignItems: 'center', marginBottom: 16,
  },
  emoji: { fontSize: 56 },
  menuName: { fontSize: 30, fontWeight: '800', marginBottom: 10, textAlign: 'center' },
  trendBadge: {
    backgroundColor: 'rgba(255,107,53,0.12)',
    borderRadius: 20, paddingVertical: 7, paddingHorizontal: 14,
    marginBottom: 10, alignSelf: 'center',
  },
  trendText: { fontSize: 13, fontWeight: '700', color: colors.primary, textAlign: 'center' },
  reason: { fontSize: 15, textAlign: 'center', lineHeight: 22 },
  divider: { height: 1, marginHorizontal: 20 },
  section: { paddingHorizontal: 24, paddingTop: 20, paddingBottom: 4 },
  sectionTitle: { fontSize: 13, fontWeight: '700', letterSpacing: 0.5, textTransform: 'uppercase', opacity: 0.5, marginBottom: 12 },
  stepRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 10 },
  stepBadge: {
    width: 24, height: 24, borderRadius: 12, backgroundColor: colors.primary,
    justifyContent: 'center', alignItems: 'center', marginRight: 10, marginTop: 1,
  },
  stepNum: { color: '#FFF', fontSize: 12, fontWeight: '700' },
  stepText: { flex: 1, fontSize: 15, lineHeight: 22 },
  showMoreBtn: { alignItems: 'center', paddingVertical: 8, marginTop: 4 },
  showMoreText: { fontSize: 13, fontWeight: '700' },
  tipBox: {
    flexDirection: 'row', alignItems: 'flex-start',
    marginHorizontal: 20, marginTop: 16, borderRadius: 14, padding: 14,
  },
  tipIcon: { fontSize: 16, marginRight: 8, marginTop: 1 },
  tipText: { flex: 1, fontSize: 14, lineHeight: 20, fontWeight: '500' },
  altRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  altTag: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 20, borderWidth: 1.5, borderColor: colors.primary },
  altText: { fontSize: 14, fontWeight: '600' },
  altArrow: { fontSize: 14, fontWeight: '700' },
  confirmBtn: {
    backgroundColor: colors.primary, marginHorizontal: 20, marginTop: 24,
    borderRadius: 16, paddingVertical: 16, alignItems: 'center', ...shadows.md,
  },
  confirmText: { color: '#FFFFFF', fontSize: 17, fontWeight: '800', letterSpacing: 0.3 },
  retryBtn: {
    marginHorizontal: 20, marginTop: 10, marginBottom: 24,
    borderRadius: 16, paddingVertical: 14, alignItems: 'center', borderWidth: 1.5,
  },
  retryText: { fontSize: 15, fontWeight: '600' },
  loadingInner: { alignItems: 'center', paddingVertical: 48, paddingHorizontal: 24 },
  loadingTitle: { fontSize: 20, fontWeight: '700', marginTop: 20, marginBottom: 8 },
  loadingSub: { fontSize: 15 },
  errorEmoji: { fontSize: 48, textAlign: 'center', marginTop: 32 },
  errorText: { color: colors.error, fontSize: 15, textAlign: 'center', marginVertical: 16, paddingHorizontal: 24 },
  retryBtnFilled: {
    backgroundColor: colors.primary, borderRadius: 14,
    paddingVertical: 14, marginHorizontal: 24, marginBottom: 24, alignItems: 'center',
  },
  retryBtnFilledText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
});
