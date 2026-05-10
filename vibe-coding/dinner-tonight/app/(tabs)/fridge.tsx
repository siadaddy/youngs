import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity, useColorScheme,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { IngredientTag } from '../../components/IngredientTag';
import { useFridgeStore } from '../../store/useFridgeStore';
import { COMMON_INGREDIENTS, INGREDIENT_CATEGORIES, IngredientCategory } from '../../constants/ingredients';
import { colors, shadows } from '../../constants/theme';

const CATEGORY_EMOJI: Record<IngredientCategory, string> = {
  육류: '🥩', 채소: '🥬', 해산물: '🦐', 유제품: '🧀', 기타: '🥫',
};

export default function FridgeScreen() {
  const isDark = useColorScheme() === 'dark';
  const [activeCategory, setActiveCategory] = useState<IngredientCategory>('채소');
  const [customInput, setCustomInput] = useState('');
  const { ingredients, addIngredient, removeIngredient } = useFridgeStore();

  function handleAddCustom() {
    const trimmed = customInput.trim();
    if (trimmed) { addIngredient(trimmed); setCustomInput(''); }
  }

  const bg = isDark ? colors.backgroundDark : '#F5F6FA';
  const cardBg = isDark ? colors.cardDark : colors.card;
  const textColor = isDark ? '#FFFFFF' : colors.dark;
  const mutedColor = isDark ? colors.textMutedDark : colors.textMuted;

  return (
    <View style={[styles.root, { backgroundColor: bg }]}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: isDark ? colors.cardDark : '#FFF' }, shadows.sm]}>
        <SafeAreaView edges={['top']}>
          <Text style={[styles.headerTitle, { color: textColor }]}>내 냉장고 🧊</Text>
          <Text style={[styles.headerSub, { color: mutedColor }]}>
            {ingredients.length > 0 ? `${ingredients.length}가지 재료 등록됨` : '재료를 추가하면 AI가 활용해요'}
          </Text>
        </SafeAreaView>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Category tabs */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryScroll} contentContainerStyle={styles.categoryContent}>
          {INGREDIENT_CATEGORIES.map((cat) => (
            <TouchableOpacity
              key={cat}
              style={[styles.catBtn, { backgroundColor: activeCategory === cat ? colors.primary : (isDark ? colors.surfaceDark : '#F2F2F7') }]}
              onPress={() => setActiveCategory(cat)}
              activeOpacity={0.8}
            >
              <Text style={styles.catEmoji}>{CATEGORY_EMOJI[cat]}</Text>
              <Text style={[styles.catText, { color: activeCategory === cat ? '#FFF' : mutedColor }]}>{cat}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Quick add grid */}
        <View style={[styles.card, { backgroundColor: cardBg }, shadows.sm]}>
          <Text style={[styles.sectionTitle, { color: mutedColor }]}>빠른 추가</Text>
          <View style={styles.quickGrid}>
            {COMMON_INGREDIENTS[activeCategory].map((item) => {
              const isAdded = ingredients.includes(item);
              return (
                <TouchableOpacity
                  key={item}
                  style={[
                    styles.quickBtn,
                    { backgroundColor: isAdded ? colors.primary : (isDark ? colors.surfaceDark : '#F2F2F7') },
                  ]}
                  onPress={() => isAdded ? removeIngredient(item) : addIngredient(item)}
                  activeOpacity={0.7}
                >
                  {isAdded && <Text style={styles.checkmark}>✓ </Text>}
                  <Text style={[styles.quickText, { color: isAdded ? '#FFF' : (isDark ? '#CCC' : '#444') }]}>{item}</Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {/* Custom input */}
          <View style={[styles.inputRow, { borderTopColor: isDark ? colors.borderDark : colors.border }]}>
            <TextInput
              style={[styles.input, { color: textColor, backgroundColor: isDark ? colors.surfaceDark : '#F8F8F8' }]}
              value={customInput}
              onChangeText={setCustomInput}
              placeholder="직접 입력..."
              placeholderTextColor={mutedColor}
              onSubmitEditing={handleAddCustom}
              returnKeyType="done"
            />
            <TouchableOpacity style={[styles.addBtn, shadows.md]} onPress={handleAddCustom}>
              <Text style={styles.addBtnText}>추가</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Registered tags */}
        {ingredients.length > 0 && (
          <View style={[styles.card, { backgroundColor: cardBg }, shadows.sm]}>
            <Text style={[styles.sectionTitle, { color: mutedColor }]}>등록된 재료 ({ingredients.length})</Text>
            <View style={styles.tagRow}>
              {ingredients.map((item) => (
                <IngredientTag key={item} name={item} onRemove={removeIngredient} />
              ))}
            </View>
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
  categoryScroll: { marginBottom: 16 },
  categoryContent: { paddingRight: 8 },
  catBtn: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 24, marginRight: 8 },
  catEmoji: { fontSize: 16, marginRight: 6 },
  catText: { fontSize: 14, fontWeight: '600' },
  card: { borderRadius: 24, padding: 20, marginBottom: 16 },
  sectionTitle: { fontSize: 12, fontWeight: '700', letterSpacing: 0.8, textTransform: 'uppercase', marginBottom: 14 },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 },
  quickBtn: { flexDirection: 'row', alignItems: 'center', paddingVertical: 9, paddingHorizontal: 14, borderRadius: 20 },
  checkmark: { color: '#FFF', fontSize: 12, fontWeight: '800' },
  quickText: { fontSize: 14, fontWeight: '500' },
  inputRow: { flexDirection: 'row', borderTopWidth: 1, paddingTop: 16 },
  input: { flex: 1, borderRadius: 14, paddingHorizontal: 16, paddingVertical: 13, fontSize: 15, marginRight: 10 },
  addBtn: { backgroundColor: colors.primary, borderRadius: 14, paddingHorizontal: 20, justifyContent: 'center' },
  addBtnText: { color: '#FFF', fontWeight: '700', fontSize: 15 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
});
