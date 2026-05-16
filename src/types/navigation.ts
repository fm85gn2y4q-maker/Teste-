// ============================================================
// Navigation Type Definitions
// ============================================================

export type RootStackParamList = {
  Start: undefined;
  Main: undefined;
  MatchDay: { fixtureId: string };
  Training: undefined;
  Finance: undefined;
  Scouting: undefined;
  Press: undefined;
  // Legacy routes kept for backward compatibility
  Detail: { ticker: string };
};

export type MainTabParamList = {
  Hub: undefined;
  Squad: undefined;
  Tactics: undefined;
  Transfer: undefined;
  League: undefined;
  // Legacy tabs kept for backward compatibility
  Home: undefined;
  Settings: undefined;
};
