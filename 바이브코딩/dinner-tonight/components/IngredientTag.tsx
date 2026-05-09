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
    backgroundColor: colors.accent,
    borderRadius: 20,
    paddingVertical: 6,
    paddingLeft: 12,
    paddingRight: 8,
    margin: 4,
  },
  name: { fontSize: 14, color: colors.dark, marginRight: 4 },
  x: { fontSize: 18, color: colors.dark, lineHeight: 20 },
});
