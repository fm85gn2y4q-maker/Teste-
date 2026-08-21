import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Carrega o .env do diretorio do projeto, se houver. Usa o carregador nativo do
 * Node (>=20.12) — nao vale uma dependencia so para ler chave=valor.
 * Variavel ja definida no ambiente continua valendo: o .env e o piso, nao o teto.
 */
export function carregarDotEnv(...diretorios: string[]): string | null {
  const candidatos = diretorios.length ? diretorios : [process.cwd()];
  const caminho = candidatos.map((d) => resolve(d, '.env')).find((c) => existsSync(c));
  if (!caminho) return null;
  try {
    const jaDefinidas = new Map(Object.entries(process.env));
    process.loadEnvFile(caminho);
    for (const [chave, valor] of jaDefinidas) {
      if (valor !== undefined) process.env[chave] = valor;
    }
    return caminho;
  } catch {
    return null;
  }
}
