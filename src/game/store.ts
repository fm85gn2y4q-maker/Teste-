// ============================================================
// Championship Manager 03/04 Clone — Zustand Game Store
// ============================================================
// NOTE: Requires @react-native-async-storage/async-storage
//       Install with: npx expo install @react-native-async-storage/async-storage

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

import {
  GameState,
  GameActions,
  FullGameStore,
  Club,
  Player,
  Fixture,
  LeagueTable,
  NewsItem,
  TransferOffer,
  ScoutReport,
  Tactic,
  TrainingSchedule,
  TrainingFocus,
  MatchEvent,
  PlayerAttributes,
  PlayerCondition,
} from './types';

import {
  CLUBS_MAP,
  PLAYERS_MAP,
  buildInitialLeagueTable,
  generateFixtures,
  PRESS_QUESTIONS,
  generateId,
} from './database';

// -------------------------------------------------------
// AsyncStorage — lazy import so web/test envs don't crash
// -------------------------------------------------------
interface IAsyncStorage {
  setItem: (key: string, value: string) => Promise<void>;
  getItem: (key: string) => Promise<string | null>;
}

// Use dynamic import pattern to avoid 'require' type error in strict mode
let AsyncStorage: IAsyncStorage | null = null;

function loadAsyncStorage(): void {
  if (AsyncStorage !== null) return;
  // Dynamic require wrapped in try/catch; will gracefully fail in envs without RN
  try {
    // We intentionally use a dynamic expression to avoid tsc complaining
    const modName = '@react-native-async-storage/async-storage';
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const mod = (Function('n', 'return require(n)') as (n: string) => { default: IAsyncStorage })(modName);
    AsyncStorage = mod.default;
  } catch {
    AsyncStorage = null;
  }
}

const SAVE_KEY = 'cm0304_game_save';

// -------------------------------------------------------
// Date Utilities
// -------------------------------------------------------
function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr);
  d.setDate(d.getDate() + days);
  return d.toISOString().split('T')[0];
}

function dayOfWeek(dateStr: string): string {
  const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  return days[new Date(dateStr).getDay()];
}

// -------------------------------------------------------
// Match Engine
// -------------------------------------------------------
function teamStrength(club: Club, players: Record<string, Player>): number {
  const lineup = Object.values(club.tactics.lineup);
  const ids: string[] = lineup.length >= 11 ? lineup.slice(0, 11) : club.playerIds.slice(0, 11);
  if (ids.length === 0) return 50;
  const total = ids.reduce((sum, id) => {
    const p = players[id];
    if (!p) return sum;
    const a = p.attributes;
    const tech = (a.passing + a.finishing + a.dribbling + a.technique + a.firstTouch) / 5;
    const men = (a.decisions + a.concentration + a.composure + a.teamwork) / 4;
    const phys = (a.pace + a.stamina + a.strength) / 3;
    return sum + (tech + men + phys) / 3;
  }, 0);
  return total / ids.length;
}

