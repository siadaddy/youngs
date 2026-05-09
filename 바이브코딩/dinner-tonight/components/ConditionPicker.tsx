import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { colors } from '../constants/theme';

interface Props {
  label: string;
  options: string[];
  value: string | null;
  onChange: (value: string) => void;
}

export function ConditionPicker({ label, options, value, onChange }: Props) {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        {options.map((option) => (
          <TouchableOpacity
            key={option}
            style={[styles.option, value === option && styles.selected]}
            onPress={() => onChange(option)}
          >
            <Text style={[styles.optionText, value === option && styles.selectedText]}>
              {option}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginVertical: 8 },
  label: { fontSize: 14, fontWeight: '600', color: colors.dark, marginBottom: 8 },
  option: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: colors.border,
    marginRight: 8,
    backgroundColor: colors.surface,
  },
  selected: { backgroundColor: colors.primary, borderColor: colors.primary },
  optionText: { fontSize: 14, color: colors.dark },
  selectedText: { color: '#FFFFFF', fontWeight: '600' },
});
