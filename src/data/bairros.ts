export interface Bairro {
  id: string;
  name: string;
  zone: string;
  /** Multiplicador de custo de vida do bairro (afeta preços dos mercados locais). */
  costFactor: number;
  /** Distância média (km) até um mercado dentro do próprio bairro. */
  internalKm: number;
  /** Bairros vizinhos considerados "próximos" e a distância média até eles. */
  adjacent: { bairroId: string; km: number }[];
}

export const BAIRROS: Bairro[] = [
  {
    id: 'barra',
    name: 'Barra da Tijuca',
    zone: 'Zona Oeste',
    costFactor: 1.05,
    internalKm: 3,
    adjacent: [
      { bairroId: 'recreio', km: 8 },
      { bairroId: 'jacarepagua', km: 7 },
      { bairroId: 'sao-conrado', km: 6 },
    ],
  },
  {
    id: 'recreio',
    name: 'Recreio dos Bandeirantes',
    zone: 'Zona Oeste',
    costFactor: 0.98,
    internalKm: 2.5,
    adjacent: [
      { bairroId: 'barra', km: 8 },
      { bairroId: 'jacarepagua', km: 11 },
    ],
  },
  {
    id: 'jacarepagua',
    name: 'Jacarepaguá (Freguesia)',
    zone: 'Zona Oeste',
    costFactor: 0.94,
    internalKm: 3,
    adjacent: [
      { bairroId: 'barra', km: 7 },
      { bairroId: 'recreio', km: 11 },
      { bairroId: 'tijuca', km: 10 },
    ],
  },
  {
    id: 'sao-conrado',
    name: 'São Conrado',
    zone: 'Zona Sul',
    costFactor: 1.08,
    internalKm: 1.5,
    adjacent: [
      { bairroId: 'barra', km: 6 },
      { bairroId: 'ipanema-leblon', km: 4 },
    ],
  },
  {
    id: 'ipanema-leblon',
    name: 'Ipanema / Leblon',
    zone: 'Zona Sul',
    costFactor: 1.12,
    internalKm: 1.2,
    adjacent: [
      { bairroId: 'copacabana', km: 3 },
      { bairroId: 'sao-conrado', km: 4 },
      { bairroId: 'botafogo', km: 5 },
    ],
  },
  {
    id: 'copacabana',
    name: 'Copacabana',
    zone: 'Zona Sul',
    costFactor: 1.06,
    internalKm: 1.2,
    adjacent: [
      { bairroId: 'ipanema-leblon', km: 3 },
      { bairroId: 'botafogo', km: 4 },
    ],
  },
  {
    id: 'botafogo',
    name: 'Botafogo',
    zone: 'Zona Sul',
    costFactor: 1.04,
    internalKm: 1.3,
    adjacent: [
      { bairroId: 'copacabana', km: 4 },
      { bairroId: 'ipanema-leblon', km: 5 },
      { bairroId: 'centro', km: 6 },
      { bairroId: 'tijuca', km: 7 },
    ],
  },
  {
    id: 'tijuca',
    name: 'Tijuca',
    zone: 'Zona Norte',
    costFactor: 0.98,
    internalKm: 1.8,
    adjacent: [
      { bairroId: 'centro', km: 6 },
      { bairroId: 'meier', km: 6 },
      { bairroId: 'botafogo', km: 7 },
      { bairroId: 'jacarepagua', km: 10 },
    ],
  },
  {
    id: 'centro',
    name: 'Centro',
    zone: 'Centro',
    costFactor: 1.0,
    internalKm: 1.5,
    adjacent: [
      { bairroId: 'botafogo', km: 6 },
      { bairroId: 'tijuca', km: 6 },
      { bairroId: 'meier', km: 8 },
    ],
  },
  {
    id: 'meier',
    name: 'Méier',
    zone: 'Zona Norte',
    costFactor: 0.93,
    internalKm: 1.5,
    adjacent: [
      { bairroId: 'tijuca', km: 6 },
      { bairroId: 'centro', km: 8 },
    ],
  },
];

export function getBairro(bairroId: string): Bairro {
  const b = BAIRROS.find((x) => x.id === bairroId);
  if (!b) throw new Error(`Bairro desconhecido: ${bairroId}`);
  return b;
}

/** Distância (km) do morador de `homeId` até mercados do bairro `targetId`, ou null se longe. */
export function distanceKm(homeId: string, targetId: string): number | null {
  const home = getBairro(homeId);
  if (homeId === targetId) return home.internalKm;
  const link = home.adjacent.find((a) => a.bairroId === targetId);
  return link ? link.km : null;
}
