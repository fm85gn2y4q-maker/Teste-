// ============================================================
// Championship Manager 03/04 Clone — Core Type Definitions
// ============================================================

// -------------------------------------------------------
// Player Attributes (each 1-20)
// -------------------------------------------------------
export interface PlayerAttributes {
  // Technical
  passing: number;
  crossing: number;
  dribbling: number;
  finishing: number;
  firstTouch: number;
  heading: number;
  longShots: number;
  marking: number;
  tackling: number;
  technique: number;
  corners: number;
  freekicks: number;
  penalties: number;
  longPassing: number;
  // Mental
  aggression: number;
  anticipation: number;
  bravery: number;
  composure: number;
  concentration: number;
  creativity: number;
  decisions: number;
  determination: number;
  flair: number;
  influence: number;
  offTheBall: number;
  positioning: number;
  teamwork: number;
  workRate: number;
  // Physical
  acceleration: number;
  agility: number;
  balance: number;
  jumping: number;
  naturalFitness: number;
  pace: number;
  stamina: number;
  strength: number;
  // Goalkeeper specific
  aerial: number;
  command: number;
  communication: number;
  eccentricity: number;
  handling: number;
  kicking: number;
  oneOnOnes: number;
  reflexes: number;
  throwing: number;
}

// -------------------------------------------------------
// Hidden Attributes (each 1-20)
// -------------------------------------------------------
export interface HiddenAttributes {
  consistency: number;       // how consistently player performs
  importantMatches: number;  // performance in big games
  injuryProneness: number;   // higher = more injuries
  versatility: number;       // adapts to new positions
  ambition: number;          // career ambition
  loyalty: number;           // loyalty to club
  pressure: number;          // handles pressure
  professionalism: number;   // training attitude
}

// -------------------------------------------------------
// Enumerations & Simple Types
// -------------------------------------------------------
export type Position =
  | 'GK'
  | 'SW'
  | 'DC'
  | 'DL'
  | 'DR'
  | 'WBL'
  | 'WBR'
  | 'DM'
  | 'MC'
  | 'ML'
  | 'MR'
  | 'AMC'
  | 'AML'
  | 'AMR'
  | 'SC';

export type Foot = 'Right' | 'Left' | 'Both';
export type Nationality = string;

export type PlayerCondition = 'Fit' | 'Carrying Knock' | 'Injured' | 'Suspended';

// -------------------------------------------------------
// Player
// -------------------------------------------------------
export interface Player {
  id: string;
  name: string;
  age: number;
  nationality: Nationality;
  position: Position;
  secondaryPositions: Position[];
  foot: Foot;
  attributes: PlayerAttributes;
  hidden: HiddenAttributes;
  value: number;              // transfer value in R$
  wage: number;               // weekly wage in R$
  contractExpiry: string;     // "YYYY-MM-DD"
  clubId: string;
  morale: number;             // 1-10
  fitness: number;            // 0-100
  injured: boolean;
  injuryDaysRemaining: number;
  injuryDescription: string;
  form: number[];             // last 5 match ratings
  currentRating: number;      // average of form
  scoutedBy: string[];        // club IDs that scouted this player
  isScoutKnown: boolean;      // player known to user club
  condition: PlayerCondition;
  yellowCards: number;
  redCards: number;
  goals: number;
  assists: number;
  appearances: number;
}

// -------------------------------------------------------
// Tactics
// -------------------------------------------------------
export type Formation =
  | '4-4-2'
  | '4-3-3'
  | '4-5-1'
  | '3-5-2'
  | '5-3-2'
  | '4-4-1-1'
  | '4-1-4-1'
  | '3-4-3';

export interface TacticInstruction {
  mentality: 'Defensive' | 'Normal' | 'Attacking' | 'Overloading';
  tempo: 'Slow' | 'Normal' | 'Fast';
  passingStyle: 'Short' | 'Mixed' | 'Long';
  pressing: 'Low' | 'Medium' | 'High';
  width: 'Narrow' | 'Normal' | 'Wide';
  focus: 'Left' | 'Centre' | 'Right' | 'Mixed';
  cornerRoutine: 'Near Post' | 'Far Post' | 'Edge';
  freeKickRoutine: 'Shoot' | 'Cross' | 'Short';
}

export interface Tactic {
  id: string;
  name: string;
  formation: Formation;
  instructions: TacticInstruction;
  lineup: { [position: string]: string }; // position key -> player ID
  substitutes: string[];                  // player IDs (max 7)
}

// -------------------------------------------------------
// Club Finances
// -------------------------------------------------------
export interface ClubFinances {
  balance: number;
  weeklyWages: number;
  transferIncome: number;
  transferExpenditure: number;
  matchRevenue: number;
  sponsorshipIncome: number;
}

