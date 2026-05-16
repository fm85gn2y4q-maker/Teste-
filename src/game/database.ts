// ============================================================
// Championship Manager 03/04 Clone — Seed Database
// Brazilian Série A (2003/04 era)
// ============================================================

import {
  Club,
  ClubFinances,
  Player,
  PlayerAttributes,
  HiddenAttributes,
  Fixture,
  LeagueTable,
  Tactic,
  Position,
  Foot,
} from './types';

// -------------------------------------------------------
// ID Generator
// -------------------------------------------------------
let _idCounter = 1;
export function generateId(prefix = 'id'): string {
  return `${prefix}_${(_idCounter++).toString().padStart(6, '0')}`;
}

// -------------------------------------------------------
// Attribute Helpers
// -------------------------------------------------------
function clamp(v: number): number {
  return Math.max(1, Math.min(20, Math.round(v)));
}

/** Build a full PlayerAttributes object from a partial spec, filling the rest with a base value. */
function makeAttrs(base: number, overrides: Partial<PlayerAttributes> = {}): PlayerAttributes {
  const defaults: PlayerAttributes = {
    // Technical
    passing: base, crossing: base, dribbling: base, finishing: base,
    firstTouch: base, heading: base, longShots: base, marking: base,
    tackling: base, technique: base, corners: base, freekicks: base,
    penalties: base, longPassing: base,
    // Mental
    aggression: base, anticipation: base, bravery: base, composure: base,
    concentration: base, creativity: base, decisions: base, determination: base,
    flair: base, influence: base, offTheBall: base, positioning: base,
    teamwork: base, workRate: base,
    // Physical
    acceleration: base, agility: base, balance: base, jumping: base,
    naturalFitness: base, pace: base, stamina: base, strength: base,
    // Goalkeeper
    aerial: base, command: base, communication: base, eccentricity: base,
    handling: base, kicking: base, oneOnOnes: base, reflexes: base, throwing: base,
  };
  const merged = { ...defaults, ...overrides };
  // Clamp all values
  (Object.keys(merged) as (keyof PlayerAttributes)[]).forEach(k => {
    merged[k] = clamp(merged[k]);
  });
  return merged;
}

function makeHidden(overrides: Partial<HiddenAttributes> = {}): HiddenAttributes {
  const defaults: HiddenAttributes = {
    consistency: 12, importantMatches: 12, injuryProneness: 8,
    versatility: 10, ambition: 12, loyalty: 12, pressure: 12, professionalism: 13,
  };
  return { ...defaults, ...overrides };
}

function makePlayer(
  clubId: string,
  name: string,
  age: number,
  position: Position,
  secondaryPositions: Position[],
  foot: Foot,
  attrs: PlayerAttributes,
  hidden: HiddenAttributes,
  value: number,
  wage: number,
  contractYears: number = 2,
): Player {
  const id = generateId('plr');
  const contractExpiry = `${2003 + contractYears}-06-30`;
  const currentRating = 6.5;
  return {
    id, name, age, nationality: 'Brazilian', position,
    secondaryPositions, foot, attributes: attrs, hidden,
    value, wage, contractExpiry, clubId,
    morale: 7, fitness: 95, injured: false,
    injuryDaysRemaining: 0, injuryDescription: '',
    form: [6.5, 6.5, 6.5, 6.5, 6.5], currentRating,
    scoutedBy: [], isScoutKnown: false, condition: 'Fit',
    yellowCards: 0, redCards: 0, goals: 0, assists: 0, appearances: 0,
  };
}

function defaultTactic(clubId: string, playerIds: string[]): Tactic {
  return {
    id: generateId('tac'),
    name: '4-4-2 Normal',
    formation: '4-4-2',
    instructions: {
      mentality: 'Normal', tempo: 'Normal', passingStyle: 'Mixed',
      pressing: 'Medium', width: 'Normal', focus: 'Mixed',
      cornerRoutine: 'Far Post', freeKickRoutine: 'Cross',
    },
    lineup: {},
    substitutes: playerIds.slice(11, 18),
  };
}

function defaultFinances(balance: number, wages: number, sponsorship: number): ClubFinances {
  return {
    balance, weeklyWages: wages, transferIncome: 0,
    transferExpenditure: 0, matchRevenue: 0, sponsorshipIncome: sponsorship,
  };
}

// ============================================================
// PLAYERS — organised per club
// ============================================================

// -----------------------------------------------------------------
// 1. CRUZEIRO (top-tier: attribute base ~14-15)
// -----------------------------------------------------------------
const cruzPlayers: Player[] = [
  // GK
  makePlayer('cruzeiro', 'Fábio Machado', 23, 'GK', [], 'Right',
    makeAttrs(9, { aerial:16, command:15, communication:14, handling:16, kicking:13, oneOnOnes:15, reflexes:17, throwing:14, concentration:15, positioning:14, decisions:14 }),
    makeHidden({ consistency:15, importantMatches:14 }), 4500000, 18000, 3),
  makePlayer('cruzeiro', 'Rodrigo Galvão', 28, 'GK', [], 'Right',
    makeAttrs(8, { aerial:14, command:13, handling:14, oneOnOnes:13, reflexes:14, communication:13 }),
    makeHidden({ consistency:13 }), 800000, 8000, 2),

  // DC
  makePlayer('cruzeiro', 'Léo Moura', 25, 'DC', ['DL'], 'Left',
    makeAttrs(11, { marking:16, tackling:15, heading:15, concentration:15, positioning:15, strength:15, jumping:14, bravery:15, decisions:14, anticipation:15 }),
    makeHidden({ consistency:14, importantMatches:13 }), 3200000, 14000, 2),
  makePlayer('cruzeiro', 'Paulo Rodrigues', 29, 'DC', [], 'Right',
    makeAttrs(11, { marking:15, tackling:14, heading:16, concentration:14, positioning:14, strength:16, jumping:15, bravery:14, decisions:13 }),
    makeHidden({ consistency:13 }), 1800000, 10000, 2),
  makePlayer('cruzeiro', 'Rodrigo Bentes', 26, 'DC', ['SW'], 'Right',
    makeAttrs(11, { marking:14, tackling:14, heading:14, concentration:14, positioning:14, strength:14, decisions:13 }),
    makeHidden({ consistency:12 }), 1200000, 8500, 1),
  makePlayer('cruzeiro', 'Welton César', 22, 'DC', [], 'Right',
    makeAttrs(10, { marking:13, tackling:12, heading:13, concentration:12, positioning:12 }),
    makeHidden({ consistency:11 }), 600000, 5000, 3),

  // DL/DR
  makePlayer('cruzeiro', 'Cléberson Andrade', 24, 'DL', ['MC'], 'Left',
    makeAttrs(12, { crossing:14, pace:15, acceleration:15, stamina:15, tackling:12, passing:13, dribbling:13 }),
    makeHidden({ consistency:13, versatility:13 }), 2200000, 11000, 2),
  makePlayer('cruzeiro', 'Marcos Adriano', 23, 'DR', ['MC'], 'Right',
    makeAttrs(11, { crossing:13, pace:14, acceleration:14, stamina:14, tackling:12, passing:12 }),
    makeHidden({ consistency:12 }), 1400000, 8000, 2),

  // DM/MC
  makePlayer('cruzeiro', 'Alex Mineiro', 27, 'MC', ['DM'], 'Right',
    makeAttrs(12, { passing:15, longPassing:14, tackling:14, composure:14, teamwork:15, decisions:14, concentration:14, workRate:15 }),
    makeHidden({ consistency:14, professionalism:15 }), 3000000, 15000, 2),
  makePlayer('cruzeiro', 'Renato Augusto', 20, 'MC', ['AMC'], 'Right',
    makeAttrs(12, { passing:14, creativity:15, technique:14, dribbling:13, firstTouch:14, decisions:13 }),
    makeHidden({ consistency:12, ambition:16 }), 2800000, 10000, 3),
  makePlayer('cruzeiro', 'Henrique Dourado', 25, 'MC', [], 'Right',
    makeAttrs(12, { passing:13, tackling:13, workRate:14, teamwork:14, stamina:15 }),
    makeHidden({ consistency:13 }), 1500000, 9000, 2),
  makePlayer('cruzeiro', 'Diego Tardelli', 19, 'MC', ['AMC'], 'Right',
    makeAttrs(11, { creativity:14, dribbling:13, technique:13, flair:13 }),
    makeHidden({ consistency:11, ambition:15 }), 1800000, 7000, 3),

  // ML/MR
  makePlayer('cruzeiro', 'Éverton Felipe', 24, 'ML', ['DL'], 'Left',
    makeAttrs(12, { crossing:15, pace:14, dribbling:13, stamina:14, acceleration:14 }),
    makeHidden({ consistency:13 }), 2000000, 10000, 2),
  makePlayer('cruzeiro', 'Júlio César Santos', 23, 'MR', ['DR'], 'Right',
    makeAttrs(12, { crossing:14, pace:14, dribbling:13, stamina:14 }),
    makeHidden({ consistency:12 }), 1600000, 9000, 2),

  // AMC
  makePlayer('cruzeiro', 'Marcelo Moreno', 22, 'AMC', ['SC'], 'Right',
    makeAttrs(12, { technique:15, creativity:15, dribbling:14, firstTouch:15, passing:14, flair:14, finishing:13, composure:13 }),
    makeHidden({ consistency:13, importantMatches:14 }), 4000000, 16000, 2),
  makePlayer('cruzeiro', 'Rafael Sobis', 19, 'AMC', ['SC'], 'Right',
    makeAttrs(11, { technique:14, creativity:13, dribbling:13, finishing:12, flair:13 }),
    makeHidden({ consistency:11, ambition:16 }), 2500000, 8000, 3),

  // SC
  makePlayer('cruzeiro', 'Eliandro Costa', 26, 'SC', [], 'Right',
    makeAttrs(11, { finishing:16, heading:14, offTheBall:15, composure:14, strength:13, pace:13, firstTouch:14 }),
    makeHidden({ consistency:14, importantMatches:15 }), 5000000, 22000, 2),
  makePlayer('cruzeiro', 'Thiago Prada', 24, 'SC', ['AMC'], 'Right',
    makeAttrs(12, { finishing:15, dribbling:13, pace:14, firstTouch:14, offTheBall:14, technique:13 }),
    makeHidden({ consistency:13 }), 3500000, 16000, 2),
  makePlayer('cruzeiro', 'Bruno Viana', 27, 'SC', [], 'Left',
    makeAttrs(11, { finishing:14, heading:15, strength:15, jumping:14, bravery:14 }),
    makeHidden({ consistency:12 }), 1500000, 9000, 1),
  makePlayer('cruzeiro', 'Paulo Sérgio Neto', 22, 'SC', ['AMC'], 'Right',
    makeAttrs(10, { finishing:13, pace:14, dribbling:12 }),
    makeHidden({ consistency:11 }), 800000, 5500, 3),

  // Extra
  makePlayer('cruzeiro', 'Roberto Claro', 21, 'MC', [], 'Right',
    makeAttrs(10, { passing:12, tackling:11, workRate:13 }),
    makeHidden({ consistency:10 }), 400000, 4000, 3),
  makePlayer('cruzeiro', 'Vanderlei Marques', 30, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11, heading:12, concentration:12 }),
    makeHidden({ consistency:11 }), 300000, 4500, 1),
  makePlayer('cruzeiro', 'Frederico Alves', 21, 'DL', [], 'Left',
    makeAttrs(10, { crossing:11, pace:12, stamina:12 }),
    makeHidden({ consistency:10 }), 350000, 4000, 3),
  makePlayer('cruzeiro', 'Lucas Abreu', 20, 'SC', [], 'Right',
    makeAttrs(9, { finishing:11, pace:12 }),
    makeHidden({ consistency:9 }), 250000, 3500, 3),
  makePlayer('cruzeiro', 'Tiago Lemos', 19, 'GK', [], 'Right',
    makeAttrs(7, { handling:10, reflexes:11, aerial:9 }),
    makeHidden({ consistency:9 }), 100000, 2500, 3),
];

