import React from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, useColorScheme,
} from 'react-native';
import { colors } from '../constants/theme';
import { MenuRecommendation } from '../lib/groq';

interface Props {
  loading: boolean;
  recommendation: MenuRecommendation | null;
  error: string | null;
  onConfirm: () => void;
  onRetry: () => void;
}

export function MenuCard({ loading, recommendation, error, onConfirm, onRetry }: Props) {
  const isDark = useColorScheme() === 'dark';
  const cardBg = isDark ? '#2d2d2d' : colors.background;
  const textColor = isDark ? '#FFFFFF' : colors.dark;

  if (loading) {
    return (
      <View style={[styles.card, { backgroundColor: cardBg }]}>
        <ActivityIndicator testID="loading-indicator" size="large" color={colors.primary} />
        <Text style={[styles.loadingText, { color: textColor }]}>AI가 고민 중...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={[styles.card, { backgroundColor: cardBg }]}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={onRetry}>
          <Text style={styles.retryText}>다시 시도</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!recommendation) return null;

  const { menu, emoji, reason, recipe, tip, alternatives } = recommendation;

  return (
    <View style={[styles.card, { backgroundColor: cardBg }]}>
      <Text style={styles.emoji}>{emoji}</Text>
      <Text style={[styles.menuName, { color: textColor }]}>{menu}</Text>
      <Text style={[styles.reason, { color: textColor }]}>{reason}</Text>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: textColor }]}>🍳 레시피</Text>
        {recipe.map((step, i) => (
          <Text key={i} style={[styles.step, { color: textColor }]}>{`${i + 1}. ${step}`}</Text>
        ))}
      </View>

      <View style={[styles.tipBox, { backgroundColor: colors.accent }]}>
        <Text style={styles.tipText}>{`💡 ${tip}`}</Text>
      </View>

      <Text style={[styles.altTitle, { color: textColor }]}>대안 메뉴</Text>
      <View style={styles.altRow}>
        {alternatives.map((alt) => (
          <View key={alt} style={styles.altTag}>
            <Text style={styles.altText}>{alt}</Text>
          </View>
        ))}
      </View>

      <TouchableOpacity style={styles.confirmBtn} onPress={onConfirm}>
        <Text style={styles.confirmText}>이 메뉴로 결정!</Text>
      </TouchableOpacity>
      <TouchableOpacity style={styles.retryBtn} onPress={onRetry}>
        <Text style={styles.retryText}>다시 추천</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 16, padding: 24, margin: 16,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08, shadowRadius: 8, elevation: 3, alignItems: 'center',
  },
  emoji: { fontSize: 64, marginBottom: 8 },
  menuName: { fontSize: 28, fontWeight: '700', marginBottom: 8 },
  reason: { fontSize: 16, textAlign: 'center', marginBottom: 16, opacity: 0.8 },
  section: { alignSelf: 'stretch', marginBottom: 16 },
  sectionTitle: { fontSize: 16, fontWeight: '600', marginBottom: 8 },
  step: { fontSize: 14, marginBottom: 4, lineHeight: 22 },
  tipBox: { borderRadius: 12, padding: 12, marginBottom: 16, alignSelf: 'stretch' },
  tipText: { fontSize: 14, color: colors.dark },
  altTitle: { fontSize: 14, fontWeight: '600', marginBottom: 8 },
  altRow: { flexDirection: 'row', marginBottom: 20 },
  altTag: {
    backgroundColor: colors.surface, borderRadius: 12,
    paddingVertical: 6, paddingHorizontal: 12, marginHorizontal: 4,
    borderWidth: 1, borderColor: colors.border,
  },
  altText: { fontSize: 13, color: colors.dark },
  confirmBtn: {
    backgroundColor: colors.primary, borderRadius: 12,
    paddingVertical: 14, alignSelf: 'stretch', alignItems: 'center', marginBottom: 10,
  },
  confirmText: { color: '#FFFFFF', fontSize: 17, fontWeight: '700' },
  retryBtn: {
    borderRadius: 12, paddingVertical: 12,
    borderWidth: 1.5, borderColor: colors.border,
    alignSelf: 'stretch', alignItems: 'center',
  },
  retryText: { color: colors.dark, fontSize: 15 },
  loadingText: { marginTop: 16, fontSize: 16 },
  errorText: { color: '#e74c3c', fontSize: 16, marginBottom: 16, textAlign: 'center' },
});