// -------------------------------------------------------
// Club
// -------------------------------------------------------
export interface Club {
  id: string;
  name: string;
  shortName: string;
  city: string;
  reputation: number;    // 1-20
  budget: number;        // transfer budget in R$
  wageBudget: number;
  stadium: string;
  capacity: number;
  leagueId: string;
  tactics: Tactic;
  playerIds: string[];
  finances: ClubFinances;
  boardConfidence: number; // 1-10
  fanHappiness: number;    // 1-10
}

// -------------------------------------------------------
// League Table
// -------------------------------------------------------
export interface LeagueTable {
  clubId: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
}

// -------------------------------------------------------
// Match Events & Fixtures
// -------------------------------------------------------
export type MatchEventType =
  | 'Goal'
  | 'YellowCard'
  | 'RedCard'
  | 'Substitution'
  | 'Miss'
  | 'Save'
  | 'Foul'
  | 'Corner'
  | 'Injury';

export interface MatchEvent {
  minute: number;
  type: MatchEventType;
  clubId: string;
  playerId?: string;
  assistId?: string;
  description: string;
}

export interface Fixture {
  id: string;
  homeClubId: string;
  awayClubId: string;
  date: string;       // "YYYY-MM-DD"
  leagueId: string;
  round: number;
  played: boolean;
  homeGoals?: number;
  awayGoals?: number;
  events?: MatchEvent[];
}

// -------------------------------------------------------
// Transfers
// -------------------------------------------------------
export type TransferStatus = 'Pending' | 'Accepted' | 'Rejected' | 'Countered';

export interface TransferOffer {
  id: string;
  playerId: string;
  fromClubId: string;
  toClubId: string;
  amount: number;
  status: TransferStatus;
  counterAmount?: number;
  createdAt: string;
}

// -------------------------------------------------------
// Scouting
// -------------------------------------------------------
export interface ScoutReport {
  id: string;
  playerId: string;
  scoutClubId: string;
  date: string;
  starRating: number;  // 1-5
  description: string;
  attributesRevealed: Partial<PlayerAttributes>;
}

// -------------------------------------------------------
// News & Press
// -------------------------------------------------------
export type NewsCategory = 'Transfer' | 'Match' | 'Injury' | 'Board' | 'General' | 'Press';

export interface NewsItem {
  id: string;
  date: string;
  headline: string;
  body: string;
  category: NewsCategory;
  clubId?: string;
}

export interface PressAnswer {
  text: string;
  moraleEffect: number;  // -3 to +3 on player morale
  boardEffect: number;   // -2 to +2 on board confidence
  fanEffect: number;     // -2 to +2 on fan happiness
}

export interface PressQuestion {
  id: string;
  question: string;
  options: PressAnswer[];
}

// -------------------------------------------------------
// Training
// -------------------------------------------------------
export type TrainingFocus =
  | 'Rest'
  | 'Fitness'
  | 'Tactics'
  | 'Shooting'
  | 'Defending'
  | 'Set Pieces'
  | 'Crossing'
  | 'Passing';

export interface TrainingSchedule {
  monday: TrainingFocus;
  tuesday: TrainingFocus;
  wednesday: TrainingFocus;
  thursday: TrainingFocus;
  friday: TrainingFocus;
}

// -------------------------------------------------------
// Root Game State
// -------------------------------------------------------
export interface GameState {
  currentDate: string;
  userClubId: string;
  clubs: { [id: string]: Club };
  players: { [id: string]: Player };
  fixtures: Fixture[];
  leagueTable: LeagueTable[];
  news: NewsItem[];
  transferOffers: TransferOffer[];
  scoutReports: ScoutReport[];
  trainingSchedule: TrainingSchedule;
  season: number;
  gameWeek: number;
  pendingPressConference: boolean;
  pressQuestions: PressQuestion[];
}

// -------------------------------------------------------
// Store Action signatures (used by store.ts)
// -------------------------------------------------------
export interface GameActions {
  initGame: (clubId: string) => void;
  advanceDay: () => void;
  simulateMatch: (fixtureId: string) => void;
  makeTransferOffer: (playerId: string, amount: number) => void;
  respondToOffer: (offerId: string, accept: boolean, counter?: number) => void;
  setTactic: (tactic: Tactic) => void;
  setTraining: (schedule: TrainingSchedule) => void;
  addNews: (item: NewsItem) => void;
  scoutPlayer: (playerId: string) => void;
  answerPress: (questionId: string, answerIndex: number) => void;
  saveGame: () => Promise<void>;
  loadGame: () => Promise<boolean>;
  resetGame: () => void;
}

export type FullGameStore = GameState & GameActions;
