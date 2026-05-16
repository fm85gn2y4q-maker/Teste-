// ============================================================
// Championship Manager 03/04 Clone — Match Engine
// Pure functions: no side effects, returns updates only.
// ============================================================

import {
  Player,
  Club,
  Fixture,
  LeagueTable,
  NewsItem,
  MatchEvent,
  MatchEventType,
  Position,
  PlayerCondition,
} from '../types';

// -------------------------------------------------------
// Utility
// -------------------------------------------------------
function rand(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randFloat(): number {
  return Math.random();
}

/** Weighted random pick: weights is parallel array to items */
function weightedPick<T>(items: T[], weights: number[]): T | null {
  if (items.length === 0) return null;
  const total = weights.reduce((s, w) => s + w, 0);
  if (total <= 0) return items[rand(0, items.length - 1)];
  let r = randFloat() * total;
  for (let i = 0; i < items.length; i++) {
    r -= weights[i];
    if (r <= 0) return items[i];
  }
  return items[items.length - 1];
}

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

let _idCounter = 900000; // start high so IDs don't collide with database.ts
function generateId(prefix = 'id'): string {
  return `${prefix}_${(_idCounter++).toString().padStart(6, '0')}`;
}

// -------------------------------------------------------
// Commentary Templates (Portuguese)
// -------------------------------------------------------
const COMMENTARY: Record<string, string[]> = {
  Goal: [
    '{scorer} finaliza com categoria e marca o {n}º gol do jogo!',
    'QUE GOL! {scorer} não perdoa e coloca {club} à frente!',
    '{scorer} recebe de {assist} e empurra para o fundo das redes!',
    'GOOOOOL! {scorer} amplia para {club}! Que partida!',
    '{scorer} chuta cruzado e não dá chance para o goleiro!',
    'Que precisão! {scorer} encontra o ângulo e faz {club} explodir de alegria!',
    'GOOOOOL de {scorer}! {club} está em vantagem!',
  ],
  GoalNoAssist: [
    '{scorer} finaliza com categoria e marca o {n}º gol do jogo!',
    'QUE GOL! {scorer} não perdoa e coloca {club} à frente!',
    'GOOOOOL! {scorer} amplia para {club}! Que partida!',
    '{scorer} chuta cruzado e não dá chance para o goleiro!',
    'Que finalização! {scorer} bate forte e marca para {club}!',
    'GOOOOOL de {scorer}! {club} abre o placar!',
  ],
  Miss: [
    '{player} desperdiça grande oportunidade na área!',
    'Incrível! {player} perde gol feito na frente do goleiro!',
    'Que chance perdida! {player} chuta por cima do gol!',
    '{player} estava bem posicionado mas manda pela linha de fundo!',
  ],
  Save: [
    'Grande defesa do goleiro! Salva {club} por enquanto.',
    'Defesaça! O goleiro voa e evita o gol!',
    'Milagre! O goleiro pega a finalização de {player}!',
    'Incrível! O guardião evita o que seria um golaço!',
  ],
  YellowCard: [
    '{player} recebe o cartão amarelo após falta dura.',
    'Árbitro não perdoa e mostra amarelo para {player}.',
    'Cartão amarelo para {player}! A tensão aumenta em campo.',
    '{player} vai para o livro do árbitro com um carrinho perigoso.',
  ],
  RedCard: [
    'VERMELHO! {player} é expulso! {club} fica com dez homens!',
    'Que decisão polêmica! {player} toma o vermelho direto!',
    'EXPULSO! {player} deixa {club} em inferioridade numérica!',
    'Loucura em campo! {player} recebe o segundo amarelo e vai para o chuveiro!',
  ],
  Injury: [
    '{player} cai no gramado se segurando. Parece contusão séria.',
    'Preocupação para {club}: {player} pede substituição com dores.',
    '{player} deixa o campo mancando. Esperamos que não seja grave.',
    'Jogo paralisado! {player} está no chão recebendo atendimento médico.',
  ],
  Substitution: [
    '{player} entra em campo no lugar do companheiro.',
    '{club} faz mudança tática: {player} é o escolhido.',
    'Substituição em {club}: {player} ganha oportunidade.',
  ],
};

function fillTemplate(template: string, vars: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_, key) => vars[key] ?? `{${key}}`);
}

function pickTemplate(type: string): string {
  const pool = COMMENTARY[type];
  if (!pool || pool.length === 0) return '';
  return pool[rand(0, pool.length - 1)];
}

// -------------------------------------------------------
// Player Strength Calculation (CM 03/04 inspired)
// -------------------------------------------------------
/**
 * Calculates a raw weighted strength score for a player at a given position.
 * Attribute weights differ by position, then we apply morale / fitness / form.
 */
