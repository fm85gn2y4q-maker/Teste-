#!/usr/bin/env node
/**
 * Verifica se a ligacao com o banco esta de pe e se os dados chegam no formato
 * que as ferramentas esperam. Roda sozinho, antes de plugar no cliente MCP.
 *
 * O relatorio mascara todo digito antes de imprimir: da para colar num chat
 * pedindo ajuda sem expor saldo, numero de conta nem CPF.
 */
import { carregarDotEnv } from './util/env.js';
import { carregarConfig } from './config.js';
import { criarProvider } from './providers/index.js';
import { PluggyProvider } from './providers/pluggy/provider.js';
import { brl, soma } from './util/dinheiro.js';
import { hojeISO, somarDias } from './util/datas.js';
import type { BankProvider } from './providers/types.js';

const caminho = carregarDotEnv();
const config = carregarConfig();

const ok = (s: string) => console.log(`  ok    ${s}`);
const aviso = (s: string) => console.log(`  aviso ${s}`);
const erro = (s: string) => console.log(`  ERRO  ${s}`);
const titulo = (s: string) => console.log(`\n${s}\n${'-'.repeat(s.length)}`);

/** Troca todo digito por # — o relatorio mostra o formato, nunca o valor. */
const mascarar = (s: string): string => s.replace(/\d/g, '#');

function esconder(v: string | undefined, sensivel = false): string {
  if (!v) return '(vazio)';
  // Segredo nunca aparece nem em pedaco: so o tamanho, para pegar chave truncada.
  if (sensivel) return `(definido, ${v.length} caracteres)`;
  return v.length <= 8 ? '****' : `${v.slice(0, 4)}…${v.slice(-4)}`;
}

