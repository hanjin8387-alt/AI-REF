import React from 'react';
import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import Colors from '@/constants/Colors';

const TAB_ICONS = {
  index: { active: 'home', inactive: 'home-outline' },
  scan: { active: 'scan', inactive: 'scan-outline' },
  inventory: { active: 'cube', inactive: 'cube-outline' },
  shopping: { active: 'cart', inactive: 'cart-outline' },
  history: { active: 'time', inactive: 'time-outline' },
  alerts: { active: 'notifications', inactive: 'notifications-outline' },
} as const;

type TabName = keyof typeof TAB_ICONS;

type IconName = keyof typeof Ionicons.glyphMap;

function TabBarIcon({ name, focused }: { name: TabName; focused: boolean }) {
  const iconName: IconName = focused ? TAB_ICONS[name].active : TAB_ICONS[name].inactive;
  return (
    <View style={[styles.iconContainer, focused && styles.iconContainerActive]}>
      <Ionicons name={iconName} size={22} color={focused ? Colors.primary : Colors.gray500} />
    </View>
  );
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={() => ({
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.gray500,
        tabBarStyle: {
          backgroundColor: Colors.white,
          borderTopColor: Colors.gray200,
          height: 92,
          paddingBottom: 22,
          paddingTop: 8,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '700',
        },
        headerShown: false,
      })}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: '홈',
          tabBarIcon: ({ focused }) => <TabBarIcon name="index" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="scan"
        options={{
          title: '스캔',
          tabBarIcon: ({ focused }) => <TabBarIcon name="scan" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="inventory"
        options={{
          title: '인벤토리',
          tabBarIcon: ({ focused }) => <TabBarIcon name="inventory" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="shopping"
        options={{
          title: '장보기',
          tabBarIcon: ({ focused }) => <TabBarIcon name="shopping" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: '이력',
          tabBarIcon: ({ focused }) => <TabBarIcon name="history" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="alerts"
        options={{
          title: '알림',
          tabBarIcon: ({ focused }) => <TabBarIcon name="alerts" focused={focused} />,
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  iconContainer: {
    width: 36,
    height: 28,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconContainerActive: {
    backgroundColor: '#E8F8F2',
  },
});