export function playerStrength(player: Player, position: Position): number {
  const a = player.attributes;
  let raw = 0;

  switch (position) {
    case 'GK':
      raw =
        a.reflexes * 3 +
        a.handling * 3 +
        a.aerial * 2 +
        a.oneOnOnes * 2 +
        a.command * 1 +
        a.pace * 1;
      break;

    case 'SW':
    case 'DC':
      raw =
        a.marking * 3 +
        a.tackling * 3 +
        a.heading * 2 +
        a.concentration * 2 +
        a.strength * 2 +
        a.pace * 1;
      break;

    case 'DL':
    case 'DR':
    case 'WBL':
    case 'WBR':
      raw =
        a.tackling * 2 +
        a.crossing * 2 +
        a.pace * 2 +
        a.stamina * 2 +
        a.workRate * 2;
      break;

    case 'DM':
      raw =
        a.tackling * 3 +
        a.marking * 2 +
        a.passing * 2 +
        a.positioning * 2 +
        a.stamina * 2;
      break;

    case 'MC':
      raw =
        a.passing * 3 +
        a.creativity * 2 +
        a.stamina * 2 +
        a.decisions * 2 +
        a.workRate * 2;
      break;

    case 'ML':
    case 'MR':
    case 'AML':
    case 'AMR':
      raw =
        a.crossing * 3 +
        a.pace * 2 +
        a.stamina * 2 +
        a.dribbling * 2 +
        a.workRate * 2;
      break;

    case 'AMC':
      raw =
        a.creativity * 3 +
        a.passing * 3 +
        a.technique * 2 +
        a.decisions * 2 +
        a.flair * 2;
      break;

    case 'SC':
      raw =
        a.finishing * 4 +
        a.pace * 2 +
        a.heading * 2 +
        a.offTheBall * 2 +
        a.composure * 2 +
        a.strength * 2;
      break;

    default:
      // Generic fallback
      raw =
        a.passing * 2 +
        a.technique * 2 +
        a.pace * 2 +
        a.stamina * 2 +
        a.decisions * 2;
      break;
  }

  // Morale effect: morale 1-10, centred on 5 → ±20%
  const moraleFactor = 0.8 + (player.morale / 10) * 0.4;

  // Fitness effect: 0-100 → 0-1
  const fitnessFactor = player.fitness / 100;

  // Form effect: last 5 ratings averaged, scale 1-10, centred on 5.5 → ±15%
  let formAvg = 6.5; // default neutral
  if (player.form.length > 0) {
    formAvg = player.form.reduce((s, r) => s + r, 0) / player.form.length;
  }
  const formFactor = 0.85 + (formAvg / 10) * 0.3;

  return raw * moraleFactor * fitnessFactor * formFactor;
}

// -------------------------------------------------------
// Team Strength (attack / defense split)
// -------------------------------------------------------
interface TeamStrengths {
  attack: number;
  defense: number;
  overall: number;
  lineup: Player[];       // resolved starters (up to 11)
  substitutes: Player[];  // resolved subs
}

const ATTACKING_POSITIONS: Position[] = ['SC', 'AMC', 'AML', 'AMR', 'ML', 'MR'];
const DEFENSIVE_POSITIONS: Position[] = ['GK', 'SW', 'DC', 'DL', 'DR', 'WBL', 'WBR', 'DM'];

function resolveLineup(club: Club, players: Record<string, Player>): { starters: Player[]; subs: Player[] } {
  const lineupIds = Object.values(club.tactics.lineup);
  const subIds = club.tactics.substitutes ?? [];

  const starters: Player[] = [];
  const seen = new Set<string>();

  for (const id of lineupIds) {
    const p = players[id];
    if (p && !seen.has(id)) {
      starters.push(p);
      seen.add(id);
    }
    if (starters.length >= 11) break;
  }

  // If not enough in tactics, fill from squad
  if (starters.length < 11) {
    for (const id of club.playerIds) {
      if (starters.length >= 11) break;
      if (seen.has(id)) continue;
      const p = players[id];
      if (p && p.condition !== 'Injured' && p.condition !== 'Suspended') {
        starters.push(p);
        seen.add(id);
      }
    }
  }

  const subs: Player[] = [];
  for (const id of subIds) {
    const p = players[id];
    if (p && !seen.has(id)) {
      subs.push(p);
      seen.add(id);
    }
  }

  return { starters, subs };
}

