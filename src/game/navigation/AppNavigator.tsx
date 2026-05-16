// ============================================================
// AppNavigator — Main Navigation Wiring
// ============================================================
import React from 'react';
import { Text } from 'react-native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

import { useGameStore } from '../store';
import { RootStackParamList, MainTabParamList } from '../../types/navigation';

import StartScreen from '../screens/StartScreen';
import MainHubScreen from '../screens/MainHubScreen';
import SquadScreen from '../screens/SquadScreen';
import TacticsScreen from '../screens/TacticsScreen';
import TransferScreen from '../screens/TransferScreen';
import LeagueScreen from '../screens/LeagueScreen';
import MatchDayScreen from '../screens/MatchDayScreen';
import TrainingScreen from '../screens/TrainingScreen';
import FinanceScreen from '../screens/FinanceScreen';
import ScoutingScreen from '../screens/ScoutingScreen';
import PressScreen from '../screens/PressScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();

function TabIcon({ icon, focused }: { icon: string; focused: boolean }) {
  return (
    <Text style={{ fontSize: 18, opacity: focused ? 1 : 0.45 }}>{icon}</Text>
  );
}

function MainTabs() {
  const pendingPress = useGameStore((s) => s.pendingPressConference);

  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#0d0d1a',
          borderTopColor: '#1a1a2e',
          borderTopWidth: 1,
          height: 60,
          paddingBottom: 8,
        },
        tabBarActiveTintColor: '#00ff88',
        tabBarInactiveTintColor: '#444',
        tabBarLabelStyle: {
          fontSize: 9,
          fontWeight: '700',
          letterSpacing: 0.5,
        },
      }}
    >
      <Tab.Screen
        name="Hub"
        component={MainHubScreen}
        options={{
          tabBarLabel: 'HUB',
          tabBarIcon: ({ focused }) => <TabIcon icon="🏠" focused={focused} />,
          tabBarBadge: pendingPress ? '!' : undefined,
          tabBarBadgeStyle: { backgroundColor: '#ff6600', color: '#fff', fontSize: 9 },
        }}
      />
      <Tab.Screen
        name="Squad"
        component={SquadScreen}
        options={{
          tabBarLabel: 'ELENCO',
          tabBarIcon: ({ focused }) => <TabIcon icon="👥" focused={focused} />,
        }}
      />
      <Tab.Screen
        name="Tactics"
        component={TacticsScreen}
        options={{
          tabBarLabel: 'TÁTICAS',
          tabBarIcon: ({ focused }) => (
            <Text style={{ fontSize: 12, fontWeight: '900', opacity: focused ? 1 : 0.45, color: focused ? '#00ff88' : '#444' }}>TÁT</Text>
          ),
        }}
      />
      <Tab.Screen
        name="Transfer"
        component={TransferScreen}
        options={{
          tabBarLabel: 'MERCADO',
          tabBarIcon: ({ focused }) => <TabIcon icon="💱" focused={focused} />,
        }}
      />
      <Tab.Screen
        name="League"
        component={LeagueScreen}
        options={{
          tabBarLabel: 'LIGA',
          tabBarIcon: ({ focused }) => <TabIcon icon="🏆" focused={focused} />,
        }}
      />
    </Tab.Navigator>
  );
}

export default function AppNavigator() {
  const userClubId = useGameStore((s) => s.userClubId);

  return (
    <Stack.Navigator
      screenOptions={{ headerShown: false, animation: 'slide_from_right' }}
      initialRouteName={userClubId ? 'Main' : 'Start'}
    >
      <Stack.Screen name="Start" component={StartScreen} />
      <Stack.Screen name="Main" component={MainTabs} />
      <Stack.Screen
        name="MatchDay"
        component={MatchDayScreen}
        options={{ animation: 'slide_from_bottom' }}
      />
      <Stack.Screen name="Training" component={TrainingScreen} />
      <Stack.Screen name="Finance" component={FinanceScreen} />
      <Stack.Screen name="Scouting" component={ScoutingScreen} />
      <Stack.Screen
        name="Press"
        component={PressScreen}
        options={{ animation: 'slide_from_bottom' }}
      />
    </Stack.Navigator>
  );
}
