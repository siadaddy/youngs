import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity,
  useColorScheme, SafeAreaView,
} from 'react-native';
import { useProfileStore, FamilyMember, AgeGroup } from '../../store/useProfileStore';
import { colors } from '../../constants/theme';

const AGE_GROUPS: AgeGroup[] = ['아이', '청소년', '어른', '노인'];

export default function ProfileScreen() {
  const isDark = useColorScheme() === 'dark';
  const { members, addMember, removeMember } = useProfileStore();

  const [name, setName] = useState('');
  const [ageGroup, setAgeGroup] = useState<AgeGroup>('어른');
  const [allergyInput, setAllergyInput] = useState('');

  const cardBg = isDark ? '#2d2d2d' : '#FFF';
  const textColor = isDark ? '#FFF' : colors.dark;

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
      <View key={member.id} style={[styles.memberCard, { backgroundColor: cardBg }]}>
        <View style={styles.memberRow}>
          <Text style={[styles.memberName, { color: textColor }]}>
            {member.name} · {member.ageGroup}
          </Text>
          <TouchableOpacity onPress={() => removeMember(member.id)}>
            <Text style={styles.deleteText}>삭제</Text>
          </TouchableOpacity>
        </View>
        {member.allergies.length > 0 && (
          <Text style={styles.allergyText}>🚫 {member.allergies.join(', ')}</Text>
        )}
      </View>
    );
  }

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: isDark ? colors.backgroundDark : '#F5F5F5' }]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={[styles.title, { color: textColor }]}>👨‍👩‍👧‍👦 가족 프로필</Text>

        <View style={[styles.form, { backgroundColor: cardBg }]}>
          <Text style={[styles.label, { color: textColor }]}>이름</Text>
          <TextInput
            style={[styles.input, { color: textColor }]}
            value={name}
            onChangeText={setName}
            placeholder="이름 입력"
            placeholderTextColor="#aaa"
          />

          <Text style={[styles.label, { color: textColor }]}>나이대</Text>
          <View style={styles.ageRow}>
            {AGE_GROUPS.map((ag) => (
              <TouchableOpacity
                key={ag}
                style={[styles.ageBtn, ageGroup === ag && styles.ageBtnActive]}
                onPress={() => setAgeGroup(ag)}
              >
                <Text style={[styles.ageBtnText, ageGroup === ag && styles.ageBtnActiveText]}>{ag}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={[styles.label, { color: textColor }]}>알레르기 (쉼표로 구분)</Text>
          <TextInput
            style={[styles.input, { color: textColor }]}
            value={allergyInput}
            onChangeText={setAllergyInput}
            placeholder="예: 견과류, 새우"
            placeholderTextColor="#aaa"
          />

          <TouchableOpacity style={styles.addBtn} onPress={handleAdd}>
            <Text style={styles.addBtnText}>구성원 추가</Text>
          </TouchableOpacity>
        </View>

        {members.length > 0 && (
          <>
            <Text style={[styles.subTitle, { color: textColor }]}>등록된 구성원 ({members.length}명)</Text>
            {members.map(renderMember)}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  scroll: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 24, fontWeight: '800', marginBottom: 16 },
  form: {
    borderRadius: 16, padding: 16, marginBottom: 20,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06, shadowRadius: 4, elevation: 2,
  },
  label: { fontSize: 14, fontWeight: '600', marginBottom: 8, marginTop: 12 },
  input: {
    borderWidth: 1.5, borderColor: colors.border, borderRadius: 12,
    paddingHorizontal: 14, paddingVertical: 12, fontSize: 15,
  },
  ageRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  ageBtn: {
    paddingVertical: 8, paddingHorizontal: 14, borderRadius: 20,
    borderWidth: 1.5, borderColor: colors.border, backgroundColor: '#FFF',
  },
  ageBtnActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  ageBtnText: { fontSize: 14, color: colors.dark },
  ageBtnActiveText: { color: '#FFF', fontWeight: '600' },
  addBtn: {
    backgroundColor: colors.primary, borderRadius: 12,
    paddingVertical: 14, alignItems: 'center', marginTop: 16,
  },
  addBtnText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
  subTitle: { fontSize: 16, fontWeight: '700', marginBottom: 12 },
  memberCard: {
    borderRadius: 14, padding: 14, marginBottom: 10,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 2,
  },
  memberRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  memberName: { fontSize: 16, fontWeight: '600' },
  deleteText: { color: '#e74c3c', fontSize: 13, fontWeight: '600' },
  allergyText: { fontSize: 13, color: '#888', marginTop: 4 },
});
