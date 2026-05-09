import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity,
  useColorScheme, SafeAreaView,
} from 'react-native';
import { IngredientTag } from '../../components/IngredientTag';
import { useFridgeStore } from '../../store/useFridgeStore';
import { COMMON_INGREDIENTS, INGREDIENT_CATEGORIES, IngredientCategory } from '../../constants/ingredients';
import { colors } from '../../constants/theme';

export default function FridgeScreen() {
  const isDark = useColorScheme() === 'dark';
  const [activeCategory, setActiveCategory] = useState<IngredientCategory>('채소');
  const [customInput, setCustomInput] = useState('');
  const { ingredients, addIngredient, removeIngredient } = useFridgeStore();

  function handleAddCustom() {
    const trimmed = customInput.trim();
    if (trimmed) { addIngredient(trimmed); setCustomInput(''); }
  }

  const cardBg = isDark ? '#2d2d2d' : '#FFF';
  const textColor = isDark ? '#FFF' : colors.dark;

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: isDark ? colors.backgroundDark : '#F5F5F5' }]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={[styles.title, { color: textColor }]}>🧊 내 냉장고</Text>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryRow}>
          {INGREDIENT_CATEGORIES.map((cat) => (
            <TouchableOpacity
              key={cat}
              style={[styles.catBtn, activeCategory === cat && styles.catActive]}
              onPress={() => setActiveCategory(cat)}
            >
              <Text style={[styles.catText, activeCategory === cat && styles.catActiveText]}>{cat}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <View style={[styles.card, { backgroundColor: cardBg }]}>
          <Text style={[styles.subTitle, { color: textColor }]}>빠른 추가</Text>
          <View style={styles.quickGrid}>
            {COMMON_INGREDIENTS[activeCategory].map((item) => {
              const isAdded = ingredients.includes(item);
              return (
                <TouchableOpacity
                  key={item}
                  style={[styles.quickBtn, isAdded && styles.quickBtnAdded]}
                  onPress={() => isAdded ? removeIngredient(item) : addIngredient(item)}
                >
                  <Text style={[styles.quickText, isAdded && styles.quickTextAdded]}>{item}</Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <View style={styles.inputRow}>
            <TextInput
              style={[styles.input, { color: textColor, borderColor: colors.border }]}
              value={customInput}
              onChangeText={setCustomInput}
              placeholder="직접 입력..."
              placeholderTextColor="#aaa"
              onSubmitEditing={handleAddCustom}
              returnKeyType="done"
            />
            <TouchableOpacity style={styles.addBtn} onPress={handleAddCustom}>
              <Text style={styles.addBtnText}>추가</Text>
            </TouchableOpacity>
          </View>
        </View>

        {ingredients.length > 0 && (
          <View style={[styles.card, { backgroundColor: cardBg }]}>
            <Text style={[styles.subTitle, { color: textColor }]}>등록된 재료 ({ingredients.length})</Text>
            <View style={styles.tagRow}>
              {ingredients.map((item) => (
                <IngredientTag key={item} name={item} onRemove={removeIngredient} />
              ))}
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  scroll: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 24, fontWeight: '800', marginBottom: 16 },
  categoryRow: { marginBottom: 12 },
  catBtn: {
    paddingVertical: 8, paddingHorizontal: 16, borderRadius: 20,
    borderWidth: 1.5, borderColor: colors.border, marginRight: 8, backgroundColor: '#FFF',
  },
  catActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  catText: { fontSize: 14, color: colors.dark },
  catActiveText: { color: '#FFF', fontWeight: '600' },
  card: {
    borderRadius: 16, padding: 16, marginBottom: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06, shadowRadius: 4, elevation: 2,
  },
  subTitle: { fontSize: 15, fontWeight: '600', marginBottom: 10 },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 12 },
  quickBtn: {
    paddingVertical: 8, paddingHorizontal: 14, borderRadius: 20,
    borderWidth: 1.5, borderColor: colors.border, margin: 4, backgroundColor: '#FFF',
  },
  quickBtnAdded: { backgroundColor: colors.primary, borderColor: colors.primary },
  quickText: { fontSize: 14, color: colors.dark },
  quickTextAdded: { color: '#FFF', fontWeight: '600' },
  inputRow: { flexDirection: 'row' },
  input: {
    flex: 1, borderRadius: 12, paddingHorizontal: 14,
    paddingVertical: 12, fontSize: 15, borderWidth: 1.5, marginRight: 8,
  },
  addBtn: { backgroundColor: colors.primary, borderRadius: 12, paddingHorizontal: 20, justifyContent: 'center' },
  addBtnText: { color: '#FFF', fontWeight: '700', fontSize: 15 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap' },
});
