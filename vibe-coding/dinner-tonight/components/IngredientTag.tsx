import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors } from '../constants/theme';

interface Props {
  name: string;
  onRemove: (name: string) => void;
}

export function IngredientTag({ name, onRemove }: Props) {
  return (
    <View style={styles.tag}>
      <Text style={styles.name}>{name}</Text>
      <TouchableOpacity
        testID="remove-button"
        onPress={() => onRemove(name)}
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      >
        <Text style={styles.x}>×</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  tag: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.accentStrong,
    borderRadius: 24,
    paddingVertical: 8,
    paddingLeft: 14,
    paddingRight: 10,
  },
  name: { fontSize: 14, color: colors.primaryDark, fontWeight: '600', marginRight: 6 },
  x: { fontSize: 16, color: colors.primaryDark, fontWeight: '700', lineHeight: 18 },
});