// -----------------------------------------------------------------
// 2. SÃO PAULO (top-tier: base ~14)
// -----------------------------------------------------------------
const spfcPlayers: Player[] = [
  makePlayer('saopaulo', 'Rogério Ceni', 30, 'GK', [], 'Right',
    makeAttrs(9, { aerial:15, command:16, communication:15, handling:16, kicking:17, oneOnOnes:15, reflexes:16, throwing:14, freekicks:17, penalties:15, concentration:16, decisions:15 }),
    makeHidden({ consistency:16, importantMatches:16, loyalty:18, professionalism:17 }), 5000000, 25000, 3),
  makePlayer('saopaulo', 'Fábio Costa', 26, 'GK', [], 'Right',
    makeAttrs(8, { aerial:13, command:12, handling:14, reflexes:14, oneOnOnes:13 }),
    makeHidden({ consistency:12 }), 700000, 7000, 2),

  makePlayer('saopaulo', 'Gustavo Nery', 27, 'DL', ['DC'], 'Left',
    makeAttrs(12, { crossing:14, pace:14, tackling:13, marking:13, stamina:14, passing:13 }),
    makeHidden({ consistency:13 }), 2000000, 12000, 2),
  makePlayer('saopaulo', 'Alex Rodrigues', 25, 'DC', [], 'Right',
    makeAttrs(12, { marking:15, tackling:14, heading:15, concentration:15, positioning:15, strength:14, decisions:14 }),
    makeHidden({ consistency:14 }), 3000000, 14000, 2),
  makePlayer('saopaulo', 'Luís Fabiano Assis', 26, 'DC', ['SW'], 'Right',
    makeAttrs(12, { marking:15, tackling:14, heading:14, concentration:14, positioning:14, strength:15 }),
    makeHidden({ consistency:14 }), 2800000, 13000, 2),
  makePlayer('saopaulo', 'Diego Lugano', 23, 'DC', [], 'Right',
    makeAttrs(12, { marking:14, tackling:14, heading:14, concentration:14, positioning:14, strength:14, bravery:14 }),
    makeHidden({ consistency:13 }), 2200000, 11000, 2),
  makePlayer('saopaulo', 'Cicinho Santos', 24, 'DR', ['MC'], 'Right',
    makeAttrs(12, { crossing:15, pace:15, acceleration:15, tackling:12, stamina:15, dribbling:13 }),
    makeHidden({ consistency:13 }), 2500000, 12000, 2),

  makePlayer('saopaulo', 'Júlio Baptista', 21, 'MC', ['AMC'], 'Right',
    makeAttrs(13, { passing:14, technique:15, creativity:15, dribbling:14, longShots:14, firstTouch:14, strength:14, workRate:14 }),
    makeHidden({ consistency:13, ambition:16 }), 5500000, 20000, 3),
  makePlayer('saopaulo', 'Mineiro Ferreira', 28, 'MC', ['DM'], 'Right',
    makeAttrs(12, { tackling:15, marking:14, passing:13, workRate:16, teamwork:15, concentration:15, decisions:14 }),
    makeHidden({ consistency:15, professionalism:15 }), 2500000, 14000, 2),
  makePlayer('saopaulo', 'Danilo Pereira', 24, 'MC', [], 'Right',
    makeAttrs(12, { passing:14, longPassing:13, tackling:13, composure:13, decisions:13 }),
    makeHidden({ consistency:13 }), 2000000, 11000, 2),
  makePlayer('saopaulo', 'Wellington Nem', 21, 'ML', ['DL'], 'Left',
    makeAttrs(12, { crossing:14, pace:14, dribbling:13, stamina:14, acceleration:14 }),
    makeHidden({ consistency:12 }), 1800000, 9000, 3),
  makePlayer('saopaulo', 'Kaká Rodrigues', 21, 'AMC', ['MC'], 'Right',
    makeAttrs(13, { technique:17, creativity:17, dribbling:15, firstTouch:16, passing:15, flair:16, composure:14, decisions:14 }),
    makeHidden({ consistency:14, importantMatches:15, ambition:17 }), 8000000, 25000, 3),

  makePlayer('saopaulo', 'Grafite Santos', 26, 'SC', [], 'Right',
    makeAttrs(12, { finishing:16, pace:16, acceleration:15, dribbling:14, offTheBall:15, firstTouch:13, composure:13 }),
    makeHidden({ consistency:13, importantMatches:14 }), 5000000, 22000, 2),
  makePlayer('saopaulo', 'Luís Fabiano', 22, 'SC', [], 'Right',
    makeAttrs(12, { finishing:16, heading:14, strength:14, pace:14, offTheBall:15, technique:14, composure:14 }),
    makeHidden({ consistency:13, ambition:15 }), 4500000, 18000, 2),
  makePlayer('saopaulo', 'Amoroso Lima', 28, 'SC', ['AMC'], 'Right',
    makeAttrs(12, { finishing:15, technique:14, dribbling:13, firstTouch:14, flair:14 }),
    makeHidden({ consistency:12 }), 3000000, 16000, 1),
  makePlayer('saopaulo', 'Josimar Brito', 23, 'SC', [], 'Left',
    makeAttrs(11, { finishing:14, pace:14, dribbling:13 }),
    makeHidden({ consistency:12 }), 1500000, 8000, 2),

  makePlayer('saopaulo', 'Fabão Defensor', 30, 'DC', [], 'Right',
    makeAttrs(11, { marking:13, tackling:13, heading:13, concentration:13 }),
    makeHidden({ consistency:12 }), 500000, 6000, 1),
  makePlayer('saopaulo', 'Marquinhos São Paulo', 22, 'MC', [], 'Right',
    makeAttrs(11, { passing:12, tackling:12, workRate:13 }),
    makeHidden({ consistency:11 }), 600000, 5000, 3),
  makePlayer('saopaulo', 'Éderson Neto', 20, 'MC', ['AMC'], 'Right',
    makeAttrs(10, { creativity:12, technique:12 }),
    makeHidden({ consistency:10, ambition:14 }), 400000, 4000, 3),
  makePlayer('saopaulo', 'Bruno Senna SPFC', 21, 'DL', [], 'Left',
    makeAttrs(10, { crossing:11, pace:12, tackling:10 }),
    makeHidden({ consistency:10 }), 300000, 3500, 3),
  makePlayer('saopaulo', 'Anderson Polga', 24, 'DR', [], 'Right',
    makeAttrs(11, { crossing:12, pace:12, tackling:11, stamina:12 }),
    makeHidden({ consistency:11 }), 500000, 5000, 2),
  makePlayer('saopaulo', 'Renan Barcelos', 19, 'GK', [], 'Right',
    makeAttrs(7, { handling:10, reflexes:11 }),
    makeHidden({ consistency:9 }), 100000, 2500, 3),
  makePlayer('saopaulo', 'Victor Paulistano', 22, 'SC', [], 'Right',
    makeAttrs(10, { finishing:11, pace:11 }),
    makeHidden({ consistency:10 }), 300000, 3500, 3),
  makePlayer('saopaulo', 'Leandro Castán', 20, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11, heading:11 }),
    makeHidden({ consistency:10, ambition:13 }), 350000, 3500, 3),
  makePlayer('saopaulo', 'Tiago Ribas', 21, 'MC', [], 'Right',
    makeAttrs(10, { passing:11, workRate:12 }),
    makeHidden({ consistency:10 }), 250000, 3000, 3),
];

