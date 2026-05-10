import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity, useColorScheme,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useProfileStore, FamilyMember, AgeGroup } from '../../store/useProfileStore';
import { colors, shadows } from '../../constants/theme';

const AGE_GROUPS: AgeGroup[] = ['아이', '청소년', '어른', '노인'];
const AGE_EMOJI: Record<AgeGroup, string> = { 아이: '🧒', 청소년: '👦', 어른: '🧑', 노인: '👴' };

export default function ProfileScreen() {
  const isDark = useColorScheme() === 'dark';
  const { members, addMember, removeMember } = useProfileStore();

  const [name, setName] = useState('');
  const [ageGroup, setAgeGroup] = useState<AgeGroup>('어른');
  const [allergyInput, setAllergyInput] = useState('');

  const bg = isDark ? colors.backgroundDark : '#F5F6FA';
  const cardBg = isDark ? colors.cardDark : colors.card;
  const textColor = isDark ? '#FFFFFF' : colors.dark;
  const mutedColor = isDark ? colors.textMutedDark : colors.textMuted;

  function handleAdd() {
    const trimmed = name.trim();
    if (!trimmed) return;
    addMember({
      name: trimmed,
      ageGroup,
      allergies: allergyInput.split(',').map((s) => s.trim()).filter(Boolean),
      preferences: [],
    });
    setName('');
    setAllergyInput('');
    setAgeGroup('어른');
  }

  function renderMember(member: FamilyMember) {
    return (
      <View key={member.id} style={[styles.memberCard, { backgroundColor: cardBg }, shadows.sm]}>
        <View style={[styles.memberEmoji, { backgroundColor: isDark ? '#2A2A3E' : colors.accent }]}>
          <Text style={styles.memberEmojiText}>{AGE_EMOJI[member.ageGroup]}</Text>
        </View>
        <View style={styles.memberInfo}>
          <Text style={[styles.memberName, { color: textColor }]}>{member.name}</Text>
          <Text style={[styles.memberAge, { color: mutedColor }]}>{member.ageGroup}</Text>
          {member.allergies.length > 0 && (
            <Text style={styles.allergyText}>🚫 {member.allergies.join(', ')}</Text>
          )}
        </View>
        <TouchableOpacity
          onPress={() => removeMember(member.id)}
          style={styles.deleteBtn}
        >
          <Text style={styles.deleteText}>✕</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={[styles.root, { backgroundColor: bg }]}>
      <View style={[styles.header, { backgroundColor: isDark ? colors.cardDark : '#FFF' }, shadows.sm]}>
        <SafeAreaView edges={['top']}>
          <Text style={[styles.headerTitle, { color: textColor }]}>가족 프로필 👨‍👩‍👧‍👦</Text>
          <Text style={[styles.headerSub, { color: mutedColor }]}>
            {members.length > 0 ? `${members.length}명 등록됨` : '가족을 추가하면 AI가 맞춰 추천해요'}
          </Text>
        </SafeAreaView>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Add form */}
        <View style={[styles.card, { backgroundColor: cardBg }, shadows.sm]}>
          <Text style={[styles.sectionTitle, { color: mutedColor }]}>구성원 추가</Text>

          <Text style={[styles.label, { color: textColor }]}>이름</Text>
          <TextInput
            style={[styles.input, { color: textColor, backgroundColor: isDark ? colors.surfaceDark : '#F8F8F8' }]}
            value={name}
            onChangeText={setName}
            placeholder="이름 입력"
            placeholderTextColor={mutedColor}
          />

          <Text style={[styles.label, { color: textColor }]}>나이대</Text>
          <View style={styles.ageRow}>
            {AGE_GROUPS.map((ag) => (
              <TouchableOpacity
                key={ag}
                style={[
                  styles.ageBtn,
                  { backgroundColor: ageGroup === ag ? colors.primary : (isDark ? colors.surfaceDark : '#F2F2F7') },
                ]}
                onPress={() => setAgeGroup(ag)}
                activeOpacity={0.7}
              >
                <Text style={styles.ageBtnEmoji}>{AGE_EMOJI[ag]}</Text>
                <Text style={[styles.ageBtnText, { color: ageGroup === ag ? '#FFF' : mutedColor }]}>{ag}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={[styles.label, { color: textColor }]}>알레르기 <Text style={{ color: mutedColor, fontWeight: '400' }}>(쉼표로 구분)</Text></Text>
          <TextInput
            style={[styles.input, { color: textColor, backgroundColor: isDark ? colors.surfaceDark : '#F8F8F8' }]}
            value={allergyInput}
            onChangeText={setAllergyInput}
            placeholder="예: 견과류, 새우"
            placeholderTextColor={mutedColor}
          />

          <TouchableOpacity
            style={[styles.addBtn, !name.trim() && styles.addBtnDisabled, shadows.md]}
            onPress={handleAdd}
            disabled={!name.trim()}
            activeOpacity={0.85}
          >
            <Text style={styles.addBtnText}>+ 구성원 추가</Text>
          </TouchableOpacity>
        </View>

        {/* Member list */}
        {members.length > 0 && (
          <View>
            <Text style={[styles.sectionHeader, { color: mutedColor }]}>등록된 구성원</Text>
            {members.map(renderMember)}
          </View>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: { paddingHorizontal: 24, paddingBottom: 16 },
  headerTitle: { fontSize: 28, fontWeight: '800', marginTop: 8 },
  headerSub: { fontSize: 14, marginTop: 4, marginBottom: 4 },
  scroll: { paddingHorizontal: 20, paddingTop: 16 },
  card: { borderRadius: 24, padding: 20, marginBottom: 20 },
  sectionTitle: { fontSize: 12, fontWeight: '700', letterSpacing: 0.8, textTransform: 'uppercase', marginBottom: 16 },
  label: { fontSize: 14, fontWeight: '600', marginBottom: 8, marginTop: 16 },
  input: { borderRadius: 14, paddingHorizontal: 16, paddingVertical: 14, fontSize: 15 },
  ageRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  ageBtn: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, paddingHorizontal: 14, borderRadius: 20 },
  ageBtnEmoji: { fontSize: 16, marginRight: 6 },
  ageBtnText: { fontSize: 14, fontWeight: '600' },
  addBtn: { backgroundColor: colors.primary, borderRadius: 16, paddingVertical: 16, alignItems: 'center', marginTop: 20 },
  addBtnDisabled: { opacity: 0.4 },
  addBtnText: { color: '#FFF', fontSize: 16, fontWeight: '800' },
  sectionHeader: { fontSize: 12, fontWeight: '700', letterSpacing: 0.8, textTransform: 'uppercase', marginBottom: 12 },
  memberCard: {
    flexDirection: 'row', alignItems: 'center',
    borderRadius: 20, padding: 16, marginBottom: 10,
  },
  memberEmoji: {
    width: 52, height: 52, borderRadius: 26,
    justifyContent: 'center', alignItems: 'center', marginRight: 14,
  },
  memberEmojiText: { fontSize: 28 },
  memberInfo: { flex: 1 },
  memberName: { fontSize: 17, fontWeight: '700' },
  memberAge: { fontSize: 13, marginTop: 2 },
  allergyText: { fontSize: 13, color: colors.error, marginTop: 4 },
  deleteBtn: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: 'rgba(255,82,82,0.1)',
    justifyContent: 'center', alignItems: 'center',
  },
  deleteText: { color: colors.error, fontSize: 13, fontWeight: '700' },
});