function rand(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function pickPlayer(clubId: string, clubs: Record<string, Club>, players: Record<string, Player>): Player | null {
  const club = clubs[clubId];
  if (!club) return null;
  const lineup = Object.values(club.tactics.lineup);
  const ids: string[] = lineup.length >= 11 ? lineup.slice(0, 11) : club.playerIds.slice(0, 11);
  const available = ids.map((id) => players[id]).filter((p): p is Player => Boolean(p));
  if (available.length === 0) return null;
  return available[rand(0, available.length - 1)];
}

function pickAttacker(clubId: string, clubs: Record<string, Club>, players: Record<string, Player>): Player | null {
  const club = clubs[clubId];
  if (!club) return null;
  const ids = club.playerIds.slice(0, 16);
  const attackers = ids
    .map((id) => players[id])
    .filter((p): p is Player => Boolean(p) && ['SC', 'AMC', 'AML', 'AMR', 'ML', 'MR'].includes(p.position));
  if (attackers.length === 0) return pickPlayer(clubId, clubs, players);
  return attackers[rand(0, attackers.length - 1)];
}

interface SimResult {
  homeGoals: number;
  awayGoals: number;
  events: MatchEvent[];
}

function poissonSample(lambda: number): number {
  const L = Math.exp(-lambda);
  let k = 0;
  let p = 1;
  do { k++; p *= Math.random(); } while (p > L);
  return k - 1;
}

function simulateMatchEngine(
  homeClubId: string,
  awayClubId: string,
  clubs: Record<string, Club>,
  players: Record<string, Player>,
): SimResult {
  const homeStr = teamStrength(clubs[homeClubId], players);
  const awayStr = teamStrength(clubs[awayClubId], players);
  const homeAdv = 1.15;
  const adjHome = homeStr * homeAdv;
  const adjAway = awayStr;
  const totalStr = adjHome + adjAway;

  const avgGoals = 2.6;
  const homeExpected = (adjHome / totalStr) * avgGoals * (1 + Math.random() * 0.6 - 0.3);
  const awayExpected = (adjAway / totalStr) * avgGoals * (1 + Math.random() * 0.6 - 0.3);

  const homeGoals = poissonSample(homeExpected);
  const awayGoals = poissonSample(awayExpected);

  const events: MatchEvent[] = [];
  const usedMinutes = new Set<number>();

  const pickMinute = (): number => {
    let m = rand(1, 90);
    while (usedMinutes.has(m)) m = rand(1, 90);
    usedMinutes.add(m);
    return m;
  };

  for (let g = 0; g < homeGoals; g++) {
    const scorer = pickAttacker(homeClubId, clubs, players);
    const assister = pickPlayer(homeClubId, clubs, players);
    events.push({
      minute: pickMinute(),
      type: 'Goal',
      clubId: homeClubId,
      playerId: scorer?.id,
      assistId: assister?.id !== scorer?.id ? assister?.id : undefined,
      description: scorer
        ? `Gol de ${scorer.name}!${assister && assister.id !== scorer.id ? ` Assistência de ${assister.name}.` : ''}`
        : 'Gol marcado!',
    });
  }

  for (let g = 0; g < awayGoals; g++) {
    const scorer = pickAttacker(awayClubId, clubs, players);
    const assister = pickPlayer(awayClubId, clubs, players);
    events.push({
      minute: pickMinute(),
      type: 'Goal',
      clubId: awayClubId,
      playerId: scorer?.id,
      assistId: assister?.id !== scorer?.id ? assister?.id : undefined,
      description: scorer
        ? `Gol de ${scorer.name}!${assister && assister.id !== scorer.id ? ` Assistência de ${assister.name}.` : ''}`
        : 'Gol marcado!',
    });
  }

  const yellowCount = rand(1, 4);
  for (let y = 0; y < yellowCount; y++) {
    const clubId = Math.random() > 0.5 ? homeClubId : awayClubId;
    const player = pickPlayer(clubId, clubs, players);
    events.push({
      minute: pickMinute(),
      type: 'YellowCard',
      clubId,
      playerId: player?.id,
      description: player ? `Cartão amarelo para ${player.name}.` : 'Cartão amarelo.',
    });
  }

  if (Math.random() < 0.1) {
    const clubId = Math.random() > 0.5 ? homeClubId : awayClubId;
    const player = pickPlayer(clubId, clubs, players);
    events.push({
      minute: pickMinute(),
      type: 'RedCard',
      clubId,
      playerId: player?.id,
      description: player ? `Cartão vermelho para ${player.name}!` : 'Cartão vermelho!',
    });
  }

  if (Math.random() < 0.3) {
    const clubId = Math.random() > 0.5 ? homeClubId : awayClubId;
    const player = pickPlayer(clubId, clubs, players);
    events.push({
      minute: pickMinute(),
      type: 'Injury',
      clubId,
      playerId: player?.id,
      description: player ? `${player.name} sai lesionado.` : 'Lesão no jogo.',
    });
  }

  events.sort((a, b) => a.minute - b.minute);
  return { homeGoals, awayGoals, events };
}

// -------------------------------------------------------
// Apply match events to player stats
// -------------------------------------------------------
function applyMatchEvents(
  events: MatchEvent[],
  players: Record<string, Player>,
): Record<string, Player> {
  const updated = { ...players };
  events.forEach((event) => {
    if (event.type === 'Goal' && event.playerId) {
      const p = updated[event.playerId];
      if (p) updated[event.playerId] = { ...p, goals: p.goals + 1 };
    }
    if (event.type === 'Goal' && event.assistId) {
      const p = updated[event.assistId];
      if (p) updated[event.assistId] = { ...p, assists: p.assists + 1 };
    }
    if (event.type === 'YellowCard' && event.playerId) {
      const p = updated[event.playerId];
      if (p) updated[event.playerId] = { ...p, yellowCards: p.yellowCards + 1 };
    }
    if (event.type === 'RedCard' && event.playerId) {
      const p = updated[event.playerId];
      if (p) updated[event.playerId] = { ...p, redCards: p.redCards + 1, condition: 'Suspended' as PlayerCondition };
    }
    if (event.type === 'Injury' && event.playerId) {
      const p = updated[event.playerId];
      if (p) {
        updated[event.playerId] = {
          ...p,
          injured: true,
          condition: 'Injured' as PlayerCondition,
          injuryDaysRemaining: rand(7, 30),
          injuryDescription: 'Lesão durante a partida',
        };
      }
    }
  });
  return updated;
}

// -------------------------------------------------------
// Training Effect
// -------------------------------------------------------
function applyTrainingEffect(
  players: Record<string, Player>,
  schedule: TrainingSchedule,
  dayName: string,
): Record<string, Player> {
  const scheduleRecord = schedule as unknown as Record<string, TrainingFocus>;
  const focus = scheduleRecord[dayName] as TrainingFocus | undefined;
  if (!focus || focus === 'Rest') return players;

  const updated = { ...players };
  Object.keys(updated).forEach((id) => {
    const p = { ...updated[id] };
    const profBonus = (p.hidden.professionalism - 10) * 0.02;
    const injRisk = p.hidden.injuryProneness / 200;
    const improve = Math.random() < 0.05 + profBonus;

    if (improve) {
      const attrs = { ...p.attributes };
      switch (focus) {
        case 'Fitness':
          p.fitness = Math.min(100, p.fitness + rand(1, 3));
          break;
        case 'Shooting':
          if (Math.random() < 0.3 && attrs.finishing < 20) attrs.finishing++;
          if (Math.random() < 0.2 && attrs.longShots < 20) attrs.longShots++;
          break;
        case 'Defending':
          if (Math.random() < 0.3 && attrs.tackling < 20) attrs.tackling++;
          if (Math.random() < 0.2 && attrs.marking < 20) attrs.marking++;
          break;
        case 'Passing':
          if (Math.random() < 0.3 && attrs.passing < 20) attrs.passing++;
          if (Math.random() < 0.2 && attrs.longPassing < 20) attrs.longPassing++;
          break;
        case 'Crossing':
          if (Math.random() < 0.3 && attrs.crossing < 20) attrs.crossing++;
          break;
        case 'Set Pieces':
          if (Math.random() < 0.3 && attrs.freekicks < 20) attrs.freekicks++;
          if (Math.random() < 0.2 && attrs.corners < 20) attrs.corners++;
          break;
        case 'Tactics':
          if (Math.random() < 0.3 && attrs.positioning < 20) attrs.positioning++;
          if (Math.random() < 0.2 && attrs.decisions < 20) attrs.decisions++;
          break;
        default:
          break;
      }
      p.attributes = attrs;
    }

    if (focus === 'Fitness') {
      p.fitness = Math.min(100, p.fitness + 1);
    } else if (focus !== 'Tactics') {
      p.fitness = Math.max(50, p.fitness - rand(0, 2));
    }

    if (!p.injured && Math.random() < injRisk) {
      p.injured = true;
      p.condition = 'Carrying Knock';
      p.injuryDaysRemaining = rand(3, 14);
      const descriptions = ['Distensão muscular', 'Contusão no joelho', 'Torção no tornozelo', 'Problema muscular', 'Dor na coxa'];
      p.injuryDescription = descriptions[rand(0, descriptions.length - 1)];
    }

    updated[id] = p;
  });

  return updated;
}

// -------------------------------------------------------
// Injury Tick
// -------------------------------------------------------
function tickInjuries(players: Record<string, Player>): Record<string, Player> {
  const updated = { ...players };
  Object.keys(updated).forEach((id) => {
    const p = { ...updated[id] };
    if (p.injured && p.injuryDaysRemaining > 0) {
      p.injuryDaysRemaining--;
      if (p.injuryDaysRemaining === 0) {
        p.injured = false;
        p.condition = 'Fit';
        p.injuryDescription = '';
        p.fitness = Math.max(50, p.fitness);
      }
    }
    updated[id] = p;
  });
  return updated;
}

// -------------------------------------------------------
// League Table Update
// -------------------------------------------------------
function updateLeagueTable(
  table: LeagueTable[],
  homeClubId: string,
  awayClubId: string,
  homeGoals: number,
  awayGoals: number,
): LeagueTable[] {
  return table.map((row) => {
    if (row.clubId === homeClubId) {
      const won = homeGoals > awayGoals ? 1 : 0;
      const drawn = homeGoals === awayGoals ? 1 : 0;
      const lost = homeGoals < awayGoals ? 1 : 0;
      return {
        ...row,
        played: row.played + 1,
        won: row.won + won,
        drawn: row.drawn + drawn,
        lost: row.lost + lost,
        goalsFor: row.goalsFor + homeGoals,
        goalsAgainst: row.goalsAgainst + awayGoals,
        points: row.points + won * 3 + drawn,
      };
    }
    if (row.clubId === awayClubId) {
      const won = awayGoals > homeGoals ? 1 : 0;
      const drawn = awayGoals === homeGoals ? 1 : 0;
      const lost = awayGoals < homeGoals ? 1 : 0;
      return {
        ...row,
        played: row.played + 1,
        won: row.won + won,
        drawn: row.drawn + drawn,
        lost: row.lost + lost,
        goalsFor: row.goalsFor + awayGoals,
        goalsAgainst: row.goalsAgainst + homeGoals,
        points: row.points + won * 3 + drawn,
      };
    }
    return row;
  });
}

// -------------------------------------------------------
// AI Transfer Logic
// -------------------------------------------------------
interface AITransferResult {
  clubs: Record<string, Club>;
  players: Record<string, Player>;
  news: NewsItem[];
}

function processAITransfers(state: GameState): AITransferResult {
  const clubs = { ...state.clubs };
  const players = { ...state.players };
  const news: NewsItem[] = [];

  Object.keys(clubs).forEach((clubId) => {
    if (clubId === state.userClubId) return;
    if (Math.random() > 0.02) return;

    const club = clubs[clubId];
    if (!club || club.budget < 500000) return;

    const targetClubIds = Object.keys(clubs).filter((id) => id !== clubId);
    if (targetClubIds.length === 0) return;
    const targetClubId = targetClubIds[rand(0, targetClubIds.length - 1)];
    const targetClub = clubs[targetClubId];
    if (!targetClub || targetClub.playerIds.length < 20) return;

    const candidateId = targetClub.playerIds[rand(0, targetClub.playerIds.length - 1)];
    const candidate = players[candidateId];
    if (!candidate) return;

    const offer = candidate.value * (0.8 + Math.random() * 0.4);
    if (offer > club.budget) return;

    if (Math.random() < 0.6) {
      players[candidateId] = { ...candidate, clubId };

      clubs[targetClubId] = {
        ...targetClub,
        playerIds: targetClub.playerIds.filter((id) => id !== candidateId),
        budget: targetClub.budget + offer,
        finances: { ...targetClub.finances, transferIncome: targetClub.finances.transferIncome + offer },
      };
      clubs[clubId] = {
        ...club,
        playerIds: [...club.playerIds, candidateId],
        budget: club.budget - offer,
        finances: { ...club.finances, transferExpenditure: club.finances.transferExpenditure + offer },
      };

      const formattedOffer = (offer / 1000000).toFixed(1);
      news.push({
        id: generateId('news'),
        date: state.currentDate,
        headline: `${candidate.name} assina com ${club.name}`,
        body: `${club.name} confirmou a contratação de ${candidate.name} por R$ ${formattedOffer} milhões.`,
        category: 'Transfer',
        clubId,
      });
    }
  });

  return { clubs, players, news };
}

// -------------------------------------------------------
// Default Training Schedule
// -------------------------------------------------------
const DEFAULT_TRAINING: TrainingSchedule = {
  monday: 'Fitness',
  tuesday: 'Tactics',
  wednesday: 'Shooting',
  thursday: 'Passing',
  friday: 'Set Pieces',
};

// -------------------------------------------------------
// Empty Initial State
// -------------------------------------------------------
const EMPTY_STATE: GameState = {
  currentDate: '2003-04-05',
  userClubId: '',
  clubs: {},
  players: {},
  fixtures: [],
  leagueTable: [],
  news: [],
  transferOffers: [],
  scoutReports: [],
  trainingSchedule: DEFAULT_TRAINING,
  season: 2003,
  gameWeek: 1,
  pendingPressConference: false,
  pressQuestions: [],
};

// -------------------------------------------------------
// Zustand Store
// -------------------------------------------------------
export const useGameStore = create<FullGameStore>()(
  subscribeWithSelector<FullGameStore>((set, get) => ({
    ...EMPTY_STATE,

    // --------------------------------------------------
    // initGame
    // --------------------------------------------------
    initGame: (clubId: string) => {
      const clubs: Record<string, Club> = {};
      Object.entries(CLUBS_MAP).forEach(([id, club]) => {
        clubs[id] = JSON.parse(JSON.stringify(club)) as Club;
      });

      const players: Record<string, Player> = {};
      Object.entries(PLAYERS_MAP).forEach(([id, player]) => {
        players[id] = JSON.parse(JSON.stringify(player)) as Player;
      });

      const fixtures = generateFixtures();
      const leagueTable = buildInitialLeagueTable();

      const welcomeNews: NewsItem = {
        id: generateId('news'),
        date: '2003-04-05',
        headline: `Bem-vindo ao ${clubs[clubId]?.name ?? 'clube'}!`,
        body: 'O Campeonato Brasileiro Série A 2003 começa agora. Boa sorte na temporada!',
        category: 'General',
        clubId,
      };

      const shuffled = [...PRESS_QUESTIONS].sort(() => Math.random() - 0.5);
      const pressQuestions = shuffled.slice(0, 3);

      set({
        ...EMPTY_STATE,
        currentDate: '2003-04-05',
        userClubId: clubId,
        clubs,
        players,
        fixtures,
        leagueTable,
        news: [welcomeNews],
        trainingSchedule: { ...DEFAULT_TRAINING },
        season: 2003,
        gameWeek: 1,
        pendingPressConference: true,
        pressQuestions,
      });
    },

    // --------------------------------------------------
    // advanceDay
    // --------------------------------------------------
    advanceDay: () => {
      const state = get();
      const nextDate = addDays(state.currentDate, 1);
      const dow = dayOfWeek(nextDate);

      let players = state.players;
      if (['monday', 'tuesday', 'wednesday', 'thursday', 'friday'].includes(dow)) {
        players = applyTrainingEffect(players, state.trainingSchedule, dow);
      }
      players = tickInjuries(players);

      const aiResult = processAITransfers({ ...state, players });
      const clubs = aiResult.clubs;
      let updatedPlayers = aiResult.players;
      const aiNews = aiResult.news;

      const todayFixtures = state.fixtures.filter((f) => f.date === nextDate && !f.played);
      const newNews: NewsItem[] = [...aiNews];

      const updatedFixtures = [...state.fixtures];
      let updatedTable = [...state.leagueTable];

      todayFixtures.forEach((fixture) => {
        if (fixture.homeClubId === state.userClubId || fixture.awayClubId === state.userClubId) {
          return;
        }

        const result = simulateMatchEngine(
          fixture.homeClubId,
          fixture.awayClubId,
          clubs,
          updatedPlayers,
        );

        const idx = updatedFixtures.findIndex((f) => f.id === fixture.id);
        if (idx !== -1) {
          updatedFixtures[idx] = {
            ...fixture,
            played: true,
            homeGoals: result.homeGoals,
            awayGoals: result.awayGoals,
            events: result.events,
          };
        }

        updatedTable = updateLeagueTable(
          updatedTable,
          fixture.homeClubId,
          fixture.awayClubId,
          result.homeGoals,
          result.awayGoals,
        );

        updatedPlayers = applyMatchEvents(result.events, updatedPlayers);

        const homeName = clubs[fixture.homeClubId]?.shortName ?? fixture.homeClubId;
        const awayName = clubs[fixture.awayClubId]?.shortName ?? fixture.awayClubId;
        newNews.push({
          id: generateId('news'),
          date: nextDate,
          headline: `${homeName} ${result.homeGoals}-${result.awayGoals} ${awayName}`,
          body: `Resultado da rodada: ${homeName} ${result.homeGoals} x ${result.awayGoals} ${awayName}.`,
          category: 'Match',
        });
      });

      // Weekly wage deduction every Sunday
      const updatedClubs = { ...clubs };
      if (dow === 'sunday') {
        Object.keys(updatedClubs).forEach((clubId) => {
          const club = updatedClubs[clubId];
          updatedClubs[clubId] = {
            ...club,
            budget: club.budget - club.finances.weeklyWages,
          };
        });
      }

      const playedCount = updatedFixtures.filter((f) => f.played).length;
      const newGameWeek = Math.floor(playedCount / Math.max(1, state.leagueTable.length / 2)) + 1;

      const daysDiff = Math.floor(
        (new Date(nextDate).getTime() - new Date('2003-04-05').getTime()) / (1000 * 60 * 60 * 24),
      );
      const pendingPress = daysDiff > 0 && daysDiff % 7 === 0;
      const pressQuestions = pendingPress
        ? [...PRESS_QUESTIONS].sort(() => Math.random() - 0.5).slice(0, 3)
        : state.pressQuestions;

      set({
        currentDate: nextDate,
        players: { ...updatedPlayers },
        clubs: updatedClubs,
        fixtures: updatedFixtures,
        leagueTable: updatedTable,
        news: [...newNews, ...state.news].slice(0, 200),
        gameWeek: newGameWeek,
        pendingPressConference: pendingPress || state.pendingPressConference,
        pressQuestions,
      });
    },

    // --------------------------------------------------
    // simulateMatch
    // --------------------------------------------------
    simulateMatch: (fixtureId: string) => {
      const state = get();
      const fixture = state.fixtures.find((f) => f.id === fixtureId);
      if (!fixture || fixture.played) return;

      const result = simulateMatchEngine(
        fixture.homeClubId,
        fixture.awayClubId,
        state.clubs,
        state.players,
      );

      const updatedFixtures = state.fixtures.map((f) =>
        f.id === fixtureId
          ? { ...f, played: true, homeGoals: result.homeGoals, awayGoals: result.awayGoals, events: result.events }
          : f,
      );

      const updatedTable = updateLeagueTable(
        [...state.leagueTable],
        fixture.homeClubId,
        fixture.awayClubId,
        result.homeGoals,
        result.awayGoals,
      );

      let updatedPlayers = applyMatchEvents(result.events, { ...state.players });

      // Update appearance counts for lineup players
      const userClub = state.clubs[state.userClubId];
      if (userClub) {
        const lineupIds = Object.values(userClub.tactics.lineup).slice(0, 11);
        lineupIds.forEach((id) => {
          const p = updatedPlayers[id];
          if (p) updatedPlayers[id] = { ...p, appearances: p.appearances + 1 };
        });
      }

      const homeName = state.clubs[fixture.homeClubId]?.shortName ?? fixture.homeClubId;
      const awayName = state.clubs[fixture.awayClubId]?.shortName ?? fixture.awayClubId;
      const resultDesc =
        result.homeGoals > result.awayGoals
          ? `${homeName} vence por ${result.homeGoals}-${result.awayGoals}!`
          : result.homeGoals < result.awayGoals
          ? `${awayName} vence por ${result.awayGoals}-${result.homeGoals}!`
          : `Empate em ${result.homeGoals}-${result.awayGoals}!`;

      const matchNews: NewsItem = {
        id: generateId('news'),
        date: state.currentDate,
        headline: `${homeName} ${result.homeGoals}-${result.awayGoals} ${awayName}`,
        body: resultDesc,
        category: 'Match',
        clubId: state.userClubId,
      };

      set({
        fixtures: updatedFixtures,
        leagueTable: updatedTable,
        players: updatedPlayers,
        news: [matchNews, ...state.news].slice(0, 200),
      });
    },

    // --------------------------------------------------
    // makeTransferOffer
    // --------------------------------------------------
    makeTransferOffer: (playerId: string, amount: number) => {
      const state = get();
      const player = state.players[playerId];
      if (!player) return;

      const userClub = state.clubs[state.userClubId];
      if (!userClub || userClub.budget < amount) return;

      const offer: TransferOffer = {
        id: generateId('off'),
        playerId,
        fromClubId: state.userClubId,
        toClubId: player.clubId,
        amount,
        status: 'Pending',
        createdAt: state.currentDate,
      };

      const valueRatio = amount / player.value;
      let resolvedOffer: TransferOffer = { ...offer };

      if (valueRatio >= 0.85) {
        resolvedOffer = { ...resolvedOffer, status: 'Accepted' };
        const updatedPlayer: Player = { ...player, clubId: state.userClubId };
        const sellerClub = state.clubs[player.clubId];

        const updatedClubs: Record<string, Club> = {
          ...state.clubs,
          [state.userClubId]: {
            ...userClub,
            playerIds: [...userClub.playerIds, playerId],
            budget: userClub.budget - amount,
            finances: { ...userClub.finances, transferExpenditure: userClub.finances.transferExpenditure + amount },
          },
        };
        if (sellerClub) {
          updatedClubs[player.clubId] = {
            ...sellerClub,
            playerIds: sellerClub.playerIds.filter((id) => id !== playerId),
            budget: sellerClub.budget + amount,
            finances: { ...sellerClub.finances, transferIncome: sellerClub.finances.transferIncome + amount },
          };
        }

        const transferNews: NewsItem = {
          id: generateId('news'),
          date: state.currentDate,
          headline: `${player.name} assina com ${userClub.name}!`,
          body: `${userClub.name} confirma a contratação de ${player.name} por R$ ${(amount / 1000000).toFixed(1)} milhões.`,
          category: 'Transfer',
          clubId: state.userClubId,
        };

        set({
          transferOffers: [resolvedOffer, ...state.transferOffers],
          players: { ...state.players, [playerId]: updatedPlayer },
          clubs: updatedClubs,
          news: [transferNews, ...state.news].slice(0, 200),
        });
        return;
      } else if (valueRatio >= 0.6) {
        resolvedOffer = { ...resolvedOffer, status: 'Countered', counterAmount: Math.round(player.value * (0.9 + Math.random() * 0.15)) };
      } else {
        resolvedOffer = { ...resolvedOffer, status: 'Rejected' };
      }

      const statusNews: NewsItem = {
        id: generateId('news'),
        date: state.currentDate,
        headline:
          resolvedOffer.status === 'Rejected'
            ? `Proposta por ${player.name} recusada`
            : `Contra-proposta por ${player.name}`,
        body:
          resolvedOffer.status === 'Rejected'
            ? `${state.clubs[player.clubId]?.name} recusou a proposta de R$ ${(amount / 1000000).toFixed(1)} milhões por ${player.name}.`
            : `${state.clubs[player.clubId]?.name} fez uma contra-proposta de R$ ${((resolvedOffer.counterAmount ?? 0) / 1000000).toFixed(1)} milhões por ${player.name}.`,
        category: 'Transfer',
        clubId: state.userClubId,
      };

      set({
        transferOffers: [resolvedOffer, ...state.transferOffers],
        news: [statusNews, ...state.news].slice(0, 200),
      });
    },

    // --------------------------------------------------
    // respondToOffer
    // --------------------------------------------------
    respondToOffer: (offerId: string, accept: boolean, counter?: number) => {
      const state = get();
      const offer = state.transferOffers.find((o) => o.id === offerId);
      if (!offer || offer.status !== 'Pending') return;

      const player = state.players[offer.playerId];
      const userClub = state.clubs[state.userClubId];
      if (!player || !userClub) return;

      if (accept) {
        const updatedOffer: TransferOffer = { ...offer, status: 'Accepted' };
        const buyerClub = state.clubs[offer.fromClubId];
        const updatedPlayer: Player = { ...player, clubId: offer.fromClubId };

        const updatedClubs: Record<string, Club> = {
          ...state.clubs,
          [state.userClubId]: {
            ...userClub,
            playerIds: userClub.playerIds.filter((id) => id !== offer.playerId),
            budget: userClub.budget + offer.amount,
            finances: { ...userClub.finances, transferIncome: userClub.finances.transferIncome + offer.amount },
          },
        };
        if (buyerClub) {
          updatedClubs[offer.fromClubId] = {
            ...buyerClub,
            playerIds: [...buyerClub.playerIds, offer.playerId],
            budget: buyerClub.budget - offer.amount,
            finances: { ...buyerClub.finances, transferExpenditure: buyerClub.finances.transferExpenditure + offer.amount },
          };
        }

        const news: NewsItem = {
          id: generateId('news'),
          date: state.currentDate,
          headline: `${player.name} deixa ${userClub.name}`,
          body: `${player.name} foi vendido para ${state.clubs[offer.fromClubId]?.name ?? 'clube desconhecido'} por R$ ${(offer.amount / 1000000).toFixed(1)} milhões.`,
          category: 'Transfer',
          clubId: state.userClubId,
        };

        set({
          transferOffers: state.transferOffers.map((o) => (o.id === offerId ? updatedOffer : o)),
          players: { ...state.players, [offer.playerId]: updatedPlayer },
          clubs: updatedClubs,
          news: [news, ...state.news].slice(0, 200),
        });
      } else if (counter !== undefined) {
        const updatedOffer: TransferOffer = { ...offer, status: 'Countered', counterAmount: counter };
        set({ transferOffers: state.transferOffers.map((o) => (o.id === offerId ? updatedOffer : o)) });
      } else {
        const updatedOffer: TransferOffer = { ...offer, status: 'Rejected' };
        set({ transferOffers: state.transferOffers.map((o) => (o.id === offerId ? updatedOffer : o)) });
      }
    },

    // --------------------------------------------------
    // setTactic
    // --------------------------------------------------
    setTactic: (tactic: Tactic) => {
      const state = get();
      const userClub = state.clubs[state.userClubId];
      if (!userClub) return;

      set({
        clubs: {
          ...state.clubs,
          [state.userClubId]: { ...userClub, tactics: tactic },
        },
      });
    },

    // --------------------------------------------------
    // setTraining
    // --------------------------------------------------
    setTraining: (schedule: TrainingSchedule) => {
      set({ trainingSchedule: schedule });
    },

    // --------------------------------------------------
    // addNews
    // --------------------------------------------------
    addNews: (item: NewsItem) => {
      const state = get();
      set({ news: [item, ...state.news].slice(0, 200) });
    },

    // --------------------------------------------------
    // scoutPlayer
    // --------------------------------------------------
    scoutPlayer: (playerId: string) => {
      const state = get();
      const player = state.players[playerId];
      if (!player) return;

      const userClub = state.clubs[state.userClubId];
      if (!userClub || userClub.budget < 50000) return;

      const overallRating = Math.round(
        (player.attributes.passing + player.attributes.finishing + player.attributes.pace) / 3,
      );
      const starRating = Math.max(1, Math.min(5, Math.round(overallRating / 4)));

      const descriptions = [
        'Jogador mediano com potencial limitado.',
        'Jogador decente, pode ser um bom reforço para times menores.',
        'Bom jogador, pode contribuir para a equipe.',
        'Jogador acima da média, seria uma boa contratação.',
        'Jogador excepcional! Fortemente recomendado.',
      ];

      const isGK = player.position === 'GK';
      const revealedAttrs: Partial<PlayerAttributes> = isGK
        ? {
            handling: player.attributes.handling,
            reflexes: player.attributes.reflexes,
            aerial: player.attributes.aerial,
            oneOnOnes: player.attributes.oneOnOnes,
          }
        : {
            passing: player.attributes.passing,
            finishing: player.attributes.finishing,
            pace: player.attributes.pace,
            dribbling: player.attributes.dribbling,
          };

      const report: ScoutReport = {
        id: generateId('scr'),
        playerId,
        scoutClubId: state.userClubId,
        date: state.currentDate,
        starRating,
        description: descriptions[starRating - 1],
        attributesRevealed: revealedAttrs,
      };

      const updatedPlayer: Player = {
        ...player,
        isScoutKnown: true,
        scoutedBy: [...player.scoutedBy, state.userClubId],
      };

      const scoutNews: NewsItem = {
        id: generateId('news'),
        date: state.currentDate,
        headline: `Relatório de scouting: ${player.name}`,
        body: `Seu scout retornou com um relatório sobre ${player.name}. ${descriptions[starRating - 1]}`,
        category: 'General',
        clubId: state.userClubId,
      };

      set({
        scoutReports: [report, ...state.scoutReports],
        players: { ...state.players, [playerId]: updatedPlayer },
        clubs: {
          ...state.clubs,
          [state.userClubId]: { ...userClub, budget: userClub.budget - 50000 },
        },
        news: [scoutNews, ...state.news].slice(0, 200),
      });
    },

    // --------------------------------------------------
    // answerPress
    // --------------------------------------------------
    answerPress: (questionId: string, answerIndex: number) => {
      const state = get();
      const question = state.pressQuestions.find((q) => q.id === questionId);
      if (!question) return;

      const answer = question.options[answerIndex];
      if (!answer) return;

      const userClub = state.clubs[state.userClubId];
      if (!userClub) return;

      const updatedPlayers = { ...state.players };
      userClub.playerIds.forEach((id) => {
        const p = updatedPlayers[id];
        if (p) {
          updatedPlayers[id] = {
            ...p,
            morale: Math.max(1, Math.min(10, p.morale + answer.moraleEffect)),
          };
        }
      });

      const updatedClub: Club = {
        ...userClub,
        boardConfidence: Math.max(1, Math.min(10, userClub.boardConfidence + answer.boardEffect)),
        fanHappiness: Math.max(1, Math.min(10, userClub.fanHappiness + answer.fanEffect)),
      };

      const pressNews: NewsItem = {
        id: generateId('news'),
        date: state.currentDate,
        headline: 'Conferência de imprensa realizada',
        body: `Você respondeu à imprensa: "${question.question}" — "${answer.text}"`,
        category: 'Press',
        clubId: state.userClubId,
      };

      const remainingQuestions = state.pressQuestions.filter((q) => q.id !== questionId);

      set({
        players: updatedPlayers,
        clubs: { ...state.clubs, [state.userClubId]: updatedClub },
        pressQuestions: remainingQuestions,
        pendingPressConference: remainingQuestions.length > 0,
        news: [pressNews, ...state.news].slice(0, 200),
      });
    },

    // --------------------------------------------------
    // saveGame
    // --------------------------------------------------
    saveGame: async () => {
      loadAsyncStorage();
      if (!AsyncStorage) {
        console.warn('[GameStore] AsyncStorage not available. Install @react-native-async-storage/async-storage.');
        return;
      }
      const state = get();
      const saveData: GameState = {
        currentDate: state.currentDate,
        userClubId: state.userClubId,
        clubs: state.clubs,
        players: state.players,
        fixtures: state.fixtures,
        leagueTable: state.leagueTable,
        news: state.news,
        transferOffers: state.transferOffers,
        scoutReports: state.scoutReports,
        trainingSchedule: state.trainingSchedule,
        season: state.season,
        gameWeek: state.gameWeek,
        pendingPressConference: state.pendingPressConference,
        pressQuestions: state.pressQuestions,
      };
      try {
        await AsyncStorage.setItem(SAVE_KEY, JSON.stringify(saveData));
      } catch (e) {
        console.error('[GameStore] Save failed:', e);
      }
    },

    // --------------------------------------------------
    // loadGame
    // --------------------------------------------------
    loadGame: async (): Promise<boolean> => {
      loadAsyncStorage();
      if (!AsyncStorage) {
        console.warn('[GameStore] AsyncStorage not available. Install @react-native-async-storage/async-storage.');
        return false;
      }
      try {
        const raw = await AsyncStorage.getItem(SAVE_KEY);
        if (!raw) return false;
        const saveData = JSON.parse(raw) as GameState;
        set(saveData);
        return true;
      } catch (e) {
        console.error('[GameStore] Load failed:', e);
        return false;
      }
    },

    // --------------------------------------------------
    // resetGame
    // --------------------------------------------------
    resetGame: () => {
      set({ ...EMPTY_STATE });
    },
  })),
);

// -------------------------------------------------------
// Convenience Selectors
// -------------------------------------------------------
export const selectUserClub = (state: FullGameStore): Club | null =>
  state.clubs[state.userClubId] ?? null;

export const selectUserPlayers = (state: FullGameStore): Player[] => {
  const club = state.clubs[state.userClubId];
  if (!club) return [];
  return club.playerIds.map((id) => state.players[id]).filter((p): p is Player => Boolean(p));
};

export const selectSortedLeagueTable = (state: FullGameStore): LeagueTable[] =>
  [...state.leagueTable].sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    const gdA = a.goalsFor - a.goalsAgainst;
    const gdB = b.goalsFor - b.goalsAgainst;
    if (gdB !== gdA) return gdB - gdA;
    return b.goalsFor - a.goalsFor;
  });

export const selectUpcomingFixtures = (state: FullGameStore, limit = 5): Fixture[] =>
  state.fixtures
    .filter((f) => !f.played && (f.homeClubId === state.userClubId || f.awayClubId === state.userClubId))
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(0, limit);

export const selectRecentResults = (state: FullGameStore, limit = 5): Fixture[] =>
  state.fixtures
    .filter((f) => f.played && (f.homeClubId === state.userClubId || f.awayClubId === state.userClubId))
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, limit);
