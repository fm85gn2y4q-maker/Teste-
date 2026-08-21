/** PRNG deterministico (mulberry32). Mesma semente, mesmo acervo, sempre. */
export function criarRng(semente: number) {
  let a = semente >>> 0;
  const proximo = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return {
    proximo,
    /** Inteiro em [min, max]. */
    inteiro: (min: number, max: number) => min + Math.floor(proximo() * (max - min + 1)),
    /** Centavos em [min, max], arredondado para o centavo. */
    centavos: (min: number, max: number) => Math.round(min + proximo() * (max - min)),
    escolher: <T>(itens: readonly T[]): T => itens[Math.floor(proximo() * itens.length)]!,
    chance: (p: number) => proximo() < p,
  };
}

export type Rng = ReturnType<typeof criarRng>;
