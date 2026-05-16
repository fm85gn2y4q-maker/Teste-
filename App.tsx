// ============================================================
// App.tsx — Championship Manager 03/04 Clone
// ============================================================
import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import AppNavigator from './src/game/navigation/AppNavigator';

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="light" backgroundColor="#0a0a0f" />
      <AppNavigator />
    </NavigationContainer>
  );
}