// -----------------------------------------------------------------
// 3. SANTOS (top-tier: base ~14-15)
// -----------------------------------------------------------------
const santosPlayers: Player[] = [
  makePlayer('santos', 'Fábio Sanches', 27, 'GK', [], 'Right',
    makeAttrs(9, { aerial:14, command:14, handling:15, oneOnOnes:14, reflexes:15, communication:13, concentration:14, decisions:14 }),
    makeHidden({ consistency:14 }), 2500000, 14000, 2),
  makePlayer('santos', 'Giovanni Oliveira', 25, 'GK', [], 'Right',
    makeAttrs(8, { aerial:12, handling:13, reflexes:13, oneOnOnes:12 }),
    makeHidden({ consistency:12 }), 500000, 6000, 2),

  makePlayer('santos', 'Edu Dracena', 24, 'DC', ['SW'], 'Right',
    makeAttrs(12, { marking:15, tackling:14, heading:15, concentration:14, positioning:14, strength:15, decisions:13 }),
    makeHidden({ consistency:14 }), 2800000, 13000, 2),
  makePlayer('santos', 'Rodrigo Fabri', 27, 'DC', [], 'Right',
    makeAttrs(11, { marking:14, tackling:13, heading:14, concentration:13, positioning:13, strength:14 }),
    makeHidden({ consistency:13 }), 1500000, 9000, 2),
  makePlayer('santos', 'André Luís Bento', 25, 'DC', [], 'Right',
    makeAttrs(11, { marking:13, tackling:13, heading:13, concentration:13 }),
    makeHidden({ consistency:12 }), 1000000, 7000, 2),
  makePlayer('santos', 'Marcos Evangelista', 26, 'DC', [], 'Right',
    makeAttrs(11, { marking:13, tackling:12, heading:13 }),
    makeHidden({ consistency:12 }), 900000, 6500, 1),

  makePlayer('santos', 'Leandro Santos', 24, 'DL', ['ML'], 'Left',
    makeAttrs(12, { crossing:14, pace:14, tackling:12, stamina:14, dribbling:12 }),
    makeHidden({ consistency:12 }), 1800000, 10000, 2),
  makePlayer('santos', 'Renato Caju', 23, 'DR', ['MR'], 'Right',
    makeAttrs(12, { crossing:13, pace:14, tackling:12, stamina:13 }),
    makeHidden({ consistency:12 }), 1400000, 9000, 2),

  makePlayer('santos', 'Elano Blumer', 22, 'MC', ['AMC'], 'Right',
    makeAttrs(13, { passing:15, technique:15, creativity:15, dribbling:14, firstTouch:15, longShots:13, flair:14 }),
    makeHidden({ consistency:13, ambition:15 }), 5000000, 18000, 3),
  makePlayer('santos', 'Ricardinho Nunes', 25, 'MC', [], 'Right',
    makeAttrs(12, { passing:14, tackling:13, creativity:13, decisions:13, teamwork:14 }),
    makeHidden({ consistency:13 }), 2200000, 12000, 2),
  makePlayer('santos', 'Pitbull Medeiros', 28, 'MC', ['DM'], 'Right',
    makeAttrs(11, { tackling:15, marking:14, workRate:15, stamina:15, concentration:14 }),
    makeHidden({ consistency:14, professionalism:14 }), 1500000, 9000, 2),
  makePlayer('santos', 'Vandinho Sá', 24, 'ML', ['DL'], 'Left',
    makeAttrs(12, { crossing:14, dribbling:13, pace:14, stamina:14 }),
    makeHidden({ consistency:12 }), 1800000, 10000, 2),
  makePlayer('santos', 'Robinho Ferreira', 19, 'AMC', ['SC', 'ML'], 'Right',
    makeAttrs(14, { technique:17, dribbling:17, flair:17, pace:16, acceleration:16, firstTouch:16, creativity:15, finishing:14, composure:13 }),
    makeHidden({ consistency:13, ambition:17, importantMatches:14 }), 12000000, 20000, 3),
  makePlayer('santos', 'Pedrão Atacante', 27, 'AMC', ['SC'], 'Right',
    makeAttrs(12, { technique:14, creativity:14, dribbling:13, firstTouch:14, finishing:13 }),
    makeHidden({ consistency:12 }), 2500000, 13000, 1),

  makePlayer('santos', 'Deivid Atacante', 25, 'SC', [], 'Right',
    makeAttrs(12, { finishing:16, heading:15, strength:15, offTheBall:15, composure:13, firstTouch:13 }),
    makeHidden({ consistency:13, importantMatches:14 }), 4500000, 20000, 2),
  makePlayer('santos', 'Luizão Paulista', 28, 'SC', [], 'Right',
    makeAttrs(11, { finishing:14, heading:16, strength:16, jumping:15, bravery:14 }),
    makeHidden({ consistency:12 }), 2000000, 12000, 1),
  makePlayer('santos', 'Diego Ribas', 19, 'SC', ['AMC'], 'Left',
    makeAttrs(12, { technique:15, dribbling:14, firstTouch:14, creativity:14, finishing:13 }),
    makeHidden({ consistency:12, ambition:16 }), 4000000, 12000, 3),
  makePlayer('santos', 'Alessandro Costa', 22, 'SC', [], 'Right',
    makeAttrs(11, { finishing:13, pace:14, acceleration:13 }),
    makeHidden({ consistency:11 }), 1000000, 6000, 2),

  makePlayer('santos', 'Alexandro Meireles', 21, 'MC', [], 'Right',
    makeAttrs(10, { passing:12, workRate:13, teamwork:12 }),
    makeHidden({ consistency:10 }), 400000, 4000, 3),
  makePlayer('santos', 'Henrique Bentes', 23, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11, heading:11 }),
    makeHidden({ consistency:10 }), 350000, 4000, 2),
  makePlayer('santos', 'Marcos Teixeira', 20, 'DL', [], 'Left',
    makeAttrs(10, { crossing:11, pace:12 }),
    makeHidden({ consistency:10 }), 300000, 3500, 3),
  makePlayer('santos', 'Rafael Porto', 21, 'MR', [], 'Right',
    makeAttrs(10, { crossing:12, pace:12 }),
    makeHidden({ consistency:10 }), 300000, 3500, 3),
  makePlayer('santos', 'Thiago Vilar', 22, 'SC', [], 'Right',
    makeAttrs(9, { finishing:11, pace:12 }),
    makeHidden({ consistency:9 }), 200000, 3000, 3),
  makePlayer('santos', 'Bruno Paixão', 19, 'GK', [], 'Right',
    makeAttrs(7, { handling:10, reflexes:11 }),
    makeHidden({ consistency:9 }), 80000, 2000, 3),
  makePlayer('santos', 'Luciano Praiano', 24, 'DR', [], 'Right',
    makeAttrs(10, { crossing:11, pace:12, tackling:10 }),
    makeHidden({ consistency:10 }), 350000, 4000, 2),
];

// -----------------------------------------------------------------
// 4. FLAMENGO (high-tier: base ~13)
// -----------------------------------------------------------------
const flamengoPlayers: Player[] = [
  makePlayer('flamengo', 'Anderson Luis GK', 27, 'GK', [], 'Right',
    makeAttrs(9, { aerial:14, command:14, handling:15, oneOnOnes:14, reflexes:15, concentration:14 }),
    makeHidden({ consistency:13 }), 2200000, 13000, 2),
  makePlayer('flamengo', 'Bruno Fernandes GK', 25, 'GK', [], 'Right',
    makeAttrs(8, { handling:13, reflexes:14, aerial:12, oneOnOnes:12 }),
    makeHidden({ consistency:11 }), 600000, 6500, 2),

  makePlayer('flamengo', 'Juan Silveira', 24, 'DC', [], 'Right',
    makeAttrs(12, { marking:15, tackling:14, heading:15, concentration:14, positioning:14, strength:15, bravery:14 }),
    makeHidden({ consistency:14 }), 3000000, 14000, 2),
  makePlayer('flamengo', 'Rodrigo Fabiano DC', 26, 'DC', ['SW'], 'Right',
    makeAttrs(11, { marking:14, tackling:13, heading:14, concentration:13, positioning:13, strength:14 }),
    makeHidden({ consistency:13 }), 1800000, 10000, 2),
  makePlayer('flamengo', 'Leo Moraes', 25, 'DC', [], 'Right',
    makeAttrs(11, { marking:14, tackling:13, heading:13, concentration:13 }),
    makeHidden({ consistency:12 }), 1200000, 8000, 2),
  makePlayer('flamengo', 'Márcio Nunes DC', 28, 'DC', [], 'Right',
    makeAttrs(10, { marking:13, tackling:12, heading:12 }),
    makeHidden({ consistency:11 }), 500000, 5000, 1),

  makePlayer('flamengo', 'Renato Santos DL', 24, 'DL', ['ML'], 'Left',
    makeAttrs(11, { crossing:13, pace:13, tackling:12, stamina:13, dribbling:12 }),
    makeHidden({ consistency:12 }), 1500000, 8500, 2),
  makePlayer('flamengo', 'Gustavo Lima DR', 23, 'DR', ['MR'], 'Right',
    makeAttrs(11, { crossing:13, pace:13, tackling:11, stamina:13 }),
    makeHidden({ consistency:12 }), 1200000, 8000, 2),

  makePlayer('flamengo', 'Petkovic Brazuca', 32, 'AMC', ['MC'], 'Right',
    makeAttrs(11, { technique:15, creativity:15, passing:14, firstTouch:14, dribbling:13, flair:14, longShots:13 }),
    makeHidden({ consistency:12, importantMatches:14 }), 1000000, 12000, 1),
  makePlayer('flamengo', 'Fabinho Flamengo', 25, 'MC', ['DM'], 'Right',
    makeAttrs(11, { tackling:14, marking:13, workRate:14, passing:12, stamina:14 }),
    makeHidden({ consistency:13 }), 1500000, 9000, 2),
  makePlayer('flamengo', 'Zé Roberto Rubro', 30, 'MC', [], 'Left',
    makeAttrs(12, { passing:14, crossing:13, stamina:15, workRate:15, technique:13, decisions:13 }),
    makeHidden({ consistency:13, professionalism:14 }), 2000000, 13000, 1),
  makePlayer('flamengo', 'Adriano Imperador', 21, 'SC', [], 'Right',
    makeAttrs(13, { finishing:16, heading:15, strength:17, pace:14, longShots:15, technique:14, bravery:15, composure:13 }),
    makeHidden({ consistency:13, importantMatches:15, ambition:15 }), 7000000, 22000, 3),
  makePlayer('flamengo', 'Edilson Capetinha', 30, 'MR', ['DR'], 'Right',
    makeAttrs(11, { crossing:14, dribbling:13, pace:13, technique:12, flair:13 }),
    makeHidden({ consistency:11 }), 1000000, 9000, 1),

  makePlayer('flamengo', 'Obina Ribeiro', 22, 'SC', ['AMC'], 'Right',
    makeAttrs(11, { finishing:14, pace:14, dribbling:13, technique:12 }),
    makeHidden({ consistency:12 }), 2000000, 10000, 2),
  makePlayer('flamengo', 'Luiz Henrique FLA', 25, 'SC', [], 'Right',
    makeAttrs(11, { finishing:14, heading:13, strength:13, offTheBall:13 }),
    makeHidden({ consistency:12 }), 1500000, 9000, 2),
  makePlayer('flamengo', 'Anderson Polga FLA', 23, 'ML', ['DL'], 'Left',
    makeAttrs(11, { crossing:13, dribbling:12, pace:13, stamina:13 }),
    makeHidden({ consistency:11 }), 900000, 7000, 2),
  makePlayer('flamengo', 'Rodrigo Gonçalves', 22, 'MC', [], 'Right',
    makeAttrs(11, { passing:12, tackling:12, workRate:13 }),
    makeHidden({ consistency:11 }), 700000, 6000, 2),
  makePlayer('flamengo', 'Marcos Flamengo', 20, 'MC', [], 'Right',
    makeAttrs(10, { passing:12, creativity:11 }),
    makeHidden({ consistency:10, ambition:13 }), 400000, 4000, 3),
  makePlayer('flamengo', 'Cleber Santana FLA', 21, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11 }),
    makeHidden({ consistency:10 }), 350000, 4000, 3),
  makePlayer('flamengo', 'Wanderley Lima', 29, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, heading:11 }),
    makeHidden({ consistency:10 }), 300000, 4000, 1),
  makePlayer('flamengo', 'Pedro Vasconcelos', 22, 'DR', [], 'Right',
    makeAttrs(10, { crossing:11, pace:11 }),
    makeHidden({ consistency:10 }), 350000, 3500, 3),
  makePlayer('flamengo', 'André Cogumelo', 19, 'GK', [], 'Right',
    makeAttrs(7, { handling:10, reflexes:10 }),
    makeHidden({ consistency:9 }), 80000, 2000, 3),
  makePlayer('flamengo', 'Tiago Mendonça', 21, 'SC', [], 'Right',
    makeAttrs(9, { finishing:11, pace:11 }),
    makeHidden({ consistency:9 }), 200000, 3000, 3),
  makePlayer('flamengo', 'Lúcio Bezerra', 23, 'AMC', [], 'Right',
    makeAttrs(10, { technique:12, creativity:11 }),
    makeHidden({ consistency:10 }), 400000, 4000, 2),
  makePlayer('flamengo', 'Daniel Alves FLA', 20, 'DR', ['MR'], 'Right',
    makeAttrs(11, { crossing:13, pace:13, tackling:11 }),
    makeHidden({ consistency:11, ambition:15 }), 700000, 5000, 3),
];

