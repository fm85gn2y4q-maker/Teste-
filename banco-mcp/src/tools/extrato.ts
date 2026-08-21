import { z } from 'zod';
import { brl, paraCentavos, pct, soma } from '../util/dinheiro.js';
import {
  formatarDia, mesPorExtenso, periodoAnterior, resolverPeriodo,
} from '../util/datas.js';
import { barra, lista, procedencia, resultado, tabela, titulo } from '../formato.js';
import { fluxoMensal } from '../analise/fluxo.js';
import { compararCategorias, porCategoria, porEstabelecimento, porInstituicao, porMetodo } from '../analise/gastos.js';
import { levantarGastos } from '../analise/consolidado.js';
import { LEITURA, protegido, texto, type Registrador } from './base.js';

const PERIODOS = [
  'mes_atual', 'mes_passado', 'ultimos_30_dias', 'ultimos_90_dias', 'ano_atual', 'ultimos_12_meses',
] as const;

interface ArgsPeriodo {
  periodo?: (typeof PERIODOS)[number];
  mes?: string;
  de?: string;
  ate?: string;
}

interface ArgsTransacoes extends ArgsPeriodo {
  contaId?: string;
  instituicaoId?: string;
  categoria?: string;
  texto?: string;
  valorMinimo?: number;
  valorMaximo?: number;
  apenas?: 'entradas' | 'saidas';
  limite?: number;
}

interface ArgsResumo extends ArgsPeriodo {
  instituicaoId?: string;
}

interface ArgsGastos extends ArgsPeriodo {
  agruparPor?: 'categoria' | 'estabelecimento' | 'instituicao' | 'metodo';
  comparar?: boolean;
  incluirCartao?: boolean;
  incluirAplicacoes?: boolean;
  instituicaoId?: string;
  limite?: number;
}

const argsPeriodo = {
  periodo: z.enum(PERIODOS).optional().describe('Atalho de periodo. Padrao: mes_atual.'),
  mes: z.string().regex(/^\d{4}-\d{2}$/).optional().describe('Mes especifico no formato YYYY-MM.'),
  de: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional().describe('Data inicial YYYY-MM-DD.'),
  ate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional().describe('Data final YYYY-MM-DD.'),
};

