// ============================================================
// Championship Manager 03/04 Clone — AI Transfer Engine
// Pure function: no side effects, returns all state updates.
// ============================================================

import { Club, Player, NewsItem, GameState } from '../types';

// -------------------------------------------------------
// Utility
// -------------------------------------------------------
function rand(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

let _idCounter = 800000; // distinct range from matchEngine.ts
function generateId(prefix = 'id'): string {
  return `${prefix}_${(_idCounter++).toString().padStart(6, '0')}`;
}

// -------------------------------------------------------
// Result type
// -------------------------------------------------------
export interface AITransferResult {
  clubs: { [id: string]: Club };
  players: { [id: string]: Player };
  news: NewsItem[];
  /** Number of completed transfers this tick */
  completedTransfers: number;
}

// -------------------------------------------------------
// Main AI transfer function
//
// Called once per simulated day from advanceDay.
// Each AI club has a 10% chance per WEEK to attempt a bid.
// To convert: daily probability = 1 - (1 - 0.10)^(1/7) ≈ 1.5% per day.
// -------------------------------------------------------
const DAILY_ATTEMPT_PROB = 1 - Math.pow(1 - 0.10, 1 / 7); // ~0.015 per day

export function processAITransfers(state: GameState): AITransferResult {
  const clubs: { [id: string]: Club } = { ...state.clubs };
  const players: { [id: string]: Player } = { ...state.players };
  const news: NewsItem[] = [];
  let completedTransfers = 0;

  // Build a lookup for all AI club IDs (exclude user)
  const aiClubIds = Object.keys(clubs).filter((id) => id !== state.userClubId);

  for (const buyerClubId of aiClubIds) {
    // Daily probability check (weekly 10% → daily ≈1.5%)
    if (Math.random() > DAILY_ATTEMPT_PROB) continue;

    const buyer = clubs[buyerClubId];
    if (!buyer) continue;
    if (buyer.budget < 100_000) continue; // not enough money to bother

    // Pick a target club (not self, not user)
    const potentialTargetClubs = Object.keys(clubs).filter(
      (id) => id !== buyerClubId && id !== state.userClubId,
    );
    if (potentialTargetClubs.length === 0) continue;

    const targetClubId = potentialTargetClubs[rand(0, potentialTargetClubs.length - 1)];
    const targetClub = clubs[targetClubId];
    if (!targetClub) continue;

    // Target must have enough players to sell one without hollowing out the squad
    if (targetClub.playerIds.length < 18) continue;

    // Pick a candidate from the target club — prefer players whose value fits the buyer's budget
    const candidateIds = targetClub.playerIds.filter((id) => {
      const p = players[id];
      if (!p) return false;
      if (p.condition === 'Injured') return false; // AI won't bid on injured players
      // Don't steal the keeper if it would leave target with none
      if (p.position === 'GK') {
        const targetKeepers = targetClub.playerIds.filter(
          (pid) => players[pid]?.position === 'GK',
        ).length;
        if (targetKeepers <= 1) return false;
      }
      return p.value <= buyer.budget * 1.5; // willing to stretch a bit
    });

    if (candidateIds.length === 0) continue;

    // Weighted pick — prefer cheaper (more affordable) players
    const candidateWeights = candidateIds.map((id) => {
      const p = players[id];
      if (!p) return 0;
      // Higher weight for players that cost less relative to budget
      const affordRatio = buyer.budget / Math.max(1, p.value);
      return Math.max(0.1, Math.min(affordRatio, 5));
    });

    let candidateIdx: number | null = null;
    {
      const total = candidateWeights.reduce((s, w) => s + w, 0);
      let r = Math.random() * total;
      for (let i = 0; i < candidateIds.length; i++) {
        r -= candidateWeights[i];
        if (r <= 0) { candidateIdx = i; break; }
      }
      if (candidateIdx === null) candidateIdx = 0;
    }

    const candidateId = candidateIds[candidateIdx];
    const candidate = players[candidateId];
    if (!candidate) continue;

    // Offer amount: value × (0.8 + random(0, 0.4))
    const offerAmount = Math.round(candidate.value * (0.8 + Math.random() * 0.4));

    // Can buyer actually afford it?
    if (offerAmount > buyer.budget) continue;

    // --- Selling club decision ---
    // AI auto-accepts if offer > 90% of player value
    const acceptanceThreshold = candidate.value * 0.9;
    const willAccept = offerAmount >= acceptanceThreshold;

    // Player loyalty: loyal players are harder to prise away
    // loyaltyResistance 0-1: higher = harder to sell
    const loyaltyResistance = candidate.hidden.loyalty / 20;
    if (Math.random() < loyaltyResistance * 0.5) continue; // player refuses to move

    // The target club must still have budget room to function (wage check)
    // Simplified: seller always accepts if offer is good enough
    if (!willAccept) continue;

    // --- Execute transfer ---
    const updatedCandidate: Player = {
      ...candidate,
      clubId: buyerClubId,
      morale: Math.min(10, candidate.morale + 1), // happy about the move
    };

    const updatedTargetClub: Club = {
      ...targetClub,
      playerIds: targetClub.playerIds.filter((id) => id !== candidateId),
      budget: targetClub.budget + offerAmount,
      finances: {
        ...targetClub.finances,
        transferIncome: targetClub.finances.transferIncome + offerAmount,
      },
    };

    const updatedBuyerClub: Club = {
      ...buyer,
      playerIds: [...buyer.playerIds, candidateId],
      budget: buyer.budget - offerAmount,
      finances: {
        ...buyer.finances,
        transferExpenditure: buyer.finances.transferExpenditure + offerAmount,
      },
    };

    // Commit changes into our mutable copies
    players[candidateId] = updatedCandidate;
    clubs[targetClubId] = updatedTargetClub;
    clubs[buyerClubId] = updatedBuyerClub;
    completedTransfers++;

    // --- Generate news item ---
    const formattedAmount = (offerAmount / 1_000_000).toFixed(1);
    const fromClubName = targetClub.name;
    const toClubName = buyer.name;
    const playerName = candidate.name;

    const headlines = [
      `${playerName} assina com ${toClubName}`,
      `${toClubName} confirma contratação de ${playerName}`,
      `${playerName} deixa ${fromClubName} e vai para ${toClubName}`,
      `Negócio fechado: ${playerName} é reforço do ${toClubName}`,
    ];
    const headline = headlines[rand(0, headlines.length - 1)];

    const bodies = [
      `${toClubName} anunciou a contratação de ${playerName} por R$ ${formattedAmount} milhões. O jogador assinou contrato e já está à disposição do treinador.`,
      `${playerName} está de malas prontas! O atleta deixa ${fromClubName} e reforça o ${toClubName} pelo valor de R$ ${formattedAmount} milhões.`,
      `Negócio concluído entre ${fromClubName} e ${toClubName}. ${playerName} muda de clube por R$ ${formattedAmount} milhões e deve ser apresentado em breve.`,
    ];
    const body = bodies[rand(0, bodies.length - 1)];

    news.push({
      id: generateId('news'),
      date: state.currentDate,
      headline,
      body,
      category: 'Transfer',
      clubId: buyerClubId,
    });
  }

  return { clubs, players, news, completedTransfers };
}

// -------------------------------------------------------
// Re-export helper type for store integration
// -------------------------------------------------------
export type { Club, Player, NewsItem };