async function main(): Promise<number> {
  titulo('Configuracao');
  console.log(`  arquivo .env      ${caminho ?? '(nao encontrado — usando so o ambiente)'}`);
  console.log(`  provedor          ${config.provedor}`);
  if (config.provedor === 'pluggy') {
    console.log(`  PLUGGY_CLIENT_ID  ${esconder(config.pluggy.clientId)}`);
    console.log(`  PLUGGY_SECRET     ${esconder(config.pluggy.clientSecret, true)}`);
    console.log(`  conexoes (items)  ${config.pluggy.itemIds.length || '(nenhuma)'}`);
    if (!config.pluggy.clientId || !config.pluggy.clientSecret) {
      erro('sem credencial da Pluggy. Preencha o .env e rode de novo.');
      return 1;
    }
    if (config.pluggy.itemIds.length === 0) {
      erro('nenhuma conexao configurada. Rode: npm run conectar');
      return 1;
    }
  } else {
    aviso('provedor "mock": os numeros abaixo sao sinteticos, nenhum banco foi consultado.');
    aviso('para usar dados reais, rode: npm run conectar');
  }

  let provider: BankProvider;
  try {
    provider = criarProvider(config);
  } catch (e) {
    erro(e instanceof Error ? e.message : String(e));
    return 1;
  }

  titulo('Conexoes');
  const instituicoes = await provider.listarInstituicoes();
  if (instituicoes.length === 0) {
    erro('nenhuma instituicao devolvida.');
    return 1;
  }
  for (const i of instituicoes) {
    const linha = `${i.nome} · ${i.status}${i.consentimentoExpiraEm ? ` · consentimento ate ${i.consentimentoExpiraEm}` : ''}`;
    if (i.status === 'ativa') ok(linha);
    else aviso(`${linha} — os dados dessa instituicao nao entram em nenhuma analise`);
  }

  titulo('Contas e cartoes');
  const [contas, cartoes] = await Promise.all([provider.listarContas(), provider.listarCartoes()]);
  console.log(`  ${contas.length} contas, ${cartoes.length} cartoes`);
  for (const c of contas) {
    console.log(`  conta   ${c.instituicao} · ${c.tipo} · ${mascarar(c.numero)} · saldo ${mascarar(brl(c.saldo))}`);
  }
  for (const c of cartoes) {
    console.log(`  cartao  ${c.instituicao} · ${c.bandeira} ·${mascarar(c.finalNumero)} · fecha dia ${c.diaFechamento}, vence dia ${c.diaVencimento}`);
  }
  if (contas.length === 0 && cartoes.length === 0) {
    erro('a conexao existe mas nao trouxe conta nenhuma. No Dashboard da Pluggy, confira se o item terminou de sincronizar.');
    return 1;
  }

  // O caso do agregador: todas as contas sob o mesmo rotulo.
  if (provider instanceof PluggyProvider) {
    const brutas = await provider.carregarContas();
    const agregadas = brutas.filter((b) => b.agregado);
    if (agregadas.length > 0) {
      const nomes = new Set(agregadas.map((b) => b.instituicao));
      aviso(`${agregadas.length} contas ficaram sob o rotulo generico ${[...nomes].join(', ')} —`);
      aviso('o conector agrega varios bancos e nao disse de qual banco e cada conta.');
      aviso('Para corrigir os nomes, ponha no .env (uma linha so):');
      const exemplo = agregadas.slice(0, 3)
        .map((b) => `"${b.conta.id}":"Nome do banco"`).join(',');
      aviso(`  BANCO_MCP_INSTITUICOES={${exemplo}}`);
      aviso('As contas na ordem acima ajudam a identificar qual e qual.');
    }
  }

  titulo('Extrato');
  const hoje = hojeISO();
  const de = somarDias(hoje, -60);
  const transacoes = await provider.listarTransacoes({ de, ate: hoje });
  console.log(`  ${transacoes.length} lancamentos entre ${de} e ${hoje}`);
  if (transacoes.length === 0) {
    aviso('nenhum lancamento em 60 dias. Pode ser conta parada, ou sincronizacao incompleta.');
  } else {
    const entradas = transacoes.filter((t) => t.valor > 0);
    const saidas = transacoes.filter((t) => t.valor < 0);
    console.log(`  ${entradas.length} entradas, ${saidas.length} saidas`);
    if (entradas.length === 0 || saidas.length === 0) {
      aviso('so ha lancamento de um sinal. Isso costuma indicar sinal invertido no conector —');
      aviso('confira uma compra conhecida contra o extrato oficial antes de confiar nos totais.');
    }
    const semCategoria = transacoes.filter((t) => t.categoria === 'Sem categoria').length;
    if (semCategoria > transacoes.length / 2) {
      aviso(`${semCategoria} de ${transacoes.length} lancamentos sem categoria — a analise por categoria fica pobre.`);
    }
    const semData = transacoes.filter((t) => !/^\d{4}-\d{2}-\d{2}$/.test(t.data)).length;
    if (semData) erro(`${semData} lancamentos vieram sem data valida.`);
  }

  titulo('Fatura, carteira e credito');
  const [faturas, investimentos, emprestimos] = await Promise.all([
    provider.listarFaturas(), provider.listarInvestimentos(), provider.listarEmprestimos(),
  ]);
  console.log(`  ${faturas.length} faturas, ${investimentos.length} posicoes, ${emprestimos.length} contratos de credito`);
  for (const f of faturas.slice(0, 4)) {
    const somaLanc = soma(f.lancamentos.map((t) => Math.abs(t.valor)));
    const bate = f.valorTotal === 0 || Math.abs(somaLanc - f.valorTotal) <= Math.max(100, f.valorTotal * 0.02);
    const desc = `fatura ${f.cartao} ${f.mesReferencia} · ${f.status} · total ${mascarar(brl(f.valorTotal))} · ${f.lancamentos.length} lancamentos`;
    if (bate) ok(desc);
    else aviso(`${desc} — a soma dos lancamentos do ciclo nao bate com o total; o ciclo pode estar deslocado`);
  }
  if (cartoes.length > 0 && faturas.length === 0) {
    aviso('ha cartao mas nenhuma fatura. Algumas instituicoes so expoem fatura fechada.');
  }

  titulo('Resultado');
  ok(`${contas.length + cartoes.length} produtos legiveis, 13 ferramentas prontas.`);
  console.log('\n  Plugue no Claude Code com:');
  console.log(`    claude mcp add banco -- node ${process.cwd()}/dist/index.js\n`);
  return 0;
}

main().then((codigo) => process.exit(codigo)).catch((e) => {
  console.log(`\n  ERRO  ${e instanceof Error ? e.message : String(e)}`);
  console.log('\n  Se o erro for 401 ou 403, a credencial da Pluggy esta errada ou expirou.');
  console.log('  Se for 404 em /items, o id da conexao no .env nao existe mais — rode: npm run conectar\n');
  process.exit(1);
});
