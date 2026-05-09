import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../constants/theme';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

function tabIcon(name: IconName) {
  return ({ color, size }: { color: string; size: number }) => (
    <Ionicons name={name} size={size} color={color} />
  );
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: '#636e72',
        headerShown: false,
      }}
    >
      <Tabs.Screen name="index" options={{ title: '추천', tabBarIcon: tabIcon('restaurant') }} />
      <Tabs.Screen name="fridge" options={{ title: '냉장고', tabBarIcon: tabIcon('grid') }} />
      <Tabs.Screen name="history" options={{ title: '기록', tabBarIcon: tabIcon('time') }} />
      <Tabs.Screen name="profile" options={{ title: '프로필', tabBarIcon: tabIcon('people') }} />
    </Tabs>
  );
}