function teamStrengths(club: Club, players: Record<string, Player>): TeamStrengths {
  const { starters, subs } = resolveLineup(club, players);

  if (starters.length === 0) {
    return { attack: 50, defense: 50, overall: 50, lineup: [], substitutes: subs };
  }

  let attackTotal = 0;
  let defenseTotal = 0;
  let attackCount = 0;
  let defenseCount = 0;

  for (const p of starters) {
    const str = playerStrength(p, p.position);
    if (ATTACKING_POSITIONS.includes(p.position)) {
      attackTotal += str;
      attackCount++;
    } else if (DEFENSIVE_POSITIONS.includes(p.position)) {
      defenseTotal += str;
      defenseCount++;
    } else {
      // midfielders contribute half to each
      attackTotal += str * 0.5;
      defenseTotal += str * 0.5;
      attackCount += 0.5;
      defenseCount += 0.5;
    }
  }

  const attack = attackCount > 0 ? attackTotal / attackCount : 50;
  const defense = defenseCount > 0 ? defenseTotal / defenseCount : 50;
  const overall = (attack + defense) / 2;

  // Tactic mentality modifiers
  const mentality = club.tactics.instructions.mentality;
  let attackMod = 1;
  let defenseMod = 1;
  if (mentality === 'Attacking') { attackMod = 1.05; defenseMod = 0.95; }
  if (mentality === 'Overloading') { attackMod = 1.10; defenseMod = 0.88; }
  if (mentality === 'Defensive') { attackMod = 0.95; defenseMod = 1.05; }

  return {
    attack: attack * attackMod,
    defense: defense * defenseMod,
    overall,
    lineup: starters,
    substitutes: subs,
  };
}

// -------------------------------------------------------
// Player pickers weighted by attribute
// -------------------------------------------------------
function pickByWeight(players: Player[], weightFn: (p: Player) => number): Player | null {
  if (players.length === 0) return null;
  const weights = players.map(weightFn);
  return weightedPick(players, weights);
}

function pickScorer(lineup: Player[]): Player | null {
  // Scorers weighted by position and finishing / offTheBall
  return pickByWeight(lineup, (p) => {
    if (p.position === 'SC') return p.attributes.finishing * 4 + p.attributes.offTheBall;
    if (['AMC', 'AML', 'AMR'].includes(p.position)) return p.attributes.finishing * 2 + p.attributes.offTheBall * 2;
    if (['MC', 'ML', 'MR'].includes(p.position)) return p.attributes.longShots * 2 + p.attributes.finishing;
    if (['DM', 'DC', 'SW'].includes(p.position)) return p.attributes.heading + p.attributes.finishing * 0.5;
    return p.attributes.finishing * 0.5;
  });
}

function pickAssister(lineup: Player[], scorerId: string): Player | null {
  const candidates = lineup.filter((p) => p.id !== scorerId);
  return pickByWeight(candidates, (p) => {
    if (['DL', 'DR', 'WBL', 'WBR', 'ML', 'MR', 'AML', 'AMR'].includes(p.position))
      return p.attributes.crossing * 3 + p.attributes.passing;
    if (['AMC', 'MC'].includes(p.position))
      return p.attributes.creativity * 3 + p.attributes.passing * 2;
    return p.attributes.passing;
  });
}

function pickFoulCommitter(lineup: Player[]): Player | null {
  return pickByWeight(lineup, (p) => p.attributes.aggression);
}

function pickInjuryVictim(lineup: Player[]): Player | null {
  return pickByWeight(lineup, (p) => p.hidden.injuryProneness);
}

// -------------------------------------------------------
// Per-phase event simulation (5-minute phases)
// -------------------------------------------------------
interface PhaseState {
  homeLineup: Player[];
  awayLineup: Player[];
  homeYellows: Map<string, number>;  // playerId -> yellow count
  homeRedded: Set<string>;
  awayYellows: Map<string, number>;
  awayRedded: Set<string>;
  homeGoals: number;
  awayGoals: number;
  homeSubs: number;
  awaySubs: number;
  homeSusbstitutes: Player[];
  awaySusbstitutes: Player[];
  events: MatchEvent[];
}

// -------------------------------------------------------
// Main Match Simulation — phase-by-phase
// -------------------------------------------------------
export interface MatchResult {
  fixture: Fixture;
  playerUpdates: { [playerId: string]: Partial<Player> };
  leagueTableUpdates: LeagueTable[];
  newsItem: NewsItem;
}