// -----------------------------------------------------------------
// 5. GRÊMIO (high-tier: base ~12-13)
// -----------------------------------------------------------------
const gremioPlayers: Player[] = [
  makePlayer('gremio', 'Dida Grêmio', 29, 'GK', [], 'Right',
    makeAttrs(9, { aerial:14, command:15, handling:15, oneOnOnes:14, reflexes:16, communication:14, concentration:14, decisions:14 }),
    makeHidden({ consistency:14 }), 2000000, 12000, 2),
  makePlayer('gremio', 'Márcio GK2', 26, 'GK', [], 'Right',
    makeAttrs(8, { handling:13, reflexes:13, aerial:12 }),
    makeHidden({ consistency:11 }), 450000, 5500, 2),

  makePlayer('gremio', 'Roger Flores', 26, 'DC', [], 'Right',
    makeAttrs(11, { marking:14, tackling:14, heading:14, concentration:14, positioning:14, strength:14 }),
    makeHidden({ consistency:13 }), 2200000, 12000, 2),
  makePlayer('gremio', 'Anderson Lima DC', 25, 'DC', [], 'Right',
    makeAttrs(11, { marking:14, tackling:13, heading:14, concentration:13 }),
    makeHidden({ consistency:13 }), 1600000, 9500, 2),
  makePlayer('gremio', 'Claiton Grêmio', 24, 'DC', ['SW'], 'Right',
    makeAttrs(11, { marking:13, tackling:13, heading:13, concentration:13 }),
    makeHidden({ consistency:12 }), 1000000, 7000, 2),
  makePlayer('gremio', 'Diogo Grêmio DC', 27, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:12, heading:12 }),
    makeHidden({ consistency:11 }), 500000, 5000, 1),

  makePlayer('gremio', 'Ronei Grêmio DL', 25, 'DL', ['ML'], 'Left',
    makeAttrs(11, { crossing:13, pace:13, tackling:12, stamina:13 }),
    makeHidden({ consistency:12 }), 1200000, 8000, 2),
  makePlayer('gremio', 'Fábio Aurélio GRE', 24, 'DR', ['MR'], 'Right',
    makeAttrs(12, { crossing:14, pace:14, tackling:12, stamina:13, dribbling:13 }),
    makeHidden({ consistency:13 }), 2000000, 11000, 2),

  makePlayer('gremio', 'Paulo Nunes GRE', 27, 'MC', [], 'Right',
    makeAttrs(11, { passing:13, tackling:13, workRate:14, teamwork:14, stamina:14 }),
    makeHidden({ consistency:13 }), 1600000, 10000, 2),
  makePlayer('gremio', 'Anderson Gomes MC', 24, 'MC', ['AMC'], 'Right',
    makeAttrs(12, { passing:13, creativity:14, technique:13, dribbling:13, longShots:12 }),
    makeHidden({ consistency:12 }), 2000000, 10500, 2),
  makePlayer('gremio', 'Tinga Ferreira', 25, 'MC', ['DM'], 'Right',
    makeAttrs(11, { tackling:14, marking:13, workRate:15, stamina:15, concentration:14 }),
    makeHidden({ consistency:13, professionalism:14 }), 1500000, 9000, 2),
  makePlayer('gremio', 'Thaciano GRE', 20, 'MC', ['AMC'], 'Right',
    makeAttrs(11, { creativity:13, technique:12, passing:12, dribbling:12 }),
    makeHidden({ consistency:11, ambition:14 }), 900000, 6000, 3),

  makePlayer('gremio', 'Lucas Lima GRE', 21, 'ML', ['DL'], 'Left',
    makeAttrs(11, { crossing:13, pace:13, dribbling:12, stamina:13 }),
    makeHidden({ consistency:11 }), 1000000, 7000, 3),
  makePlayer('gremio', 'Souza Winger', 25, 'MR', ['DR'], 'Right',
    makeAttrs(11, { crossing:13, pace:13, dribbling:12 }),
    makeHidden({ consistency:12 }), 1100000, 7500, 2),

  makePlayer('gremio', 'Fernandão Grêmio', 26, 'SC', [], 'Right',
    makeAttrs(12, { finishing:15, heading:15, strength:15, offTheBall:14, bravery:14, composure:13 }),
    makeHidden({ consistency:13, importantMatches:13 }), 3500000, 16000, 2),
  makePlayer('gremio', 'Diego Carioca GRE', 23, 'SC', ['AMC'], 'Right',
    makeAttrs(11, { finishing:14, dribbling:13, technique:13, pace:13 }),
    makeHidden({ consistency:12 }), 2000000, 10000, 2),
  makePlayer('gremio', 'Cláudio Grêmio SC', 25, 'SC', [], 'Left',
    makeAttrs(11, { finishing:13, pace:14, acceleration:14 }),
    makeHidden({ consistency:12 }), 1400000, 8500, 2),
  makePlayer('gremio', 'Régis Grêmio SC', 22, 'SC', [], 'Right',
    makeAttrs(10, { finishing:12, pace:12, heading:11 }),
    makeHidden({ consistency:11 }), 700000, 5500, 3),

  makePlayer('gremio', 'Geromel Jovem', 19, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11 }),
    makeHidden({ consistency:10, ambition:14 }), 300000, 3500, 3),
  makePlayer('gremio', 'Ciro Grêmio', 21, 'MC', [], 'Right',
    makeAttrs(10, { passing:11, workRate:12 }),
    makeHidden({ consistency:10 }), 250000, 3500, 3),
  makePlayer('gremio', 'Rodrigo Grêmio AMC', 22, 'AMC', [], 'Right',
    makeAttrs(10, { technique:12, creativity:11 }),
    makeHidden({ consistency:10 }), 300000, 4000, 3),
  makePlayer('gremio', 'Pedro Grêmio GK', 24, 'GK', [], 'Right',
    makeAttrs(7, { handling:10, reflexes:10 }),
    makeHidden({ consistency:9 }), 80000, 2000, 2),
  makePlayer('gremio', 'Victor Grêmio DR', 22, 'DR', [], 'Right',
    makeAttrs(10, { crossing:11, pace:11, tackling:10 }),
    makeHidden({ consistency:10 }), 300000, 3500, 3),
  makePlayer('gremio', 'Gabriel Grêmio DL', 20, 'DL', [], 'Left',
    makeAttrs(9, { crossing:10, pace:11 }),
    makeHidden({ consistency:9 }), 200000, 3000, 3),
  makePlayer('gremio', 'Índio Grêmio SC', 28, 'SC', [], 'Right',
    makeAttrs(10, { finishing:11, heading:11, strength:12 }),
    makeHidden({ consistency:10 }), 300000, 4000, 1),
];