export const registrarExtrato: Registrador = (server, ctx) => {
  server.registerTool(
    'listar_transacoes',
    {
      title: 'Listar transacoes do extrato',
      description:
        'Extrato detalhado das contas, com filtro por periodo, conta, instituicao, categoria, valor e busca ' +
        'livre no texto do lancamento. Use para responder "quanto paguei em X", "quando caiu Y" ou para ' +
        'conferir um lancamento especifico. Nao inclui compras de cartao de credito — para elas use consultar_fatura.',
      inputSchema: {
        ...argsPeriodo,
        contaId: z.string().optional().describe('Restringe a uma conta (veja listar_contas).'),
        instituicaoId: z.string().optional().describe('Restringe a uma instituicao.'),
        categoria: z.string().optional().describe('Categoria exata, ex.: "Moradia".'),
        texto: z.string().optional().describe('Busca livre na descricao e no beneficiario, sem acento e sem caixa.'),
        valorMinimo: z.number().optional().describe('Valor minimo em reais (modulo).'),
        valorMaximo: z.number().optional().describe('Valor maximo em reais (modulo).'),
        apenas: z.enum(['entradas', 'saidas']).optional().describe('Filtra so entradas ou so saidas.'),
        limite: z.number().int().min(1).max(300).optional().describe('Maximo de linhas exibidas. Padrao: 60.'),
      },
      annotations: LEITURA,
    },
    protegido(async (a: ArgsTransacoes) => {
      const periodo = resolverPeriodo(a, ctx.hoje());
      const limite = a.limite ?? 60;

      const transacoes = await ctx.provider.listarTransacoes({
        de: periodo.de,
        ate: periodo.ate,
        ...(a.contaId ? { contaId: a.contaId } : {}),
        ...(a.instituicaoId ? { instituicaoId: a.instituicaoId } : {}),
        ...(a.categoria ? { categoria: a.categoria } : {}),
        ...(a.texto ? { texto: a.texto } : {}),
        ...(a.apenas ? { apenas: a.apenas } : {}),
        ...(a.valorMinimo !== undefined ? { valorMinimo: paraCentavos(a.valorMinimo) } : {}),
        ...(a.valorMaximo !== undefined ? { valorMaximo: paraCentavos(a.valorMaximo) } : {}),
      });

      if (transacoes.length === 0) {
        return texto(
          `Nenhum lancamento em ${periodo.rotulo} com esse filtro.\n\n` +
          `Se esperava encontrar algo: compras no cartao de credito nao aparecem no extrato da conta — ` +
          `elas estao na fatura (\`consultar_fatura\`). Bancos com consentimento expirado tambem ficam ` +
          `de fora (\`listar_conexoes\`).` +
          procedencia(ctx.provider.origem),
        );
      }

      const entradas = soma(transacoes.filter((t) => t.valor > 0).map((t) => t.valor));
      const saidas = soma(transacoes.filter((t) => t.valor < 0).map((t) => -t.valor));

      const exibidas = [...transacoes].reverse().slice(0, limite);
      const linhas = exibidas.map((t) => [
        formatarDia(t.data),
        t.descricao.length > 42 ? `${t.descricao.slice(0, 41)}…` : t.descricao,
        t.categoria,
        t.metodo,
        brl(t.valor),
      ]);

      const md = [
        titulo(`Extrato — ${periodo.rotulo}`),
        `${transacoes.length} lancamentos · entradas ${brl(entradas)} · saidas ${brl(saidas)} · ${resultado(entradas - saidas)}`,
        tabela(['Data', 'Descricao', 'Categoria', 'Metodo', 'Valor'], linhas, ['esq', 'esq', 'esq', 'esq', 'dir']),
        transacoes.length > limite
          ? `\n_Mostrando os ${limite} mais recentes de ${transacoes.length}. Use \`limite\` ou estreite o periodo._`
          : '',
        procedencia(ctx.provider.origem),
      ].join('\n\n');

      return texto(md);
    }),
  );

  server.registerTool(
    'resumo_mensal',
    {
      title: 'Resumo mensal de entradas e saidas',
      description:
        'Entradas, saidas e resultado mes a mes, para ver a tendencia e identificar os meses fora da curva. ' +
        'Use para "como foi meu ano", "estou gastando mais que ganho?" ou antes de qualquer planejamento.',
      inputSchema: {
        ...argsPeriodo,
        instituicaoId: z.string().optional().describe('Restringe a uma instituicao.'),
      },
      annotations: LEITURA,
    },
    protegido(async (a: ArgsResumo) => {
      const periodo = resolverPeriodo({ ...a, periodo: a.periodo ?? (a.mes || a.de ? undefined : 'ultimos_12_meses') }, ctx.hoje());
      const transacoes = await ctx.provider.listarTransacoes({
        de: periodo.de,
        ate: periodo.ate,
        ...(a.instituicaoId ? { instituicaoId: a.instituicaoId } : {}),
      });

      // Fatura de cartao e transferencia interna distorcem o mes: o gasto ja
      // aparece na compra. Aqui o extrato e visto como caixa, entao o debito da
      // fatura fica, mas transferencia entre contas proprias sai (entra e sai no mesmo mes).
      const caixa = transacoes.filter((t) => t.categoria !== 'Transferencia');
      const meses = fluxoMensal(caixa, periodo.de, periodo.ate);

      const linhas = meses.map((m) => [
        mesPorExtenso(m.mes),
        brl(m.entradas),
        brl(m.saidas),
        brl(m.resultado),
        m.entradas === 0 ? '-' : `${((m.resultado / m.entradas) * 100).toFixed(0)}%`,
      ]);

      const positivos = meses.filter((m) => m.resultado > 0).length;
      const totalEntradas = soma(meses.map((m) => m.entradas));
      const totalSaidas = soma(meses.map((m) => m.saidas));
      const pior = [...meses].sort((x, y) => x.resultado - y.resultado)[0];
      const melhor = [...meses].sort((x, y) => y.resultado - x.resultado)[0];

      const md = [
        titulo(`Resumo mensal — ${periodo.rotulo}`),
        tabela(
          ['Mes', 'Entradas', 'Saidas', 'Resultado', 'Taxa de poupanca'],
          linhas,
          ['esq', 'dir', 'dir', 'dir', 'dir'],
        ),
        lista([
          `No agregado: entradas ${brl(totalEntradas)}, saidas ${brl(totalSaidas)}, ${resultado(totalEntradas - totalSaidas)}.`,
          `${positivos} de ${meses.length} meses fecharam no azul.`,
          melhor ? `Melhor mes: ${mesPorExtenso(melhor.mes)} (${brl(melhor.resultado)}).` : '',
          pior ? `Pior mes: ${mesPorExtenso(pior.mes)} (${brl(pior.resultado)}).` : '',
        ].filter(Boolean)),
        `\n_O mes corrente costuma aparecer incompleto: so contem o que ja foi lancado ate hoje._`,
        procedencia(ctx.provider.origem),
      ].join('\n\n');

      return texto(md);
    }),
  );

  server.registerTool(
    'analisar_gastos',
    {
      title: 'Analisar gastos por categoria',
      description:
        'Analise de gastos do periodo, agrupada por categoria, estabelecimento, instituicao ou meio de pagamento, ' +
        'com comparacao opcional contra o periodo anterior de mesmo tamanho. Junta conta e cartao sem contar duas ' +
        'vezes a mesma compra. Use para "com que eu gasto meu dinheiro" e "por que esse mes foi mais caro".',
      inputSchema: {
        ...argsPeriodo,
        agruparPor: z.enum(['categoria', 'estabelecimento', 'instituicao', 'metodo']).optional()
          .describe('Eixo da analise. Padrao: categoria.'),
        comparar: z.boolean().optional().describe('Compara com o periodo anterior de mesmo tamanho. Padrao: true.'),
        incluirCartao: z.boolean().optional().describe('Soma compras de cartao pela data da compra. Padrao: true.'),
        incluirAplicacoes: z.boolean().optional().describe('Conta aplicacao financeira como gasto. Padrao: false.'),
        instituicaoId: z.string().optional(),
        limite: z.number().int().min(3).max(50).optional().describe('Quantos grupos exibir. Padrao: 15.'),
      },
      annotations: LEITURA,
    },
    protegido(async (a: ArgsGastos) => {
      const periodo = resolverPeriodo(a, ctx.hoje());
      const agruparPor = a.agruparPor ?? 'categoria';
      const limite = a.limite ?? 15;
      const comparar = a.comparar ?? true;

      const opcoes = {
        incluirCartao: a.incluirCartao ?? true,
        incluirAplicacoes: a.incluirAplicacoes ?? false,
        ...(a.instituicaoId ? { instituicaoId: a.instituicaoId } : {}),
      };

      const atual = await levantarGastos(ctx.provider, periodo, opcoes);
      if (atual.saidas.length === 0) {
        return texto(`Nenhum gasto encontrado em ${periodo.rotulo}.` + procedencia(ctx.provider.origem));
      }

      const agrupador =
        agruparPor === 'estabelecimento' ? porEstabelecimento
        : agruparPor === 'instituicao' ? porInstituicao
        : agruparPor === 'metodo' ? porMetodo
        : porCategoria;

      const grupos = agrupador(atual.saidas).slice(0, limite);
      const linhas = grupos.map((g) => [
        g.chave,
        brl(g.total),
        `${g.percentual.toFixed(1)}%`,
        barra(g.percentual),
        String(g.quantidade),
      ]);

      const partes: string[] = [
        titulo(`Gastos em ${periodo.rotulo}: ${brl(atual.totalSaidas)}`),
        tabela(
          [agruparPor === 'metodo' ? 'Meio' : agruparPor.replace(/^./, (c) => c.toUpperCase()), 'Total', '%', '', 'Lancamentos'],
          linhas,
          ['esq', 'dir', 'dir', 'esq', 'dir'],
        ),
      ];

      if (comparar) {
        const anterior = periodoAnterior(periodo);
        const gastosAnteriores = await levantarGastos(ctx.provider, anterior, opcoes);
        const delta = atual.totalSaidas - gastosAnteriores.totalSaidas;
        const variacaoTotal = gastosAnteriores.totalSaidas === 0
          ? null
          : (delta / gastosAnteriores.totalSaidas) * 100;

        const comparacoes = compararCategorias(atual.saidas, gastosAnteriores.saidas)
          .filter((c) => Math.abs(c.delta) > 0)
          .slice(0, 8)
          .map((c) => [
            c.chave,
            brl(c.anterior),
            brl(c.atual),
            `${c.delta > 0 ? '+' : ''}${brl(c.delta)}`,
            c.variacaoPct === null ? 'novo' : pct(c.variacaoPct, 0),
          ]);

        partes.push(
          titulo(`Contra ${anterior.rotulo}`, 3),
          `Gasto total ${delta > 0 ? 'subiu' : 'caiu'} ${brl(Math.abs(delta))}` +
          `${variacaoTotal === null ? '' : ` (${pct(variacaoTotal, 0)})`}, ` +
          `de ${brl(gastosAnteriores.totalSaidas)} para ${brl(atual.totalSaidas)}.`,
          tabela(['Categoria', 'Antes', 'Agora', 'Diferenca', 'Variacao'], comparacoes, ['esq', 'dir', 'dir', 'dir', 'dir']),
        );
      }

      if (atual.notas.length) {
        partes.push(`${titulo('Como esse numero foi montado', 3)}\n${lista(atual.notas)}`);
      }
      partes.push(procedencia(ctx.provider.origem));

      return texto(partes.join('\n\n'));
    }),
  );
};
