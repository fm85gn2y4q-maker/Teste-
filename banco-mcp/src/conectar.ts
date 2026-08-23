#!/usr/bin/env node
/**
 * Fluxo de conexao: sobe uma pagina local que abre o Pluggy Connect, voce
 * autoriza cada banco no ambiente do proprio banco, e os ids das conexoes
 * (items) caem no .env sozinhos.
 *
 * Nenhuma credencial de banco passa por aqui: o widget fala direto com a
 * Pluggy, e o que volta para este processo e so o identificador da conexao.
 */
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { carregarDotEnv } from './util/env.js';
import { mesclarItemIds } from './util/envArquivo.js';
import { ClientePluggy } from './providers/pluggy/cliente.js';
import { carregarConfig } from './config.js';

carregarDotEnv();
const config = carregarConfig();
const CAMINHO_ENV = resolve(process.cwd(), '.env');
const PORTA = Number(process.env.BANCO_MCP_PORTA_CONEXAO ?? 8788);
// O pacote publicado nao traz bundle de navegador e depende de zoid e
// jwt-decode, entao servi-lo local exigiria um empacotador. O /+esm do
// jsDelivr resolve as dependencias e entrega um modulo pronto.
const URL_WIDGET = process.env.PLUGGY_CONNECT_URL
  ?? 'https://cdn.jsdelivr.net/npm/pluggy-connect-sdk@2.14.2/+esm';

function log(msg: string): void {
  process.stdout.write(`${msg}\n`);
}

if (!config.pluggy.clientId || !config.pluggy.clientSecret) {
  log('Faltam PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET.');
  log('Pegue os dois no Dashboard da Pluggy e coloque no arquivo .env (veja .env.example).');
  process.exit(1);
}

const cliente = new ClientePluggy({
  clientId: config.pluggy.clientId,
  clientSecret: config.pluggy.clientSecret,
  baseUrl: config.pluggy.baseUrl,
});

/** Le os ids ja gravados, junta com os novos e regrava o .env preservando o resto. */
function gravarItens(novos: string[]): string[] {
  const atual = existsSync(CAMINHO_ENV) ? readFileSync(CAMINHO_ENV, 'utf8') : '';
  const { conteudo, itens } = mesclarItemIds(atual, novos);
  writeFileSync(CAMINHO_ENV, conteudo, 'utf8');
  process.env.PLUGGY_ITEM_IDS = itens.join(',');
  return itens;
}

async function corpoJson(req: IncomingMessage): Promise<Record<string, unknown>> {
  const pedacos: Buffer[] = [];
  let tamanho = 0;
  for await (const p of req) {
    tamanho += (p as Buffer).length;
    if (tamanho > 64 * 1024) throw new Error('corpo grande demais');
    pedacos.push(p as Buffer);
  }
  const texto = Buffer.concat(pedacos).toString('utf8');
  return texto ? JSON.parse(texto) as Record<string, unknown> : {};
}

const PAGINA = (token: string) => `<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Conectar bancos — Banco MCP</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 16px/1.55 system-ui, -apple-system, sans-serif; max-width: 44rem; margin: 3rem auto; padding: 0 1.25rem; }
  h1 { font-size: 1.5rem; margin-bottom: .25rem; }
  p.sub { color: #6b7280; margin-top: 0; }
  button { font: inherit; padding: .7rem 1.2rem; border-radius: .5rem; border: 0; background: #6C3DE8; color: #fff; cursor: pointer; }
  button.secundario { background: transparent; color: inherit; border: 1px solid currentColor; }
  input { font: inherit; padding: .6rem; width: 22rem; max-width: 100%; border-radius: .5rem; border: 1px solid #9ca3af; background: transparent; color: inherit; }
  ul { padding-left: 1.1rem; }
  .caixa { border: 1px solid #9ca3af55; border-radius: .75rem; padding: 1rem 1.25rem; margin: 1.5rem 0; }
  .aviso { border-left: 3px solid #d97706; padding-left: .9rem; color: #92400e; background: #fef3c722; }
  code { background: #9ca3af22; padding: .15rem .35rem; border-radius: .25rem; }
</style></head>
<body>
<h1>Conectar seus bancos</h1>
<p class="sub">Voce autoriza cada banco no ambiente do proprio banco. Sua senha nao passa por este servidor.</p>

<div class="caixa">
  <button id="abrir">Abrir o Pluggy Connect</button>
  <p id="estado"></p>
</div>

<div class="caixa" id="manual">
  <strong>Ou cole o id da conexao</strong>
  <p class="sub">No Dashboard da Pluggy: abra sua aplicacao, conecte o conector
  <strong>Meu Pluggy</strong> entrando com a conta onde seus bancos ja estao, e
  copie o <code>itemId</code> que aparecer. Este caminho nao depende de CDN.</p>
  <p><input id="itemId" placeholder="00000000-0000-0000-0000-000000000000" autocomplete="off">
  <button class="secundario" id="salvarManual">Salvar</button></p>
</div>

<div class="caixa">
  <strong>Conexoes gravadas no .env</strong>
  <ul id="lista"><li>nenhuma ainda</li></ul>
  <p class="sub">Quando terminar, feche esta aba e volte ao terminal.</p>
</div>

<script type="module">
const estado = document.getElementById('estado');
const lista = document.getElementById('lista');

async function salvar(itemId) {
  const r = await fetch('/salvar', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ itemId }),
  });
  const dados = await r.json();
  if (!r.ok) { estado.textContent = 'Nao consegui gravar: ' + (dados.erro || r.status); return; }
  lista.innerHTML = dados.itens.map((i) => '<li><code>' + i + '</code></li>').join('');
  estado.textContent = 'Conexao gravada. Pode conectar outro banco.';
}

// O campo manual nao depende de nada externo: e o caminho que sempre funciona.
document.getElementById('salvarManual').onclick = () => {
  const v = document.getElementById('itemId').value.trim();
  if (v) salvar(v);
};

// O widget depende de CDN, e CDN cai. Se nao carregar, a pagina continua util.
try {
  const { PluggyConnect } = await import('${URL_WIDGET}');
  document.getElementById('abrir').onclick = async () => {
    estado.textContent = 'Abrindo...';
    const { token } = await (await fetch('/token')).json();
    new PluggyConnect({
      connectToken: token,
      includeSandbox: ${config.pluggy.baseUrl.includes('sandbox') ? 'true' : 'false'},
      onSuccess: (dados) => salvar(dados?.item?.id),
      onError: (e) => { estado.textContent = 'O Connect devolveu um erro: ' + JSON.stringify(e); },
    }).init();
  };
} catch (e) {
  document.getElementById('abrir').disabled = true;
  estado.innerHTML = '<span class="aviso">Nao consegui carregar o widget da Pluggy ' +
    '(' + (e?.message || e) + '). Use o campo abaixo — ele nao depende de CDN.</span>';
}
</script>
</body></html>`;

