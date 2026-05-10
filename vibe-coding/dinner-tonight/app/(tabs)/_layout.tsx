import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useColorScheme } from 'react-native';
import { colors } from '../../constants/theme';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

function tabIcon(filled: IconName, outline: IconName) {
  return ({ color, focused }: { color: string; size: number; focused: boolean }) => (
    <Ionicons name={focused ? filled : outline} size={24} color={color} />
  );
}

export default function TabLayout() {
  const isDark = useColorScheme() === 'dark';

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: isDark ? '#555570' : '#ADADBE',
        headerShown: false,
        tabBarStyle: {
          backgroundColor: isDark ? colors.cardDark : '#FFFFFF',
          borderTopColor: isDark ? colors.borderDark : colors.border,
          borderTopWidth: 1,
          height: 60,
          paddingBottom: 8,
          paddingTop: 6,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '600',
        },
      }}
    >
      <Tabs.Screen name="index" options={{ title: '추천', tabBarIcon: tabIcon('restaurant', 'restaurant-outline') }} />
      <Tabs.Screen name="fridge" options={{ title: '냉장고', tabBarIcon: tabIcon('nutrition', 'nutrition-outline') }} />
      <Tabs.Screen name="history" options={{ title: '기록', tabBarIcon: tabIcon('calendar', 'calendar-outline') }} />
      <Tabs.Screen name="profile" options={{ title: '프로필', tabBarIcon: tabIcon('people', 'people-outline') }} />
    </Tabs>
  );
}
