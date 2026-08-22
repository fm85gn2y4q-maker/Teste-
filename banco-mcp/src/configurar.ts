#!/usr/bin/env node
/**
 * Guarda as credenciais da Pluggy no .env, depois de conferir que elas
 * funcionam. Escrever chave errada num arquivo e o erro que so aparece tres
 * comandos depois — aqui ele aparece na hora.
 */
import { readFileSync, writeFileSync, existsSync, chmodSync } from 'node:fs';
import { resolve } from 'node:path';
import { carregarDotEnv } from './util/env.js';
import { definirChave, lerChave } from './util/envArquivo.js';
import { perguntar } from './util/pergunta.js';
import { ClientePluggy } from './providers/pluggy/cliente.js';

const CAMINHO = resolve(process.cwd(), '.env');
carregarDotEnv(process.cwd());

/**
 * Quando o instalador chega por `irm | iex` (ou `curl | bash`), a entrada
 * padrao do shell ja foi consumida pelo cano e o processo filho herda um stdin
 * fechado: qualquer pergunta le vazio na hora. Nesse caso o shell coleta as
 * credenciais e as repassa por ambiente, e este comando roda sem perguntar.
 */
function credenciaisDoAmbiente(): { clientId: string; clientSecret: string } | null {
  const clientId = process.env.PLUGGY_CLIENT_ID?.trim();
  const clientSecret = process.env.PLUGGY_CLIENT_SECRET?.trim();
  return clientId && clientSecret ? { clientId, clientSecret } : null;
}

async function main(): Promise<number> {
  if (process.argv.includes('--do-ambiente')) {
    const doAmbiente = credenciaisDoAmbiente();
    if (!doAmbiente) {
      console.log('\n  --do-ambiente exige PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET definidos.\n');
      return 1;
    }
    return await gravar(doAmbiente.clientId, doAmbiente.clientSecret);
  }

  if (!process.stdin.isTTY) {
    console.log('\n  Este comando precisa de um terminal interativo para perguntar as credenciais,');
    console.log('  e a entrada padrao deste processo esta fechada — costuma acontecer quando o');
    console.log('  instalador vem por "irm | iex" ou "curl | bash".\n');
    console.log('  Rode direto na pasta do projeto:\n');
    console.log('    npm run configurar\n');
    return 1;
  }

  console.log('\nCredenciais da Pluggy (Dashboard > sua aplicacao)');
  console.log('Elas ficam so neste computador, no arquivo .env. Nao cole clientSecret');
  console.log('em chat, ticket ou commit: quem tem o par le todas as suas contas.\n');

  const atualId = process.env.PLUGGY_CLIENT_ID;
  if (atualId) console.log(`  Ja ha um clientId gravado (${atualId.slice(0, 4)}…). Enter mantem o atual.\n`);

  const clientId = (await perguntar('  clientId:     ')) || atualId || '';
  if (!clientId) {
    console.log('\n  Sem clientId nao da para seguir.\n');
    return 1;
  }

  const clientSecret = (await perguntar('  clientSecret (aparece como asteriscos): ', true)) || process.env.PLUGGY_CLIENT_SECRET || '';
  if (!clientSecret) {
    console.log('\n  Sem clientSecret nao da para seguir.\n');
    return 1;
  }

  return await gravar(clientId, clientSecret);
}

async function gravar(clientId: string, clientSecret: string): Promise<number> {
  const baseUrl = process.env.PLUGGY_BASE_URL ?? 'https://api.pluggy.ai';
  process.stdout.write('\n  Conferindo com a Pluggy... ');
  try {
    await new ClientePluggy({ clientId, clientSecret, baseUrl }).verificarCredenciais();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    console.log('nao passou.\n');
    console.log(`  ${msg}\n`);
    console.log(msg.includes('403') || msg.includes('401')
      ? '  Confira se copiou clientId e clientSecret da MESMA aplicacao no Dashboard.\n'
      : '  Parece problema de rede, nao de credencial. Tente de novo.\n');
    return 1;
  }
  console.log('ok, credenciais aceitas.');

  const atual = existsSync(CAMINHO) ? readFileSync(CAMINHO, 'utf8') : '';
  let conteudo = definirChave(atual, 'PLUGGY_CLIENT_ID', clientId);
  conteudo = definirChave(conteudo, 'PLUGGY_CLIENT_SECRET', clientSecret);
  conteudo = definirChave(conteudo, 'BANCO_MCP_PROVEDOR', 'pluggy');
  writeFileSync(CAMINHO, conteudo, 'utf8');
  // O arquivo guarda credencial: so o dono le.
  try { chmodSync(CAMINHO, 0o600); } catch { /* sistema sem permissao POSIX */ }

  console.log(`  Gravado em ${CAMINHO} (permissao 600).\n`);

  const itens = lerChave(conteudo, 'PLUGGY_ITEM_IDS');
  if (itens) {
    console.log(`  Ja ha ${itens.split(',').filter(Boolean).length} conexao(oes) gravada(s).`);
    console.log('  Proximo passo:  npm run diagnostico\n');
  } else {
    console.log('  Proximo passo:  npm run conectar\n');
  }
  return 0;
}

main().then((c) => { process.exitCode = c; }).catch((e) => {
  console.log(`\n  ${e instanceof Error ? e.message : String(e)}\n`);
  process.exitCode = 1;
});