/**
 * Modo --listar: quem ja conectou os bancos no Meu Pluggy nao precisa de
 * navegador nenhum. As conexoes ja existem na conta; aqui so perguntamos quais
 * sao e gravamos os ids.
 */
async function listar(): Promise<number> {
  log('\n  Procurando conexoes ja existentes na sua conta Pluggy...\n');

  let itens: Array<{ id: string; status?: string; connector?: { name?: string } }>;
  try {
    itens = await cliente.paginar('/items');
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    log(`  Nao consegui listar: ${msg}\n`);
    // A Pluggy responde 401 a quem pede a lista inteira de items, e 404/405 a
    // quem cai num endpoint que a conta nao tem. Nos tres casos a saida e a
    // mesma: conectar pelo navegador. So um erro de rede merece outra leitura.
    if (/40[1345]/.test(msg)) {
      log('  Esta conta nao expoe a lista de conexoes pela API — e comum, nao e erro seu.');
      log('  A credencial esta certa (a autenticacao passou); o que falta e o id de');
      log('  cada conexao. Pegue-os pelo navegador:\n');
      log('    npm run conectar\n');
      log('  Ou copie os ids no Dashboard da Pluggy e ponha em PLUGGY_ITEM_IDS no .env.\n');
    }
    return 1;
  }

  if (itens.length === 0) {
    log('  Nenhuma conexao encontrada.');
    log('  Conecte seus bancos em meu.pluggy.ai e rode este comando de novo.\n');
    return 1;
  }

  for (const i of itens) {
    log(`  ${i.id}  ${i.connector?.name ?? '(conector desconhecido)'}  ${i.status ?? ''}`);
  }

  const gravados = gravarItens(itens.map((i) => i.id));
  log(`\n  ${gravados.length} conexoes gravadas no .env.`);
  log('  Proximo passo:  npm run diagnostico\n');
  return 0;
}

if (process.argv.includes('--listar')) {
  listar().then((c) => { process.exitCode = c; }).catch((e) => {
    log(`  erro: ${e instanceof Error ? e.message : String(e)}`);
    process.exitCode = 1;
  });
}

const servidor = createServer((req, res) => {
  void (async () => {
    const url = new URL(req.url ?? '/', `http://127.0.0.1:${PORTA}`);

    if (req.method === 'GET' && url.pathname === '/') {
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
      res.end(PAGINA(''));
      return;
    }

    if (req.method === 'GET' && url.pathname === '/token') {
      const token = await cliente.criarConnectToken();
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ token }));
      return;
    }

    if (req.method === 'POST' && url.pathname === '/salvar') {
      const corpo = await corpoJson(req);
      const itemId = String(corpo.itemId ?? '').trim();
      if (!/^[a-zA-Z0-9-]{8,64}$/.test(itemId)) {
        res.writeHead(400, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ erro: 'itemId invalido' }));
        return;
      }
      const itens = gravarItens([itemId]);
      log(`conexao gravada: ${itemId}  (total: ${itens.length})`);
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ itens }));
      return;
    }

    res.writeHead(404).end();
  })().catch((e) => {
    const msg = e instanceof Error ? e.message : String(e);
    log(`erro: ${msg}`);
    if (!res.headersSent) {
      res.writeHead(500, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ erro: msg }));
    }
  });
});

if (!process.argv.includes('--listar')) servidor.listen(PORTA, '127.0.0.1', () => {
  log('');
  log(`  Abra no navegador:  http://127.0.0.1:${PORTA}`);
  log('');
  log('  Conecte quantos bancos quiser. Cada um vira uma linha no .env.');
  log('  Quando terminar, encerre com Ctrl+C e rode:  npm run diagnostico');
  log('');
  log('  Se ja conectou tudo em meu.pluggy.ai, o navegador e dispensavel:');
  log('    npm run conectar -- --listar');
  log('');
});
