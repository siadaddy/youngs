import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors } from '../constants/theme';

interface Props {
  label: string;
  options: string[];
  value: string | null;
  onChange: (value: string) => void;
  isDark?: boolean;
}

export function ConditionPicker({ label, options, value, onChange, isDark = false }: Props) {
  return (
    <View style={styles.container}>
      <Text style={[styles.label, { color: isDark ? '#FFF' : colors.dark }]}>{label}</Text>
      <View style={styles.row}>
        {options.map((option) => {
          const selected = value === option;
          return (
            <TouchableOpacity
              key={option}
              style={[
                styles.option,
                {
                  backgroundColor: selected ? colors.primary : (isDark ? colors.surfaceDark : '#F2F2F7'),
                  borderColor: selected ? colors.primary : 'transparent',
                },
              ]}
              onPress={() => onChange(option)}
              activeOpacity={0.7}
            >
              <Text style={[styles.optionText, { color: selected ? '#FFF' : (isDark ? '#DDD' : '#555') }]}>
                {option}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginBottom: 18 },
  label: { fontSize: 13, fontWeight: '700', letterSpacing: 0.5, marginBottom: 10, textTransform: 'uppercase', opacity: 0.6 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  option: {
    paddingVertical: 10,
    paddingHorizontal: 18,
    borderRadius: 24,
    borderWidth: 1.5,
  },
  optionText: { fontSize: 15, fontWeight: '600' },
});
