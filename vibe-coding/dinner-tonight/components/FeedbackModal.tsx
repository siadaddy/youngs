import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  Modal, useColorScheme, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { colors, shadows } from '../constants/theme';
import { submitFeedback } from '../lib/supabase';

interface Props {
  visible: boolean;
  onClose: () => void;
}

const RATINGS = ['😞', '😕', '😐', '😊', '🤩'];

export function FeedbackModal({ visible, onClose }: Props) {
  const isDark = useColorScheme() === 'dark';
  const [rating, setRating] = useState(0);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const cardBg = isDark ? colors.cardDark : '#FFF';
  const textColor = isDark ? '#FFF' : colors.dark;
  const mutedColor = isDark ? colors.textMutedDark : colors.textMuted;

  async function handleSubmit() {
    if (!message.trim() || rating === 0) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      await submitFeedback(message.trim(), rating);
      setDone(true);
      setTimeout(() => {
        setDone(false);
        setRating(0);
        setMessage('');
        onClose();
      }, 1800);
    } catch (e: any) {
      setErrorMsg(e?.message ?? '전송에 실패했어요. 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <KeyboardAvoidingView
        style={styles.overlay}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <TouchableOpacity style={styles.backdrop} onPress={onClose} activeOpacity={1} />
        <View style={[styles.sheet, { backgroundColor: cardBg }, shadows.lg]}>
          {done ? (
            <View style={styles.doneBox}>
              <Text style={styles.doneEmoji}>🎉</Text>
              <Text style={[styles.doneText, { color: textColor }]}>피드백 고마워요!</Text>
              <Text style={[styles.doneSub, { color: mutedColor }]}>소중한 의견 잘 받았어요</Text>
            </View>
          ) : (
            <>
              <Text style={[styles.title, { color: textColor }]}>딱메 피드백 보내기</Text>
              <Text style={[styles.sub, { color: mutedColor }]}>솔직한 의견이 앱을 더 좋게 만들어요 😊</Text>

              {/* 별점 */}
              <Text style={[styles.label, { color: mutedColor }]}>만족도</Text>
              <View style={styles.ratingRow}>
                {RATINGS.map((emoji, i) => (
                  <TouchableOpacity
                    key={i}
                    onPress={() => setRating(i + 1)}
                    style={[styles.ratingBtn, rating === i + 1 && styles.ratingBtnActive]}
                  >
                    <Text style={[styles.ratingEmoji, rating === i + 1 && styles.ratingEmojiActive]}>
                      {emoji}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              {/* 텍스트 */}
              <Text style={[styles.label, { color: mutedColor }]}>내용</Text>
              <TextInput
                style={[styles.input, {
                  backgroundColor: isDark ? colors.surfaceDark : colors.surface,
                  color: textColor,
                  borderColor: isDark ? colors.borderDark : colors.border,
                }]}
                value={message}
                onChangeText={setMessage}
                placeholder="불편한 점, 좋은 점, 개선 아이디어 뭐든 좋아요"
                placeholderTextColor={mutedColor}
                multiline
                numberOfLines={4}
                textAlignVertical="top"
              />

              {errorMsg && (
                <Text style={styles.errorText}>{errorMsg}</Text>
              )}

              <TouchableOpacity
                style={[styles.submitBtn, (!message.trim() || rating === 0 || loading) && styles.disabled]}
                onPress={handleSubmit}
                disabled={!message.trim() || rating === 0 || loading}
                activeOpacity={0.85}
              >
                {loading
                  ? <ActivityIndicator color="#FFF" />
                  : <Text style={styles.submitText}>전송하기</Text>
                }
              </TouchableOpacity>

              <TouchableOpacity onPress={onClose} style={styles.cancelBtn}>
                <Text style={[styles.cancelText, { color: mutedColor }]}>취소</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, justifyContent: 'flex-end' },
  backdrop: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.4)' },
  sheet: { borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 28, paddingBottom: 40 },
  title: { fontSize: 20, fontWeight: '800', marginBottom: 6 },
  sub: { fontSize: 14, marginBottom: 24 },
  label: { fontSize: 12, fontWeight: '700', letterSpacing: 0.6, textTransform: 'uppercase', marginBottom: 10 },
  ratingRow: { flexDirection: 'row', gap: 10, marginBottom: 24 },
  ratingBtn: {
    width: 52, height: 52, borderRadius: 26,
    justifyContent: 'center', alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.05)',
  },
  ratingBtnActive: { backgroundColor: colors.primary },
  ratingEmoji: { fontSize: 26 },
  ratingEmojiActive: { transform: [{ scale: 1.2 }] },
  input: {
    borderRadius: 16, borderWidth: 1.5,
    paddingHorizontal: 16, paddingVertical: 14,
    fontSize: 15, lineHeight: 22, minHeight: 110, marginBottom: 20,
  },
  submitBtn: {
    backgroundColor: colors.primary, borderRadius: 16,
    paddingVertical: 16, alignItems: 'center', marginBottom: 10,
  },
  disabled: { opacity: 0.4 },
  submitText: { color: '#FFF', fontSize: 16, fontWeight: '800' },
  cancelBtn: { alignItems: 'center', paddingVertical: 10 },
  cancelText: { fontSize: 15, fontWeight: '600' },
  errorText: { color: colors.error, fontSize: 14, textAlign: 'center', marginBottom: 12 },
  doneBox: { alignItems: 'center', paddingVertical: 40 },
  doneEmoji: { fontSize: 56, marginBottom: 16 },
  doneText: { fontSize: 22, fontWeight: '800', marginBottom: 8 },
  doneSub: { fontSize: 15 },
});