function buildLeagueUpdates(
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

/** Match rating for a player (5-10 scale, rough approximation). */
function calculateMatchRating(
  player: Player,
  events: MatchEvent[],
  isWinner: boolean,
  isDraw: boolean,
): number {
  let rating = 6.0;
  for (const ev of events) {
    if (ev.playerId !== player.id && ev.assistId !== player.id) continue;
    if (ev.type === 'Goal' && ev.playerId === player.id) rating += 1.0;
    if (ev.type === 'Goal' && ev.assistId === player.id) rating += 0.5;
    if (ev.type === 'YellowCard' && ev.playerId === player.id) rating -= 0.3;
    if (ev.type === 'RedCard' && ev.playerId === player.id) rating -= 1.5;
    if (ev.type === 'Injury' && ev.playerId === player.id) rating -= 0.5;
  }
  if (isWinner) rating += 0.3;
  if (isDraw) rating += 0.1;
  return clamp(rating + (randFloat() * 0.6 - 0.3), 4.0, 10.0);
}

/**
 * Pure match simulation. Takes fixture + supporting state, returns all updates.
 * No mutations — caller must merge results into game state.
 */
export function simulateMatch(
  fixture: Fixture,
  clubs: { [id: string]: Club },
  players: { [id: string]: Player },
  userClubId: string,
  leagueTable: LeagueTable[],
  currentDate: string,
): MatchResult {
  const homeClub = clubs[fixture.homeClubId];
  const awayClub = clubs[fixture.awayClubId];

  if (!homeClub || !awayClub) {
    // Degenerate case: can't simulate
    const updatedFixture: Fixture = { ...fixture, played: true, homeGoals: 0, awayGoals: 0, events: [] };
    return {
      fixture: updatedFixture,
      playerUpdates: {},
      leagueTableUpdates: leagueTable,
      newsItem: {
        id: generateId('news'),
        date: currentDate,
        headline: 'Jogo não pôde ser simulado',
        body: 'Informações de clube faltando.',
        category: 'Match',
      },
    };
  }

  const homeStr = teamStrengths(homeClub, players);
  const awayStr = teamStrengths(awayClub, players);

  // Home advantage: +8% to home attack and defense probabilities
  const HOME_ADVANTAGE = 1.08;

  // Phase state
  const state: PhaseState = {
    homeLineup: [...homeStr.lineup],
    awayLineup: [...awayStr.lineup],
    homeYellows: new Map(),
    awayYellows: new Map(),
    homeRedded: new Set(),
    awayRedded: new Set(),
    homeGoals: 0,
    awayGoals: 0,
    homeSubs: 0,
    awaySubs: 0,
    homeSusbstitutes: [...homeStr.substitutes],
    awaySusbstitutes: [...awayStr.substitutes],
    events: [],
  };

  const PHASES = 18; // 18 × 5 min = 90 min
  const PHASE_DURATION = 5;
  let goalCount = 0;

  for (let phase = 0; phase < PHASES; phase++) {
    const minuteBase = phase * PHASE_DURATION + 1;
    const minute = minuteBase + rand(0, PHASE_DURATION - 1);

    const activeHomeCount = state.homeLineup.filter((p) => !state.homeRedded.has(p.id)).length;
    const activeAwayCount = state.awayLineup.filter((p) => !state.awayRedded.has(p.id)).length;

    // Adjust strength for red cards (each red card reduces effective team size)
    const homeManMod = activeHomeCount >= 11 ? 1 : activeHomeCount / 11;
    const awayManMod = activeAwayCount >= 11 ? 1 : activeAwayCount / 11;

    const effectiveHomeAttack = homeStr.attack * HOME_ADVANTAGE * homeManMod;
    const effectiveAwayDefense = awayStr.defense * awayManMod;
    const effectiveAwayAttack = awayStr.attack * awayManMod;
    const effectiveHomeDefense = homeStr.defense * HOME_ADVANTAGE * homeManMod;

    // Goal probability per phase (base 8% max, scaled by attack vs defence ratio)
    const homeGoalProb = (effectiveHomeAttack / (effectiveHomeAttack + effectiveAwayDefense)) * 0.08 * HOME_ADVANTAGE;
    const awayGoalProb = (effectiveAwayAttack / (effectiveAwayAttack + effectiveHomeDefense)) * 0.08;

    // --- Home goal attempt ---
    if (randFloat() < homeGoalProb) {
      goalCount++;
      const scorer = pickScorer(state.homeLineup.filter((p) => !state.homeRedded.has(p.id)));
      const hasAssist = randFloat() < 0.35;
      const assister = hasAssist && scorer ? pickAssister(state.homeLineup, scorer.id) : null;

      let description: string;
      if (assister && scorer) {
        description = fillTemplate(pickTemplate('Goal'), {
          scorer: scorer.name,
          assist: assister.name,
          club: homeClub.shortName,
          n: String(goalCount),
        });
      } else if (scorer) {
        description = fillTemplate(pickTemplate('GoalNoAssist'), {
          scorer: scorer.name,
          club: homeClub.shortName,
          n: String(goalCount),
        });
      } else {
        description = `Gol para ${homeClub.shortName}!`;
      }

      state.events.push({
        minute,
        type: 'Goal',
        clubId: fixture.homeClubId,
        playerId: scorer?.id,
        assistId: assister?.id,
        description,
      });
      state.homeGoals++;
    } else if (randFloat() < 0.04) {
      // Miss event
      const attacker = pickScorer(state.homeLineup.filter((p) => !state.homeRedded.has(p.id)));
      if (attacker) {
        state.events.push({
          minute,
          type: 'Miss',
          clubId: fixture.homeClubId,
          playerId: attacker.id,
          description: fillTemplate(pickTemplate('Miss'), { player: attacker.name }),
        });
      }
    } else if (randFloat() < 0.03) {
      // Save event
      const attacker = pickScorer(state.homeLineup.filter((p) => !state.homeRedded.has(p.id)));
      if (attacker) {
        state.events.push({
          minute,
          type: 'Save',
          clubId: fixture.awayClubId,
          playerId: attacker.id,
          description: fillTemplate(pickTemplate('Save'), {
            player: attacker.name,
            club: awayClub.shortName,
          }),
        });
      }
    }

    // --- Away goal attempt ---
    if (randFloat() < awayGoalProb) {
      goalCount++;
      const scorer = pickScorer(state.awayLineup.filter((p) => !state.awayRedded.has(p.id)));
      const hasAssist = randFloat() < 0.35;
      const assister = hasAssist && scorer ? pickAssister(state.awayLineup, scorer.id) : null;

      let description: string;
      if (assister && scorer) {
        description = fillTemplate(pickTemplate('Goal'), {
          scorer: scorer.name,
          assist: assister.name,
          club: awayClub.shortName,
          n: String(goalCount),
        });
      } else if (scorer) {
        description = fillTemplate(pickTemplate('GoalNoAssist'), {
          scorer: scorer.name,
          club: awayClub.shortName,
          n: String(goalCount),
        });
      } else {
        description = `Gol para ${awayClub.shortName}!`;
      }

      state.events.push({
        minute,
        type: 'Goal',
        clubId: fixture.awayClubId,
        playerId: scorer?.id,
        assistId: assister?.id,
        description,
      });
      state.awayGoals++;
    } else if (randFloat() < 0.04) {
      const attacker = pickScorer(state.awayLineup.filter((p) => !state.awayRedded.has(p.id)));
      if (attacker) {
        state.events.push({
          minute,
          type: 'Miss',
          clubId: fixture.awayClubId,
          playerId: attacker.id,
          description: fillTemplate(pickTemplate('Miss'), { player: attacker.name }),
        });
      }
    } else if (randFloat() < 0.03) {
      const attacker = pickScorer(state.awayLineup.filter((p) => !state.awayRedded.has(p.id)));
      if (attacker) {
        state.events.push({
          minute,
          type: 'Save',
          clubId: fixture.homeClubId,
          playerId: attacker.id,
          description: fillTemplate(pickTemplate('Save'), {
            player: attacker.name,
            club: homeClub.shortName,
          }),
        });
      }
    }

    // --- Disciplinary events ---
    // Home yellow card (1.5% per phase)
    if (randFloat() < 0.015) {
      const activeHome = state.homeLineup.filter((p) => !state.homeRedded.has(p.id));
      const fouler = pickFoulCommitter(activeHome);
      if (fouler) {
        const yellows = (state.homeYellows.get(fouler.id) ?? 0) + 1;
        state.homeYellows.set(fouler.id, yellows);
        if (yellows >= 2) {
          // Second yellow = red
          state.homeRedded.add(fouler.id);
          state.events.push({
            minute,
            type: 'RedCard',
            clubId: fixture.homeClubId,
            playerId: fouler.id,
            description: fillTemplate(pickTemplate('RedCard'), {
              player: fouler.name,
              club: homeClub.shortName,
            }),
          });
        } else {
          state.events.push({
            minute,
            type: 'YellowCard',
            clubId: fixture.homeClubId,
            playerId: fouler.id,
            description: fillTemplate(pickTemplate('YellowCard'), { player: fouler.name }),
          });
          // 15% chance of red on next foul (straight red override)
          if (randFloat() < 0.15) {
            state.homeRedded.add(fouler.id);
            state.events.push({
              minute: Math.min(90, minute + rand(1, 5)),
              type: 'RedCard',
              clubId: fixture.homeClubId,
              playerId: fouler.id,
              description: fillTemplate(pickTemplate('RedCard'), {
                player: fouler.name,
                club: homeClub.shortName,
              }),
            });
          }
        }
      }
    }

    // Home straight red card (0.1% per phase)
    if (randFloat() < 0.001) {
      const activeHome = state.homeLineup.filter((p) => !state.homeRedded.has(p.id));
      const offender = pickFoulCommitter(activeHome);
      if (offender) {
        state.homeRedded.add(offender.id);
        state.events.push({
          minute,
          type: 'RedCard',
          clubId: fixture.homeClubId,
          playerId: offender.id,
          description: fillTemplate(pickTemplate('RedCard'), {
            player: offender.name,
            club: homeClub.shortName,
          }),
        });
      }
    }

    // Away yellow card
    if (randFloat() < 0.015) {
      const activeAway = state.awayLineup.filter((p) => !state.awayRedded.has(p.id));
      const fouler = pickFoulCommitter(activeAway);
      if (fouler) {
        const yellows = (state.awayYellows.get(fouler.id) ?? 0) + 1;
        state.awayYellows.set(fouler.id, yellows);
        if (yellows >= 2) {
          state.awayRedded.add(fouler.id);
          state.events.push({
            minute,
            type: 'RedCard',
            clubId: fixture.awayClubId,
            playerId: fouler.id,
            description: fillTemplate(pickTemplate('RedCard'), {
              player: fouler.name,
              club: awayClub.shortName,
            }),
          });
        } else {
          state.events.push({
            minute,
            type: 'YellowCard',
            clubId: fixture.awayClubId,
            playerId: fouler.id,
            description: fillTemplate(pickTemplate('YellowCard'), { player: fouler.name }),
          });
          if (randFloat() < 0.15) {
            state.awayRedded.add(fouler.id);
            state.events.push({
              minute: Math.min(90, minute + rand(1, 5)),
              type: 'RedCard',
              clubId: fixture.awayClubId,
              playerId: fouler.id,
              description: fillTemplate(pickTemplate('RedCard'), {
                player: fouler.name,
                club: awayClub.shortName,
              }),
            });
          }
        }
      }
    }

    // Away straight red card
    if (randFloat() < 0.001) {
      const activeAway = state.awayLineup.filter((p) => !state.awayRedded.has(p.id));
      const offender = pickFoulCommitter(activeAway);
      if (offender) {
        state.awayRedded.add(offender.id);
        state.events.push({
          minute,
          type: 'RedCard',
          clubId: fixture.awayClubId,
          playerId: offender.id,
          description: fillTemplate(pickTemplate('RedCard'), {
            player: offender.name,
            club: awayClub.shortName,
          }),
        });
      }
    }

    // --- Injuries (0.8% per team per phase) ---
    if (randFloat() < 0.008) {
      const activeHome = state.homeLineup.filter((p) => !state.homeRedded.has(p.id));
      const victim = pickInjuryVictim(activeHome);
      if (victim) {
        state.events.push({
          minute,
          type: 'Injury',
          clubId: fixture.homeClubId,
          playerId: victim.id,
          description: fillTemplate(pickTemplate('Injury'), {
            player: victim.name,
            club: homeClub.shortName,
          }),
        });
        // Remove from lineup (simulate coming off)
        state.homeRedded.add(victim.id);
        // Auto-substitute if possible
        if (state.homeSubs < 3 && state.homeSusbstitutes.length > 0) {
          const sub = state.homeSusbstitutes.shift()!;
          state.homeLineup.push(sub);
          state.homeSubs++;
          state.events.push({
            minute: Math.min(90, minute + 1),
            type: 'Substitution',
            clubId: fixture.homeClubId,
            playerId: sub.id,
            description: fillTemplate(pickTemplate('Substitution'), {
              player: sub.name,
              club: homeClub.shortName,
            }),
          });
        }
      }
    }

    if (randFloat() < 0.008) {
      const activeAway = state.awayLineup.filter((p) => !state.awayRedded.has(p.id));
      const victim = pickInjuryVictim(activeAway);
      if (victim) {
        state.events.push({
          minute,
          type: 'Injury',
          clubId: fixture.awayClubId,
          playerId: victim.id,
          description: fillTemplate(pickTemplate('Injury'), {
            player: victim.name,
            club: awayClub.shortName,
          }),
        });
        state.awayRedded.add(victim.id);
        if (state.awaySubs < 3 && state.awaySusbstitutes.length > 0) {
          const sub = state.awaySusbstitutes.shift()!;
          state.awayLineup.push(sub);
          state.awaySubs++;
          state.events.push({
            minute: Math.min(90, minute + 1),
            type: 'Substitution',
            clubId: fixture.awayClubId,
            playerId: sub.id,
            description: fillTemplate(pickTemplate('Substitution'), {
              player: sub.name,
              club: awayClub.shortName,
            }),
          });
        }
      }
    }

    // --- AI Tactical substitutions (after minute 60, when losing) ---
    if (minute >= 60) {
      // Home team losing → make sub
      if (state.homeGoals < state.awayGoals && state.homeSubs < 3 && state.homeSusbstitutes.length > 0) {
        if (randFloat() < 0.3) {
          const sub = state.homeSusbstitutes.shift()!;
          const activeHome = state.homeLineup.filter((p) => !state.homeRedded.has(p.id));
          // Remove weakest non-GK player
          const outCandidates = activeHome.filter((p) => p.position !== 'GK');
          const outPlayer = pickByWeight(
            outCandidates,
            (p) => 1 / (p.attributes.stamina + 1),
          );
          if (outPlayer) {
            state.homeRedded.add(outPlayer.id);
            state.homeLineup.push(sub);
            state.homeSubs++;
            state.events.push({
              minute: Math.min(90, minute + rand(1, 3)),
              type: 'Substitution',
              clubId: fixture.homeClubId,
              playerId: sub.id,
              description: fillTemplate(pickTemplate('Substitution'), {
                player: sub.name,
                club: homeClub.shortName,
              }),
            });
          }
        }
      }

      // Away team losing → make sub
      if (state.awayGoals < state.homeGoals && state.awaySubs < 3 && state.awaySusbstitutes.length > 0) {
        if (randFloat() < 0.3) {
          const sub = state.awaySusbstitutes.shift()!;
          const activeAway = state.awayLineup.filter((p) => !state.awayRedded.has(p.id));
          const outCandidates = activeAway.filter((p) => p.position !== 'GK');
          const outPlayer = pickByWeight(
            outCandidates,
            (p) => 1 / (p.attributes.stamina + 1),
          );
          if (outPlayer) {
            state.awayRedded.add(outPlayer.id);
            state.awayLineup.push(sub);
            state.awaySubs++;
            state.events.push({
              minute: Math.min(90, minute + rand(1, 3)),
              type: 'Substitution',
              clubId: fixture.awayClubId,
              playerId: sub.id,
              description: fillTemplate(pickTemplate('Substitution'), {
                player: sub.name,
                club: awayClub.shortName,
              }),
            });
          }
        }
      }
    }
  } // end phase loop

  // Sort all events chronologically
  state.events.sort((a, b) => a.minute - b.minute);

  // -------------------------------------------------------
  // Post-match: build player updates
  // -------------------------------------------------------
  const playerUpdates: { [playerId: string]: Partial<Player> } = {};

  const homeWon = state.homeGoals > state.awayGoals;
  const awayWon = state.awayGoals > state.homeGoals;
  const isDraw = state.homeGoals === state.awayGoals;

  const allParticipants = new Map<string, { player: Player; isHome: boolean }>();
  for (const p of homeStr.lineup) allParticipants.set(p.id, { player: p, isHome: true });
  for (const p of awayStr.lineup) allParticipants.set(p.id, { player: p, isHome: false });
  // Also include subs who came on
  for (const ev of state.events) {
    if (ev.type === 'Substitution' && ev.playerId) {
      const p = players[ev.playerId];
      if (p && !allParticipants.has(p.id)) {
        allParticipants.set(p.id, { player: p, isHome: ev.clubId === fixture.homeClubId });
      }
    }
  }

  allParticipants.forEach(({ player, isHome }) => {
    const isWinner = isHome ? homeWon : awayWon;
    const matchRating = calculateMatchRating(player, state.events, isWinner, isDraw);

    const newForm = [...player.form, matchRating].slice(-5);
    const newCurrentRating = newForm.reduce((s, r) => s + r, 0) / newForm.length;

    // Count this player's events
    let goalsScored = 0;
    let assistsGiven = 0;
    let yellowsThisMatch = 0;
    let redsThisMatch = 0;
    let injuredThisMatch = false;

    for (const ev of state.events) {
      if (ev.playerId === player.id) {
        if (ev.type === 'Goal') goalsScored++;
        if (ev.type === 'YellowCard') yellowsThisMatch++;
        if (ev.type === 'RedCard') redsThisMatch++;
        if (ev.type === 'Injury') injuredThisMatch = true;
      }
      if (ev.assistId === player.id && ev.type === 'Goal') assistsGiven++;
    }

    const update: Partial<Player> = {
      appearances: player.appearances + 1,
      goals: player.goals + goalsScored,
      assists: player.assists + assistsGiven,
      yellowCards: player.yellowCards + yellowsThisMatch,
      redCards: player.redCards + redsThisMatch,
      form: newForm,
      currentRating: parseFloat(newCurrentRating.toFixed(2)),
      // Fitness drain from playing
      fitness: clamp(player.fitness - rand(5, 15), 20, 100),
    };

    if (redsThisMatch > 0) {
      update.condition = 'Suspended' as PlayerCondition;
    }

    if (injuredThisMatch) {
      update.injured = true;
      update.condition = 'Injured' as PlayerCondition;
      update.injuryDaysRemaining = rand(7, 28);
      const injuryDescriptions = [
        'Distensão muscular',
        'Contusão no joelho',
        'Torção no tornozelo',
        'Lesão na coxa',
        'Problema muscular',
        'Entorse no tornozelo',
        'Contusão na panturrilha',
      ];
      update.injuryDescription = injuryDescriptions[rand(0, injuryDescriptions.length - 1)];
    }

    // Morale update
    if (isWinner) {
      update.morale = clamp((player.morale + 1), 1, 10);
    } else if (!isDraw) {
      update.morale = clamp((player.morale - 1), 1, 10);
    }

    playerUpdates[player.id] = update;
  });

  // -------------------------------------------------------
  // League table updates
  // -------------------------------------------------------
  const leagueTableUpdates = buildLeagueUpdates(
    leagueTable,
    fixture.homeClubId,
    fixture.awayClubId,
    state.homeGoals,
    state.awayGoals,
  );

  // -------------------------------------------------------
  // News item
  // -------------------------------------------------------
  const homeName = homeClub.shortName;
  const awayName = awayClub.shortName;
  const isUserMatch =
    fixture.homeClubId === userClubId || fixture.awayClubId === userClubId;

  let headline = `${homeName} ${state.homeGoals}-${state.awayGoals} ${awayName}`;
  let body: string;

  if (state.homeGoals > state.awayGoals) {
    body = `${homeClub.name} venceu ${awayClub.name} por ${state.homeGoals} a ${state.awayGoals}`;
  } else if (state.awayGoals > state.homeGoals) {
    body = `${awayClub.name} venceu ${homeClub.name} por ${state.awayGoals} a ${state.homeGoals}`;
  } else {
    body = `${homeClub.name} e ${awayClub.name} empataram em ${state.homeGoals} a ${state.awayGoals}`;
  }

  // Add scorers summary
  const scorerEvents = state.events.filter((e) => e.type === 'Goal');
  if (scorerEvents.length > 0) {
    const scorerSummary = scorerEvents
      .map((e) => {
        const p = e.playerId ? players[e.playerId] : null;
        return p ? `${p.name} (${e.minute}')` : `Gol (${e.minute}')`;
      })
      .join(', ');
    body += `. Gols: ${scorerSummary}.`;
  } else {
    body += '.';
  }

  const newsItem: NewsItem = {
    id: generateId('news'),
    date: currentDate,
    headline,
    body,
    category: 'Match',
    clubId: isUserMatch ? userClubId : undefined,
  };

  // -------------------------------------------------------
  // Updated fixture
  // -------------------------------------------------------
  const updatedFixture: Fixture = {
    ...fixture,
    played: true,
    homeGoals: state.homeGoals,
    awayGoals: state.awayGoals,
    events: state.events,
  };

  return {
    fixture: updatedFixture,
    playerUpdates,
    leagueTableUpdates,
    newsItem,
  };
}

// -------------------------------------------------------
// applyPostMatchEffects — merges MatchResult into GameState slices
// -------------------------------------------------------
export interface PostMatchStateSlice {
  players: { [id: string]: Player };
  leagueTable: LeagueTable[];
  news: NewsItem[];
  clubs: { [id: string]: Club };
}

/**
 * Merges a MatchResult into existing state slices.
 * Also handles board confidence update for the user's club.
 */
export function applyPostMatchEffects(
  currentPlayers: { [id: string]: Player },
  currentClubs: { [id: string]: Club },
  currentLeagueTable: LeagueTable[],
  currentNews: NewsItem[],
  result: MatchResult,
  userClubId: string,
): PostMatchStateSlice {
  // Merge player updates
  const players = { ...currentPlayers };
  for (const [playerId, update] of Object.entries(result.playerUpdates)) {
    const existing = players[playerId];
    if (existing) {
      players[playerId] = { ...existing, ...update };
    }
  }

  // Update board confidence for user club
  const clubs = { ...currentClubs };
  const userClub = clubs[userClubId];
  if (userClub) {
    const isUserHome = result.fixture.homeClubId === userClubId;
    const isUserAway = result.fixture.awayClubId === userClubId;
    if (isUserHome || isUserAway) {
      const userGoals = isUserHome ? (result.fixture.homeGoals ?? 0) : (result.fixture.awayGoals ?? 0);
      const oppGoals = isUserHome ? (result.fixture.awayGoals ?? 0) : (result.fixture.homeGoals ?? 0);
      let boardDelta = 0;
      if (userGoals > oppGoals) boardDelta = 1;
      else if (userGoals < oppGoals) boardDelta = -1;

      clubs[userClubId] = {
        ...userClub,
        boardConfidence: clamp(userClub.boardConfidence + boardDelta, 1, 10),
        fanHappiness: clamp(userClub.fanHappiness + boardDelta, 1, 10),
      };
    }
  }

  return {
    players,
    clubs,
    leagueTable: result.leagueTableUpdates,
    news: [result.newsItem, ...currentNews].slice(0, 200),
  };
}

// Re-export types so store/other files can import from one place
export type { MatchEvent, MatchEventType };