// -----------------------------------------------------------------
// 6. INTERNACIONAL (high-tier: base ~12-13)
// -----------------------------------------------------------------
const interPlayers: Player[] = [
  makePlayer('inter', 'Clemer Becker', 26, 'GK', [], 'Right',
    makeAttrs(9, { aerial:13, command:13, handling:15, oneOnOnes:13, reflexes:15, communication:13, concentration:13 }),
    makeHidden({ consistency:13 }), 1800000, 11000, 2),
  makePlayer('inter', 'Renan Inter GK', 24, 'GK', [], 'Right',
    makeAttrs(8, { handling:13, reflexes:13, aerial:11 }),
    makeHidden({ consistency:11 }), 400000, 5000, 2),

  makePlayer('inter', 'Beira-Rio DC1', 26, 'DC', [], 'Right',
    makeAttrs(11, { marking:14, tackling:14, heading:14, concentration:14, positioning:13, strength:14 }),
    makeHidden({ consistency:13 }), 2000000, 11000, 2),
  makePlayer('inter', 'Índio Colorado', 28, 'DC', ['SW'], 'Right',
    makeAttrs(11, { marking:13, tackling:13, heading:14, concentration:13, strength:14 }),
    makeHidden({ consistency:13 }), 1200000, 8500, 1),
  makePlayer('inter', 'Maicon Inter', 22, 'DR', ['DC'], 'Right',
    makeAttrs(12, { crossing:14, pace:15, tackling:13, marking:13, stamina:14, acceleration:14 }),
    makeHidden({ consistency:13, ambition:16 }), 2500000, 11000, 3),
  makePlayer('inter', 'Carlos Grohe', 25, 'DC', [], 'Right',
    makeAttrs(10, { marking:13, tackling:12, heading:13 }),
    makeHidden({ consistency:12 }), 800000, 6500, 2),

  makePlayer('inter', 'Tiago Galhardo DL', 24, 'DL', ['ML'], 'Left',
    makeAttrs(11, { crossing:13, pace:13, tackling:11, stamina:13 }),
    makeHidden({ consistency:12 }), 1200000, 8000, 2),
  makePlayer('inter', 'Nei Inter DC', 27, 'DC', [], 'Right',
    makeAttrs(10, { marking:13, tackling:12, heading:12 }),
    makeHidden({ consistency:12 }), 600000, 5500, 1),

  makePlayer('inter', 'Beto Abreu MC', 26, 'MC', ['DM'], 'Right',
    makeAttrs(11, { tackling:14, marking:13, workRate:14, passing:12, stamina:14, concentration:13 }),
    makeHidden({ consistency:13 }), 1400000, 9000, 2),
  makePlayer('inter', 'Bolívar Inter', 27, 'MC', [], 'Right',
    makeAttrs(11, { passing:13, tackling:13, creativity:12, teamwork:14, decisions:12 }),
    makeHidden({ consistency:12 }), 1500000, 9500, 2),
  makePlayer('inter', 'Taison Barcelos', 19, 'MC', ['AMC'], 'Right',
    makeAttrs(11, { creativity:14, dribbling:13, technique:13, pace:13, flair:13 }),
    makeHidden({ consistency:11, ambition:16 }), 1200000, 6500, 3),
  makePlayer('inter', 'Giuliano Inter', 20, 'MC', ['AMC'], 'Right',
    makeAttrs(11, { passing:12, creativity:13, technique:12 }),
    makeHidden({ consistency:11, ambition:15 }), 900000, 5500, 3),

  makePlayer('inter', 'Airton Colorado ML', 25, 'ML', ['DL'], 'Left',
    makeAttrs(11, { crossing:13, pace:13, dribbling:12, stamina:13 }),
    makeHidden({ consistency:12 }), 1100000, 7500, 2),
  makePlayer('inter', 'Cleiton Xavier', 21, 'MR', ['MC'], 'Right',
    makeAttrs(11, { crossing:13, creativity:12, technique:12, pace:12 }),
    makeHidden({ consistency:11, ambition:14 }), 1000000, 7000, 3),

  makePlayer('inter', 'Ânderson Inter AMC', 24, 'AMC', ['SC'], 'Right',
    makeAttrs(11, { technique:13, creativity:13, dribbling:12, firstTouch:13, finishing:12 }),
    makeHidden({ consistency:12 }), 1800000, 10000, 2),

  makePlayer('inter', 'Wellington Nem Inter', 24, 'SC', [], 'Right',
    makeAttrs(11, { finishing:14, pace:13, dribbling:12, offTheBall:13 }),
    makeHidden({ consistency:12 }), 1800000, 10000, 2),
  makePlayer('inter', 'Leandro Damião Inter', 19, 'SC', [], 'Right',
    makeAttrs(11, { finishing:13, heading:13, strength:13, pace:12 }),
    makeHidden({ consistency:11, ambition:15 }), 1000000, 6000, 3),
  makePlayer('inter', 'Nilmar Inter', 19, 'SC', ['AMC'], 'Right',
    makeAttrs(11, { finishing:13, pace:14, dribbling:12, acceleration:13 }),
    makeHidden({ consistency:11, ambition:15 }), 1000000, 6000, 3),
  makePlayer('inter', 'Marcelo Moreno Inter', 24, 'SC', [], 'Left',
    makeAttrs(10, { finishing:12, heading:12, strength:13 }),
    makeHidden({ consistency:11 }), 700000, 5500, 2),

  makePlayer('inter', 'Rafael Sobis Inter', 19, 'SC', ['AMC'], 'Right',
    makeAttrs(11, { finishing:13, technique:12, dribbling:12 }),
    makeHidden({ consistency:11, ambition:15 }), 800000, 5500, 3),
  makePlayer('inter', 'Pedro Colorado DC', 21, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11 }),
    makeHidden({ consistency:10 }), 300000, 3500, 3),
  makePlayer('inter', 'Roque Junior Inter', 29, 'DC', [], 'Right',
    makeAttrs(11, { marking:13, tackling:13, heading:12 }),
    makeHidden({ consistency:11 }), 500000, 5500, 1),
  makePlayer('inter', 'Volante Inter', 22, 'MC', [], 'Right',
    makeAttrs(10, { tackling:11, workRate:12 }),
    makeHidden({ consistency:10 }), 250000, 3500, 3),
  makePlayer('inter', 'Caxias Inter GK', 23, 'GK', [], 'Right',
    makeAttrs(7, { handling:10, reflexes:10 }),
    makeHidden({ consistency:9 }), 80000, 2000, 3),
  makePlayer('inter', 'Pedro Coloradão', 22, 'DL', [], 'Left',
    makeAttrs(10, { crossing:11, pace:11 }),
    makeHidden({ consistency:10 }), 250000, 3500, 3),
];

// -----------------------------------------------------------------
// 7. CORINTHIANS (high-tier: base ~12-13)
// -----------------------------------------------------------------
const corinthiansPlayers: Player[] = [
  makePlayer('corinthians', 'Dida Alves GK', 28, 'GK', [], 'Right',
    makeAttrs(9, { aerial:14, command:14, handling:15, oneOnOnes:14, reflexes:15, concentration:14 }),
    makeHidden({ consistency:13 }), 2000000, 12000, 2),
  makePlayer('corinthians', 'Felipe Corinthians', 26, 'GK', [], 'Right',
    makeAttrs(8, { handling:13, reflexes:13, aerial:12 }),
    makeHidden({ consistency:11 }), 450000, 5500, 2),

  makePlayer('corinthians', 'Betão Corinthians', 27, 'DC', [], 'Right',
    makeAttrs(11, { marking:14, tackling:14, heading:14, concentration:13, strength:14, bravery:13 }),
    makeHidden({ consistency:13 }), 2000000, 11500, 2),
  makePlayer('corinthians', 'Cléber Coritiba', 25, 'DC', ['SW'], 'Right',
    makeAttrs(11, { marking:13, tackling:13, heading:13, concentration:13 }),
    makeHidden({ consistency:12 }), 1200000, 8000, 2),
  makePlayer('corinthians', 'Ricardinho DC', 26, 'DC', [], 'Right',
    makeAttrs(11, { marking:13, tackling:12, heading:13 }),
    makeHidden({ consistency:12 }), 900000, 7000, 2),
  makePlayer('corinthians', 'Silvio Defensor', 29, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11, heading:12 }),
    makeHidden({ consistency:11 }), 400000, 5000, 1),

  makePlayer('corinthians', 'Julio Santos DL', 25, 'DL', ['ML'], 'Left',
    makeAttrs(11, { crossing:13, pace:13, tackling:11, stamina:13 }),
    makeHidden({ consistency:12 }), 1200000, 8000, 2),
  makePlayer('corinthians', 'Leandro Castán DR', 23, 'DR', ['MC'], 'Right',
    makeAttrs(11, { crossing:13, pace:13, tackling:11, acceleration:13 }),
    makeHidden({ consistency:12 }), 1400000, 8500, 2),

  makePlayer('corinthians', 'Vampeta SC', 30, 'MC', ['DM'], 'Right',
    makeAttrs(12, { tackling:15, marking:14, workRate:14, passing:13, strength:14, concentration:14, decisions:13 }),
    makeHidden({ consistency:13, professionalism:13 }), 1500000, 11000, 1),
  makePlayer('corinthians', 'Cocaína Neto MC', 26, 'MC', [], 'Right',
    makeAttrs(11, { passing:13, technique:13, creativity:12, teamwork:13, decisions:12 }),
    makeHidden({ consistency:12 }), 1500000, 9500, 2),
  makePlayer('corinthians', 'Carlos Tevita MC', 23, 'MC', ['AMC'], 'Right',
    makeAttrs(11, { creativity:13, technique:12, dribbling:12, passing:12 }),
    makeHidden({ consistency:11 }), 1200000, 8000, 2),
  makePlayer('corinthians', 'Gamarra Cori', 30, 'DC', [], 'Right',
    makeAttrs(12, { marking:15, tackling:14, heading:14, concentration:14, decisions:13, influence:14 }),
    makeHidden({ consistency:13, importantMatches:13 }), 1000000, 10000, 1),

  makePlayer('corinthians', 'Fabinho ML', 24, 'ML', ['DL'], 'Left',
    makeAttrs(11, { crossing:13, dribbling:12, pace:13, stamina:13 }),
    makeHidden({ consistency:12 }), 1100000, 7500, 2),
  makePlayer('corinthians', 'Rogerinho MR', 23, 'MR', ['DR'], 'Right',
    makeAttrs(11, { crossing:13, pace:13, dribbling:12, technique:12 }),
    makeHidden({ consistency:11 }), 1000000, 7000, 2),

  makePlayer('corinthians', 'Tevita AMC', 24, 'AMC', ['SC'], 'Right',
    makeAttrs(12, { technique:14, creativity:14, dribbling:13, firstTouch:14, passing:12, finishing:12 }),
    makeHidden({ consistency:12 }), 2500000, 13000, 2),

  makePlayer('corinthians', 'Dinei Pedroso', 27, 'SC', [], 'Right',
    makeAttrs(11, { finishing:14, heading:14, strength:14, offTheBall:13, bravery:14 }),
    makeHidden({ consistency:12, importantMatches:13 }), 2500000, 13000, 2),
  makePlayer('corinthians', 'Gil Timão SC', 25, 'SC', [], 'Right',
    makeAttrs(11, { finishing:13, heading:13, strength:13, pace:12 }),
    makeHidden({ consistency:11 }), 1500000, 9000, 2),
  makePlayer('corinthians', 'Dentinho Cori', 19, 'SC', ['MR'], 'Right',
    makeAttrs(11, { finishing:13, pace:14, dribbling:13, acceleration:14 }),
    makeHidden({ consistency:11, ambition:15 }), 1000000, 5500, 3),
  makePlayer('corinthians', 'Emerson Cori SC', 23, 'SC', [], 'Left',
    makeAttrs(10, { finishing:12, pace:13 }),
    makeHidden({ consistency:11 }), 700000, 5500, 2),

  makePlayer('corinthians', 'Jadson Cori AMC', 20, 'AMC', [], 'Right',
    makeAttrs(11, { technique:13, creativity:12, dribbling:12 }),
    makeHidden({ consistency:11, ambition:14 }), 700000, 5000, 3),
  makePlayer('corinthians', 'Pedro Cori DC', 21, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11 }),
    makeHidden({ consistency:10 }), 300000, 3500, 3),
  makePlayer('corinthians', 'Roni Timão MC', 22, 'MC', [], 'Right',
    makeAttrs(10, { passing:11, workRate:12 }),
    makeHidden({ consistency:10 }), 250000, 3500, 3),
  makePlayer('corinthians', 'Jhonny Timão', 20, 'DR', [], 'Right',
    makeAttrs(10, { crossing:11, pace:11 }),
    makeHidden({ consistency:10 }), 250000, 3000, 3),
  makePlayer('corinthians', 'Marcos Timão GK', 23, 'GK', [], 'Right',
    makeAttrs(7, { handling:10, reflexes:10 }),
    makeHidden({ consistency:9 }), 80000, 2000, 3),
  makePlayer('corinthians', 'Willian Cori', 19, 'MR', ['DR'], 'Right',
    makeAttrs(10, { crossing:12, pace:12, dribbling:11 }),
    makeHidden({ consistency:10, ambition:14 }), 350000, 4000, 3),
];

