import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';

import { HomeScreen } from './src/screens/HomeScreen';
import { DetailScreen } from './src/screens/DetailScreen';
import { SettingsScreen } from './src/screens/SettingsScreen';
import { SalaryScreen } from './src/screens/SalaryScreen';
import { RootStackParamList, MainTabParamList } from './src/types/navigation';

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();

const PURPLE = '#6C3DE8';

function TabIcon({ name, focused }: { name: string; focused: boolean }) {
  const icons: Record<string, string> = {
    Home: '📈',
    Salary: '💰',
    Settings: '⚙️',
  };
  return <Text style={{ fontSize: 20, opacity: focused ? 1 : 0.5 }}>{icons[name] ?? '•'}</Text>;
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: PURPLE,
        tabBarInactiveTintColor: '#9CA3AF',
        tabBarStyle: {
          backgroundColor: '#fff',
          borderTopColor: '#F3F4F6',
          paddingBottom: 4,
        },
        tabBarIcon: ({ focused }) => <TabIcon name={route.name} focused={focused} />,
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} options={{ tabBarLabel: 'Watchlist' }} />
      <Tab.Screen name="Salary" component={SalaryScreen} options={{ tabBarLabel: 'Remuneração' }} />
      <Tab.Screen name="Settings" component={SettingsScreen} options={{ tabBarLabel: 'Config' }} />
    </Tab.Navigator>
  );
}

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="light" />
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Main" component={MainTabs} />
        <Stack.Screen
          name="Detail"
          component={DetailScreen}
          options={{ animation: 'slide_from_right' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
