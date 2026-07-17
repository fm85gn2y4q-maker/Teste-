export function formatBRL(value: number): string {
  const fixed = Math.abs(value).toFixed(2).replace('.', ',');
  const sign = value < 0 ? '-' : '';
  return `${sign}R$ ${fixed}`;
}

export function formatPct(value: number): string {
  return `${Math.round(value)}%`;
}