// -----------------------------------------------------------------
// 8. PALMEIRAS (mid-tier: base ~11-12)
// -----------------------------------------------------------------
const palmeirasPlayers: Player[] = [
  makePlayer('palmeiras', 'Marcos Palmeiras', 31, 'GK', [], 'Right',
    makeAttrs(9, { aerial:14, command:15, handling:16, oneOnOnes:15, reflexes:16, communication:14, concentration:15 }),
    makeHidden({ consistency:15, importantMatches:15, loyalty:17, professionalism:16 }), 2000000, 15000, 2),
  makePlayer('palmeiras', 'Sérgio Palestra', 26, 'GK', [], 'Right',
    makeAttrs(8, { handling:12, reflexes:12, aerial:11 }),
    makeHidden({ consistency:11 }), 350000, 5000, 2),

  makePlayer('palmeiras', 'Roque Junior Palm', 27, 'DC', [], 'Right',
    makeAttrs(12, { marking:15, tackling:14, heading:14, concentration:14, positioning:14, strength:14 }),
    makeHidden({ consistency:13 }), 2500000, 13000, 2),
  makePlayer('palmeiras', 'Lúcio Palestra', 25, 'DC', [], 'Right',
    makeAttrs(12, { marking:14, tackling:14, heading:15, concentration:14, strength:15, pace:13 }),
    makeHidden({ consistency:13 }), 2800000, 14000, 2),
  makePlayer('palmeiras', 'Emerson Sheik DC', 27, 'DC', ['DL'], 'Right',
    makeAttrs(11, { marking:13, tackling:13, heading:13, concentration:13 }),
    makeHidden({ consistency:12 }), 1000000, 7500, 2),
  makePlayer('palmeiras', 'Ivan Palestra', 29, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11, heading:12 }),
    makeHidden({ consistency:11 }), 400000, 5000, 1),

  makePlayer('palmeiras', 'Corrêa DL', 25, 'DL', ['ML'], 'Left',
    makeAttrs(11, { crossing:13, pace:13, tackling:11, stamina:13 }),
    makeHidden({ consistency:12 }), 1100000, 7500, 2),
  makePlayer('palmeiras', 'Cicinho Palestra', 23, 'DR', ['MC'], 'Right',
    makeAttrs(12, { crossing:14, pace:14, tackling:12, acceleration:14, stamina:13 }),
    makeHidden({ consistency:12, ambition:13 }), 1600000, 9000, 2),

  makePlayer('palmeiras', 'Warley MC', 26, 'MC', ['DM'], 'Right',
    makeAttrs(11, { tackling:14, marking:13, workRate:14, passing:12, stamina:14, concentration:13 }),
    makeHidden({ consistency:13 }), 1400000, 9000, 2),
  makePlayer('palmeiras', 'Maurinho MC', 24, 'MC', [], 'Right',
    makeAttrs(11, { passing:13, technique:12, creativity:12, teamwork:13 }),
    makeHidden({ consistency:12 }), 1200000, 8000, 2),
  makePlayer('palmeiras', 'Zé Roberto Palm', 31, 'MC', ['ML'], 'Left',
    makeAttrs(12, { passing:14, stamina:14, workRate:14, crossing:13, technique:13 }),
    makeHidden({ consistency:13, professionalism:14 }), 1500000, 11000, 1),
  makePlayer('palmeiras', 'Alex Palmas AMC', 25, 'AMC', ['MC'], 'Right',
    makeAttrs(12, { technique:14, creativity:14, dribbling:13, firstTouch:14, passing:13, flair:13 }),
    makeHidden({ consistency:12 }), 2500000, 12000, 2),

  makePlayer('palmeiras', 'Marcos Assunção', 27, 'MC', ['AMC'], 'Right',
    makeAttrs(12, { passing:14, technique:13, creativity:13, freekicks:14, longPassing:13 }),
    makeHidden({ consistency:13 }), 2000000, 11000, 2),
  makePlayer('palmeiras', 'Vagner Love', 19, 'SC', [], 'Right',
    makeAttrs(12, { finishing:14, pace:15, acceleration:15, dribbling:13, technique:13, offTheBall:13 }),
    makeHidden({ consistency:12, ambition:16 }), 3500000, 12000, 3),

  makePlayer('palmeiras', 'Marcelo Moreno Palm', 26, 'SC', [], 'Right',
    makeAttrs(11, { finishing:14, heading:14, strength:14, offTheBall:13, bravery:14 }),
    makeHidden({ consistency:12 }), 2000000, 11000, 2),
  makePlayer('palmeiras', 'Euller Palestra', 27, 'SC', [], 'Left',
    makeAttrs(11, { finishing:13, technique:13, dribbling:12, flair:13 }),
    makeHidden({ consistency:12 }), 1200000, 8000, 1),
  makePlayer('palmeiras', 'Kleber Palestra', 23, 'SC', [], 'Right',
    makeAttrs(10, { finishing:12, pace:13, heading:11 }),
    makeHidden({ consistency:11 }), 800000, 6000, 2),
  makePlayer('palmeiras', 'Welliton Pal', 20, 'SC', ['AMC'], 'Right',
    makeAttrs(10, { finishing:12, pace:13, dribbling:11 }),
    makeHidden({ consistency:10, ambition:14 }), 500000, 4500, 3),

  makePlayer('palmeiras', 'Edmilson Palm DC', 21, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11 }),
    makeHidden({ consistency:10, ambition:13 }), 350000, 4000, 3),
  makePlayer('palmeiras', 'Bruno Henrique Palm', 21, 'ML', ['DL'], 'Left',
    makeAttrs(10, { crossing:12, pace:12, dribbling:11 }),
    makeHidden({ consistency:10 }), 350000, 4000, 3),
  makePlayer('palmeiras', 'Renan Palestra MC', 22, 'MC', [], 'Right',
    makeAttrs(10, { passing:11, workRate:12 }),
    makeHidden({ consistency:10 }), 250000, 3500, 3),
  makePlayer('palmeiras', 'Victor Palm DR', 23, 'DR', [], 'Right',
    makeAttrs(10, { crossing:11, pace:12 }),
    makeHidden({ consistency:10 }), 300000, 3500, 2),
  makePlayer('palmeiras', 'Lucas Palm GK', 22, 'GK', [], 'Right',
    makeAttrs(7, { handling:10, reflexes:10 }),
    makeHidden({ consistency:9 }), 80000, 2000, 3),
  makePlayer('palmeiras', 'Germano Palm', 23, 'MC', [], 'Right',
    makeAttrs(10, { passing:11, tackling:11 }),
    makeHidden({ consistency:10 }), 250000, 3500, 2),
  makePlayer('palmeiras', 'Thiago Palm SC', 21, 'SC', [], 'Right',
    makeAttrs(9, { finishing:11, pace:11 }),
    makeHidden({ consistency:9 }), 200000, 3000, 3),
];

// -----------------------------------------------------------------
// 9. ATLÉTICO-MG (mid-tier: base ~11-12)
// -----------------------------------------------------------------
const atleticoMGPlayers: Player[] = [
  makePlayer('atletico-mg', 'Neto Atletico GK', 27, 'GK', [], 'Right',
    makeAttrs(9, { aerial:13, command:13, handling:14, oneOnOnes:13, reflexes:14, concentration:13 }),
    makeHidden({ consistency:13 }), 1500000, 9000, 2),
  makePlayer('atletico-mg', 'Victor Minas GK', 22, 'GK', [], 'Right',
    makeAttrs(9, { aerial:13, command:12, handling:14, oneOnOnes:12, reflexes:14, concentration:12 }),
    makeHidden({ consistency:12, ambition:14 }), 600000, 5000, 3),

  makePlayer('atletico-mg', 'Fernandão ATL', 27, 'DC', [], 'Right',
    makeAttrs(11, { marking:13, tackling:13, heading:14, concentration:13, strength:14 }),
    makeHidden({ consistency:12 }), 1400000, 9000, 2),
  makePlayer('atletico-mg', 'Diego Tardelli DC', 24, 'DC', ['SW'], 'Right',
    makeAttrs(11, { marking:13, tackling:13, heading:13, concentration:13 }),
    makeHidden({ consistency:12 }), 1000000, 7500, 2),
  makePlayer('atletico-mg', 'Leandro ATL DC', 23, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:12, heading:12 }),
    makeHidden({ consistency:11 }), 700000, 6000, 2),
  makePlayer('atletico-mg', 'Jemerson ATL', 22, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11, heading:12 }),
    makeHidden({ consistency:11, ambition:13 }), 500000, 5000, 3),

  makePlayer('atletico-mg', 'Patric ATL DL', 24, 'DL', ['ML'], 'Left',
    makeAttrs(11, { crossing:12, pace:13, tackling:11, stamina:12 }),
    makeHidden({ consistency:11 }), 900000, 7000, 2),
  makePlayer('atletico-mg', 'Marcos Rocha ATL', 22, 'DR', ['MR'], 'Right',
    makeAttrs(11, { crossing:12, pace:13, tackling:11, stamina:12 }),
    makeHidden({ consistency:11, ambition:13 }), 800000, 6000, 3),

  makePlayer('atletico-mg', 'Guilherme ATL MC', 25, 'MC', ['DM'], 'Right',
    makeAttrs(11, { tackling:13, marking:12, workRate:14, passing:12, stamina:13 }),
    makeHidden({ consistency:12 }), 1200000, 8000, 2),
  makePlayer('atletico-mg', 'Fernandinho ATL', 18, 'MC', ['AMC'], 'Right',
    makeAttrs(11, { creativity:13, technique:12, dribbling:12, passing:12, workRate:13 }),
    makeHidden({ consistency:11, ambition:16 }), 1000000, 5500, 3),
  makePlayer('atletico-mg', 'Lincoln Atletico', 25, 'MC', [], 'Right',
    makeAttrs(11, { passing:12, tackling:12, teamwork:13, decisions:11 }),
    makeHidden({ consistency:12 }), 900000, 7000, 2),
  makePlayer('atletico-mg', 'Arouca ATL MC', 23, 'MC', [], 'Right',
    makeAttrs(10, { tackling:12, passing:11, workRate:13 }),
    makeHidden({ consistency:11 }), 600000, 5500, 2),

  makePlayer('atletico-mg', 'Diego ATL ML', 23, 'ML', ['DL'], 'Left',
    makeAttrs(11, { crossing:12, dribbling:12, pace:12, stamina:12 }),
    makeHidden({ consistency:11 }), 900000, 6500, 2),
  makePlayer('atletico-mg', 'Junior ATL MR', 24, 'MR', ['DR'], 'Right',
    makeAttrs(10, { crossing:12, pace:12, dribbling:11 }),
    makeHidden({ consistency:11 }), 800000, 6000, 2),

  makePlayer('atletico-mg', 'Neto ATL AMC', 24, 'AMC', ['MC'], 'Right',
    makeAttrs(11, { technique:13, creativity:13, dribbling:12, firstTouch:12, finishing:11 }),
    makeHidden({ consistency:11 }), 1500000, 9000, 2),

  makePlayer('atletico-mg', 'Luan ATL SC', 21, 'SC', [], 'Right',
    makeAttrs(12, { finishing:14, pace:14, dribbling:13, technique:13, offTheBall:13 }),
    makeHidden({ consistency:12, ambition:15 }), 2000000, 9000, 3),
  makePlayer('atletico-mg', 'Fred Atletico', 23, 'SC', [], 'Right',
    makeAttrs(11, { finishing:14, heading:13, strength:14, offTheBall:13, bravery:13 }),
    makeHidden({ consistency:12 }), 1800000, 9500, 2),
  makePlayer('atletico-mg', 'Alecsandro ATL', 25, 'SC', [], 'Right',
    makeAttrs(11, { finishing:13, heading:13, strength:13 }),
    makeHidden({ consistency:11 }), 1200000, 7500, 2),
  makePlayer('atletico-mg', 'Borges ATL SC', 24, 'SC', [], 'Left',
    makeAttrs(10, { finishing:12, pace:13, dribbling:11 }),
    makeHidden({ consistency:11 }), 700000, 5500, 2),

  makePlayer('atletico-mg', 'Igor ATL DC', 21, 'DC', [], 'Right',
    makeAttrs(10, { marking:11, tackling:11 }),
    makeHidden({ consistency:10 }), 300000, 3500, 3),
  makePlayer('atletico-mg', 'Thiago ATL MC', 21, 'MC', [], 'Right',
    makeAttrs(10, { passing:11, workRate:12 }),
    makeHidden({ consistency:10 }), 250000, 3500, 3),
  makePlayer('atletico-mg', 'Ramón ATL DL', 23, 'DL', [], 'Left',
    makeAttrs(10, { crossing:11, pace:11 }),
    makeHidden({ consistency:10 }), 250000, 3500, 2),
  makePlayer('atletico-mg', 'Wendel ATL GK', 21, 'GK', [], 'Right',
    makeAttrs(7, { handling:9, reflexes:10 }),
    makeHidden({ consistency:9 }), 80000, 2000, 3),
  makePlayer('atletico-mg', 'Douglas ATL SC', 22, 'SC', [], 'Right',
    makeAttrs(9, { finishing:11, pace:11 }),
    makeHidden({ consistency:9 }), 200000, 3000, 3),
  makePlayer('atletico-mg', 'Elber ATL DR', 24, 'DR', [], 'Right',
    makeAttrs(10, { crossing:11, pace:11, tackling:10 }),
    makeHidden({ consistency:10 }), 300000, 3500, 2),
];

