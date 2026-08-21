/**
 * Edicao ciruegica do .env: mexe so nas chaves pedidas e preserva comentario,
 * ordem e tudo mais que o usuario tenha escrito ali.
 */
export function definirChave(conteudo: string, chave: string, valor: string): string {
  const linhas = conteudo.split('\n');
  // Sem isso, acrescentar chave num arquivo terminado em newline cria linha em branco.
  while (linhas.length > 0 && linhas[linhas.length - 1]!.trim() === '') linhas.pop();
  const idx = linhas.findIndex((l) => l.startsWith(`${chave}=`));
  if (idx >= 0) linhas[idx] = `${chave}=${valor}`;
  else linhas.push(`${chave}=${valor}`);
  return `${linhas.join('\n').replace(/\n+$/, '')}\n`;
}

export function lerChave(conteudo: string, chave: string): string | null {
  const linha = conteudo.split('\n').find((l) => l.startsWith(`${chave}=`));
  return linha ? linha.slice(chave.length + 1) : null;
}

/** Junta os ids ja gravados com os novos, sem repetir e sem perder a ordem. */
export function mesclarItemIds(conteudo: string, novos: string[]): { conteudo: string; itens: string[] } {
  const atuais = (lerChave(conteudo, 'PLUGGY_ITEM_IDS') ?? '').split(',');
  const itens = [...new Set([...atuais, ...novos].map((s) => s.trim()).filter(Boolean))];
  let saida = definirChave(conteudo, 'PLUGGY_ITEM_IDS', itens.join(','));
  saida = definirChave(saida, 'BANCO_MCP_PROVEDOR', 'pluggy');
  return { conteudo: saida, itens };
}