// -----------------------------------------------------------------
// 10. VASCO DA GAMA (mid-tier: base ~11)
// -----------------------------------------------------------------
const vascoPlayers: Player[] = [
  makePlayer('vasco', 'Léo Jardim GK', 25, 'GK', [], 'Right',
    makeAttrs(8, { aerial:13, command:12, handling:14, oneOnOnes:12, reflexes:14, concentration:12 }),
    makeHidden({ consistency:12 }), 1200000, 8000, 2),
  makePlayer('vasco', 'Maurício GK2', 26, 'GK', [], 'Right',
    makeAttrs(8, { handling:12, reflexes:12, aerial:11 }),
    makeHidden({ consistency:11 }), 350000, 4500, 2),

  makePlayer('vasco', 'Odvan Vasco', 28, 'DC', [], 'Right',
    makeAttrs(11, { marking:13, tackling:13, heading:13, concentration:13, strength:13 }),
    makeHidden({ consistency:12 }), 1200000, 8000, 1),
  makePlayer('vasco', 'Lúcio Vasco DC', 27, 'DC', ['SW'], 'Right',
    makeAttrs(11, { marking:12, tackling:13, heading:13, concentration:12, strength:13 }),
    makeHidden({ consistency:12 }), 1000000, 7500, 1),
  makePlayer('vasco', 'Dedé Vasco', 21, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11, heading:12, concentration:11 }),
    makeHidden({ consistency:11, ambition:14 }), 600000, 5000, 3),
  makePlayer('vasco', 'Rodrigo Vasco', 26, 'DC', [], 'Right',
    makeAttrs(10, { marking:12, tackling:11, heading:11 }),
    makeHidden({ consistency:11 }), 500000, 5000, 1),

  makePlayer('vasco', 'Renato Abreu DL', 23, 'DL', ['ML'], 'Left',
    makeAttrs(11, { crossing:12, pace:12, tackling:11, stamina:12, dribbling:12 }),
    makeHidden({ consistency:11 }), 900000, 6500, 2),
  makePlayer('vasco', 'Rafael Vasco DR', 24, 'DR', ['MR'], 'Right',
    makeAttrs(10, { crossing:12, pace:12, tackling:10, stamina:12 }),
    makeHidden({ consistency:11 }), 700000, 5500, 2),

  makePlayer('vasco', 'Marcelinho Carioca', 31, 'MC', ['AMC'], 'Right',
    makeAttrs(11, { technique:15, creativity:15, dribbling:13, flair:15, freekicks:15, corners:14, passing:13, longShots:13 }),
    makeHidden({ consistency:11, importantMatches:13 }), 800000, 10000, 1),
  makePlayer('vasco', 'Juninho Pernambucano V', 28, 'MC', ['AMC'], 'Right',
    makeAttrs(12, { passing:14, freekicks:16, technique:14, creativity:14, longShots:15, corners:14 }),
    makeHidden({ consistency:13, importantMatches:14 }), 3000000, 14000, 1),
  makePlayer('vasco', 'Volante Vasco MC', 26, 'MC', ['DM'], 'Right',
    makeAttrs(10, { tackling:13, marking:12, workRate:13, passing:11, stamina:13 }),
    makeHidden({ consistency:12 }), 800000, 6500, 2),
  makePlayer('vasco', 'Carlos Alberto V', 20, 'MC', ['AMC'], 'Right',
    makeAttrs(11, { creativity:13, technique:12, dribbling:12, passing:11 }),
    makeHidden({ consistency:11, ambition:15 }), 800000, 5500, 3),

  makePlayer('vasco', 'Ciro Vasco ML', 23, 'ML', ['DL'], 'Left',
    makeAttrs(10, { crossing:12, dribbling:11, pace:12, stamina:12 }),
    makeHidden({ consistency:11 }), 700000, 5500, 2),
  makePlayer('vasco', 'Pedro Ken MR', 24, 'MR', ['MC'], 'Right',
    makeAttrs(11, { crossing:12, pace:12, dribbling:12, technique:11 }),
    makeHidden({ consistency:11 }), 900000, 6500, 2),

  makePlayer('vasco', 'Expresso Vasco AMC', 25, 'AMC', ['SC'], 'Right',
    makeAttrs(11, { technique:13, creativity:13, dribbling:12, firstTouch:12, finishing:11 }),
    makeHidden({ consistency:11 }), 1200000, 8000, 2),

  makePlayer('vasco', 'Edmundo Vasco', 33, 'SC', [], 'Right',
    makeAttrs(11, { finishing:14, dribbling:13, technique:14, flair:14, composure:12, firstTouch:13 }),
    makeHidden({ consistency:11, importantMatches:12 }), 500000, 10000, 1),
  makePlayer('vasco', 'Bernardo Vasco', 25, 'SC', [], 'Right',
    makeAttrs(11, { finishing:13, heading:13, strength:13, offTheBall:12 }),
    makeHidden({ consistency:11 }), 1200000, 8000, 2),
  makePlayer('vasco', 'Alex Vasco SC', 24, 'SC', [], 'Left',
    makeAttrs(10, { finishing:12, pace:13, dribbling:11 }),
    makeHidden({ consistency:11 }), 700000, 5500, 2),
  makePlayer('vasco', 'Pablo Vasco SC', 22, 'SC', [], 'Right',
    makeAttrs(10, { finishing:12, heading:11, pace:11 }),
    makeHidden({ consistency:10 }), 500000, 4500, 3),

  makePlayer('vasco', 'Márcio Vasco DC', 22, 'DC', [], 'Right',
    makeAttrs(10, { marking:11, tackling:11 }),
    makeHidden({ consistency:10 }), 300000, 3500, 3),
  makePlayer('vasco', 'Vitor Vasco MC', 21, 'MC', [], 'Right',
    makeAttrs(10, { passing:11, workRate:11 }),
    makeHidden({ consistency:10 }), 250000, 3500, 3),
  makePlayer('vasco', 'Neto Vasco DL', 22, 'DL', [], 'Left',
    makeAttrs(9, { crossing:11, pace:11 }),
    makeHidden({ consistency:10 }), 200000, 3000, 3),
  makePlayer('vasco', 'Junior Vasco GK', 23, 'GK', [], 'Right',
    makeAttrs(7, { handling:10, reflexes:9 }),
    makeHidden({ consistency:9 }), 80000, 2000, 3),
  makePlayer('vasco', 'Rodrigo Pato Vasco', 21, 'SC', [], 'Right',
    makeAttrs(9, { finishing:11, pace:11 }),
    makeHidden({ consistency:9 }), 200000, 3000, 3),
  makePlayer('vasco', 'Guto Vasco AMC', 23, 'AMC', [], 'Right',
    makeAttrs(10, { technique:11, creativity:11 }),
    makeHidden({ consistency:10 }), 300000, 4000, 2),
];

// ============================================================
// Compile all players
// ============================================================
export const ALL_PLAYERS: Player[] = [
  ...cruzPlayers,
  ...spfcPlayers,
  ...santosPlayers,
  ...flamengoPlayers,
  ...gremioPlayers,
  ...interPlayers,
  ...corinthiansPlayers,
  ...palmeirasPlayers,
  ...atleticoMGPlayers,
  ...vascoPlayers,
];

// ============================================================
// CLUBS
// ============================================================
function buildPlayerMap(players: Player[]): { [id: string]: Player } {
  const map: { [id: string]: Player } = {};
  players.forEach(p => { map[p.id] = p; });
  return map;
}

function makeClub(
  id: string,
  name: string,
  shortName: string,
  city: string,
  reputation: number,
  budget: number,
  wageBudget: number,
  stadium: string,
  capacity: number,
  players: Player[],
  boardConfidence: number = 7,
  fanHappiness: number = 7,
): Club {
  const playerIds = players.map(p => p.id);
  return {
    id, name, shortName, city, reputation,
    budget, wageBudget, stadium, capacity,
    leagueId: 'brasileirao-serie-a',
    tactics: defaultTactic(id, playerIds),
    playerIds,
    finances: defaultFinances(budget, players.reduce((s, p) => s + p.wage, 0), budget * 0.3),
    boardConfidence, fanHappiness,
  };
}

export const CLUBS: Club[] = [
  makeClub('cruzeiro', 'Cruzeiro Esporte Clube', 'CRU', 'Belo Horizonte', 17, 12000000, 3000000, 'Mineirão', 61846, cruzPlayers, 7, 7),
  makeClub('saopaulo', 'São Paulo Futebol Clube', 'SPF', 'São Paulo', 18, 15000000, 4000000, 'Morumbi', 72000, spfcPlayers, 7, 7),
  makeClub('santos', 'Santos Futebol Clube', 'SAN', 'Santos', 17, 10000000, 3000000, 'Vila Belmiro', 16068, santosPlayers, 7, 7),
  makeClub('flamengo', 'Clube de Regatas do Flamengo', 'FLA', 'Rio de Janeiro', 16, 8000000, 2500000, 'Maracanã', 78838, flamengoPlayers, 7, 7),
  makeClub('gremio', 'Grêmio Foot-Ball Porto Alegrense', 'GRE', 'Porto Alegre', 15, 7000000, 2200000, 'Arena do Grêmio', 55000, gremioPlayers, 7, 7),
  makeClub('inter', 'Sport Club Internacional', 'INT', 'Porto Alegre', 15, 7000000, 2200000, 'Beira-Rio', 50128, interPlayers, 7, 7),
  makeClub('corinthians', 'Sport Club Corinthians Paulista', 'COR', 'São Paulo', 16, 8000000, 2500000, 'Parque São Jorge', 20000, corinthiansPlayers, 7, 7),
  makeClub('palmeiras', 'Sociedade Esportiva Palmeiras', 'PAL', 'São Paulo', 16, 8000000, 2400000, 'Palestra Itália', 40199, palmeirasPlayers, 7, 7),
  makeClub('atletico-mg', 'Clube Atlético Mineiro', 'CAM', 'Belo Horizonte', 14, 5000000, 1800000, 'Arena Independência', 23000, atleticoMGPlayers, 7, 7),
  makeClub('vasco', 'Club de Regatas Vasco da Gama', 'VAS', 'Rio de Janeiro', 14, 4000000, 1500000, 'São Januário', 21880, vascoPlayers, 7, 7),
];

export const CLUBS_MAP: { [id: string]: Club } = {};
CLUBS.forEach(c => { CLUBS_MAP[c.id] = c; });

export const PLAYERS_MAP: { [id: string]: Player } = buildPlayerMap(ALL_PLAYERS);

// ============================================================
// LEAGUE TABLE — initial empty state
// ============================================================
export function buildInitialLeagueTable(): LeagueTable[] {
  return CLUBS.map(club => ({
    clubId: club.id,
    played: 0, won: 0, drawn: 0, lost: 0,
    goalsFor: 0, goalsAgainst: 0, points: 0,
  }));
}

// ============================================================
// FIXTURE GENERATOR — full 38-round double round-robin
// ============================================================
export function generateFixtures(): Fixture[] {
  const clubIds = CLUBS.map(c => c.id);
  const n = clubIds.length; // 10 clubs
  const fixtures: Fixture[] = [];

  // Round-robin scheduling using the circle algorithm
  const teams = [...clubIds];
  const fixed = teams.pop()!; // fix last team
  const rounds = (n - 1) * 2; // 18 rounds each leg = 36 rounds total (but we do 38 by slight variant)

  // Generate first leg (rounds 1-9 for 10 teams)
  const firstLegRounds: { home: string; away: string }[][] = [];
  for (let round = 0; round < n - 1; round++) {
    const pairings: { home: string; away: string }[] = [];
    const home = round % 2 === 0 ? fixed : teams[0];
    const away = round % 2 === 0 ? teams[0] : fixed;
    pairings.push({ home, away });
    for (let i = 1; i < n / 2; i++) {
      const h = teams[(round + i) % (n - 1)];
      const a = teams[(round + n - 1 - i) % (n - 1)];
      if (round % 2 === 0) {
        pairings.push({ home: h, away: a });
      } else {
        pairings.push({ home: a, away: h });
      }
    }
    firstLegRounds.push(pairings);
  }

  // Start date: 2003-04-05
  const startDate = new Date('2003-04-05');

  let roundNum = 1;
  // First leg
  for (let r = 0; r < firstLegRounds.length; r++) {
    const matchDate = new Date(startDate);
    matchDate.setDate(matchDate.getDate() + r * 7);
    const dateStr = matchDate.toISOString().split('T')[0];
    firstLegRounds[r].forEach(pair => {
      fixtures.push({
        id: generateId('fix'),
        homeClubId: pair.home,
        awayClubId: pair.away,
        date: dateStr,
        leagueId: 'brasileirao-serie-a',
        round: roundNum,
        played: false,
      });
    });
    roundNum++;
  }

  // Second leg — swap home/away
  for (let r = 0; r < firstLegRounds.length; r++) {
    const matchDate = new Date(startDate);
    matchDate.setDate(matchDate.getDate() + (r + (n - 1)) * 7);
    const dateStr = matchDate.toISOString().split('T')[0];
    firstLegRounds[r].forEach(pair => {
      fixtures.push({
        id: generateId('fix'),
        homeClubId: pair.away,
        awayClubId: pair.home,
        date: dateStr,
        leagueId: 'brasileirao-serie-a',
        round: roundNum,
        played: false,
      });
    });
    roundNum++;
  }

  // Sort by date then round
  fixtures.sort((a, b) => a.date.localeCompare(b.date) || a.round - b.round);
  return fixtures;
}

// ============================================================
// PRESS QUESTIONS
// ============================================================
import { PressQuestion } from './types';

export const PRESS_QUESTIONS: PressQuestion[] = [
  {
    id: 'pq_001',
    question: 'Como você avalia o desempenho do time nas últimas semanas?',
    options: [
      { text: 'Estamos jogando muito bem, a equipe está em grande fase.', moraleEffect: 2, boardEffect: 1, fanEffect: 1 },
      { text: 'Temos melhorado, mas ainda há espaço para crescer.', moraleEffect: 1, boardEffect: 0, fanEffect: 0 },
      { text: 'Precisamos trabalhar mais, o nível ainda não está bom.', moraleEffect: -1, boardEffect: 0, fanEffect: -1 },
    ],
  },
  {
    id: 'pq_002',
    question: 'Vocês estão de olho no mercado de transferências?',
    options: [
      { text: 'Estamos monitorando o mercado e agiremos na hora certa.', moraleEffect: 0, boardEffect: 1, fanEffect: 1 },
      { text: 'Estou satisfeito com o atual elenco, não precisamos de reforços.', moraleEffect: 1, boardEffect: 0, fanEffect: 0 },
      { text: 'Precisamos de reforços urgentes, o elenco não é suficiente.', moraleEffect: -1, boardEffect: -1, fanEffect: 0 },
    ],
  },
  {
    id: 'pq_003',
    question: 'O que você espera do próximo jogo?',
    options: [
      { text: 'Vamos buscar os três pontos, temos que vencer.', moraleEffect: 2, boardEffect: 1, fanEffect: 2 },
      { text: 'Será um jogo difícil, mas daremos o nosso melhor.', moraleEffect: 1, boardEffect: 0, fanEffect: 0 },
      { text: 'Vamos jogar com cautela e tentar não sofrer gols.', moraleEffect: 0, boardEffect: 0, fanEffect: -1 },
    ],
  },
  {
    id: 'pq_004',
    question: 'Como está o clima no vestiário?',
    options: [
      { text: 'Perfeito, o grupo está muito unido e motivado.', moraleEffect: 2, boardEffect: 1, fanEffect: 1 },
      { text: 'Temos nossas diferenças mas somos profissionais.', moraleEffect: 0, boardEffect: 0, fanEffect: 0 },
      { text: 'Há algumas tensões que estamos trabalhando para resolver.', moraleEffect: -2, boardEffect: -1, fanEffect: -1 },
    ],
  },
  {
    id: 'pq_005',
    question: 'Você está satisfeito com o apoio da diretoria?',
    options: [
      { text: 'A diretoria tem sido excelente, total suporte ao trabalho.', moraleEffect: 0, boardEffect: 2, fanEffect: 0 },
      { text: 'Estamos trabalhando bem juntos dentro das possibilidades.', moraleEffect: 0, boardEffect: 1, fanEffect: 0 },
      { text: 'Gostaríamos de mais investimento para competir de igual para igual.', moraleEffect: 0, boardEffect: -2, fanEffect: 1 },
    ],
  },
  {
    id: 'pq_006',
    question: 'Algum jogador chave pode estar indisponível para o próximo jogo?',
    options: [
      { text: 'Não, o grupo está completo e todos estão prontos para jogar.', moraleEffect: 1, boardEffect: 0, fanEffect: 0 },
      { text: 'Temos algumas dúvidas que serão resolvidas no treino.', moraleEffect: 0, boardEffect: 0, fanEffect: 0 },
      { text: 'Infelizmente sim, mas confio nos jogadores que entrarão.', moraleEffect: -1, boardEffect: 0, fanEffect: -1 },
    ],
  },
  {
    id: 'pq_007',
    question: 'Qual é o objetivo do clube nesta temporada?',
    options: [
      { text: 'Queremos ser campeões, nada menos que isso nos satisfaz.', moraleEffect: 2, boardEffect: 1, fanEffect: 2 },
      { text: 'Estamos buscando uma classificação para competições continentais.', moraleEffect: 1, boardEffect: 1, fanEffect: 1 },
      { text: 'Nossa meta é a consolidação do time e um bom resultado.', moraleEffect: 0, boardEffect: 0, fanEffect: -1 },
    ],
  },
  {
    id: 'pq_008',
    question: 'Como você responde às críticas da torcida?',
    options: [
      { text: 'A torcida tem razão em exigir mais, vamos melhorar.', moraleEffect: -1, boardEffect: 0, fanEffect: 2 },
      { text: 'Respeito a opinião dos torcedores, mas confiamos no trabalho.', moraleEffect: 0, boardEffect: 0, fanEffect: 1 },
      { text: 'As críticas são precipitadas, o processo leva tempo.', moraleEffect: 1, boardEffect: 0, fanEffect: -2 },
    ],
  },
];
