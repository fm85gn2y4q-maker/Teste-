import { z } from 'zod';
import { brl, soma } from '../util/dinheiro.js';
import { formatarDia, mesPorExtenso, resolverPeriodo, somarDias, mesDe } from '../util/datas.js';
import { lista, procedencia, resultado, statusConsentimento, tabela, titulo } from '../formato.js';
import { projetarFluxo } from '../analise/fluxo.js';
import { detectarRecorrentes, porCategoria } from '../analise/gastos.js';
import { levantarGastos, levantarPatrimonio } from '../analise/consolidado.js';
import { LEITURA, protegido, texto, type Registrador } from './base.js';

export const registrarPlanejamento: Registrador = (server, ctx) => {
  server.registerTool(
    'fluxo_de_caixa',
    {
      title: 'Projetar fluxo de caixa',
      description:
        'Projeta o saldo para os proximos dias a partir do que ja esta contratado (agendamentos, parcelas, ' +
        'faturas a vencer) somado ao ritmo medio de entradas e saidas dos ultimos meses fechados. Use para ' +
        '"o dinheiro chega ate o fim do mes?" e para planejar uma compra grande.',
      inputSchema: {
        dias: z.number().int().min(7).max(180).optional().describe('Horizonte da projecao. Padrao: 30.'),
      },
      annotations: LEITURA,
    },
    protegido(async ({ dias }: { dias?: number }) => {
      const horizonte = dias ?? 30;
      const hoje = ctx.hoje();
      const inicioHistorico = somarDias(hoje, -365);

      const [contas, transacoes, agendamentos, cartoes, faturas] = await Promise.all([
        ctx.provider.listarContas(),
        ctx.provider.listarTransacoes({ de: inicioHistorico, ate: hoje }),
        ctx.provider.listarAgendamentos(),
        ctx.provider.listarCartoes(),
        ctx.provider.listarFaturas(),
      ]);

      const limite = somarDias(hoje, horizonte);

      // Fatura a vencer e compromisso conhecido, ainda que o banco nao a agende.
      const faturasAVencer = faturas.filter(
        (f) => (f.status === 'aberta' || f.status === 'fechada') && f.dataVencimento >= hoje && f.dataVencimento <= limite,
      );
      const compromissosFatura = faturasAVencer.map((f) => ({
        id: `fat-${f.id}`,
        instituicaoId: '',
        instituicao: f.instituicao,
        descricao: `Fatura ${f.cartao} (${mesPorExtenso(f.mesReferencia)})`,
        valor: -f.valorTotal,
        data: f.dataVencimento,
        categoria: 'Cartao',
        recorrente: true,
        frequencia: 'mensal' as const,
      }));

      const projecao = projetarFluxo(
        contas,
        transacoes,
        [...agendamentos.filter((a) => a.valor !== 0), ...compromissosFatura],
        hoje,
        horizonte,
      );

      const linhas = projecao.compromissos.map((c) => [formatarDia(c.data), c.descricao, brl(c.valor)]);

      const alertas: string[] = [];
      if (projecao.saldoProjetado < 0) {
        alertas.push(
          `A projecao fecha negativa em ${brl(-projecao.saldoProjetado)}. Isso significa cheque especial ou ` +
          `atraso de parcela dentro do horizonte.`,
        );
      }
      const saldoAposCompromissos = projecao.saldoAtual + projecao.compromissosConhecidos;
      if (saldoAposCompromissos < 0) {
        alertas.push(
          `So os compromissos ja contratados (${brl(-projecao.compromissosConhecidos)}) superam o saldo em ` +
          `conta (${brl(projecao.saldoAtual)}) — sem contar gasto novo nenhum.`,
        );
      }
      if (cartoes.some((c) => c.limiteTotal > 0 && c.limiteDisponivel / c.limiteTotal < 0.15)) {
        alertas.push('Ha cartao com menos de 15% do limite livre; ele nao serve de folga nesse horizonte.');
      }

      const md = [
        titulo(`Fluxo de caixa — proximos ${horizonte} dias`),
        lista([
          `Saldo em conta hoje: **${brl(projecao.saldoAtual)}**`,
          `Compromissos ja conhecidos no periodo: **${brl(projecao.compromissosConhecidos)}**`,
          `Ritmo dos ultimos meses fechados: entradas ${brl(projecao.entradaMediaMensal)}/mes, saidas ${brl(projecao.gastoMedioMensal)}/mes`,
          `Saldo projetado em ${formatarDia(limite)}: **${brl(projecao.saldoProjetado)}**`,
          projecao.mesesDeFolga !== null
            ? `Se a renda parasse hoje, o saldo em conta cobriria ${projecao.mesesDeFolga} meses no ritmo atual de gastos.`
            : '',
        ].filter(Boolean)),
        linhas.length
          ? `${titulo('Compromissos no periodo', 3)}\n${tabela(['Data', 'Compromisso', 'Valor'], linhas, ['esq', 'esq', 'dir'])}`
          : '_Nenhum compromisso agendado no periodo._',
        alertas.length ? `${titulo('Atencao', 3)}\n${lista(alertas)}` : '',
        `\n_Projecao, nao promessa: parte de agendamentos informados pelos bancos e da media dos ultimos ` +
        `meses fechados. Gasto novo nao entra nessa conta._`,
        procedencia(ctx.provider.origem),
      ].filter(Boolean).join('\n\n');

      return texto(md);
    }),
  );

  server.registerTool(
    'listar_agendamentos',
    {
      title: 'Listar agendamentos e recorrencias',
      description:
        'Pagamentos agendados e debitos automaticos informados pelos bancos, mais as recorrencias detectadas ' +
        'no proprio extrato (assinaturas, mensalidades). Use para achar cobranca esquecida e para dimensionar ' +
        'o custo fixo mensal.',
      inputSchema: {
        dias: z.number().int().min(7).max(365).optional().describe('Janela de agendamentos futuros. Padrao: 60.'),
        detectarRecorrencias: z.boolean().optional()
          .describe('Procura cobranca repetida no extrato dos ultimos 12 meses. Padrao: true.'),
      },
      annotations: LEITURA,
    },
    protegido(async ({ dias, detectarRecorrencias }: { dias?: number; detectarRecorrencias?: boolean }) => {
      const janela = dias ?? 60;
      const hoje = ctx.hoje();
      const limite = somarDias(hoje, janela);

      const agendamentos = (await ctx.provider.listarAgendamentos())
        .filter((a) => a.data >= hoje && a.data <= limite)
        .sort((a, b) => a.data.localeCompare(b.data));

      const linhas = agendamentos.map((a) => [
        formatarDia(a.data),
        a.descricao,
        a.instituicao,
        a.categoria,
        a.valor === 0 ? 'valor da fatura' : brl(a.valor),
        a.recorrente ? (a.frequencia ?? 'recorrente') : 'unico',
      ]);

      const partes = [
        titulo(`Agendamentos nos proximos ${janela} dias`),
        agendamentos.length
          ? tabela(['Data', 'Descricao', 'Instituicao', 'Categoria', 'Valor', 'Frequencia'], linhas,
              ['esq', 'esq', 'esq', 'esq', 'dir', 'esq'])
          : '_Nenhum agendamento informado pelos bancos nessa janela._',
      ];

      if (detectarRecorrencias ?? true) {
        const transacoes = await ctx.provider.listarTransacoes({ de: somarDias(hoje, -365), ate: hoje });
        const faturas = await ctx.provider.listarFaturas();
        const comCartao = [...transacoes, ...faturas.flatMap((f) => f.lancamentos)];
        const recorrentes = detectarRecorrentes(comCartao);

        if (recorrentes.length) {
          const linhasRec = recorrentes.slice(0, 25).map((r) => [
            r.descricao,
            r.categoria,
            brl(r.valorTipico),
            String(r.ocorrencias),
            `~${r.intervaloDias}d`,
            formatarDia(r.ultimaData),
          ]);
          const totalMensal = soma(recorrentes.map((r) => r.valorTipico));
          const paradas = recorrentes.filter((r) => r.ultimaData < somarDias(hoje, -45));

          partes.push(
            titulo('Recorrencias detectadas no extrato', 3),
            tabela(['Cobranca', 'Categoria', 'Valor tipico', 'Vezes', 'Intervalo', 'Ultima'], linhasRec,
              ['esq', 'esq', 'dir', 'centro', 'centro', 'esq']),
            `Custo fixo recorrente estimado: **${brl(totalMensal)} por mes**.`,
            paradas.length
              ? `${titulo('Sem cobranca ha mais de 45 dias', 4)}\n` +
                lista(paradas.map((r) => `${r.descricao} — ultima em ${formatarDia(r.ultimaData)}. Pode ter sido cancelada, ou so nao caiu ainda.`))
              : '',
            `\n_Recorrencia aqui e inferencia por repeticao (tres ou mais cobrancas, intervalo perto de um mes, ` +
            `valor estavel), nao um cadastro do banco. Parcelamento de compra grande pode aparecer como recorrencia._`,
          );
        }
      }

      partes.push(procedencia(ctx.provider.origem));
      return texto(partes.filter(Boolean).join('\n\n'));
    }),
  );

  server.registerTool(
    'panorama_financeiro',
    {
      title: 'Panorama financeiro consolidado',
      description:
        'Visao geral de tudo em uma resposta: patrimonio liquido, saldos, carteira, dividas, fatura em aberto, ' +
        'resultado do mes e principais alertas. E a ferramenta certa para perguntas amplas como "como estao ' +
        'minhas financas" — evita cinco consultas separadas.',
      inputSchema: {
        mes: z.string().regex(/^\d{4}-\d{2}$/).optional().describe('Mes de referencia YYYY-MM. Padrao: mes corrente.'),
      },
      annotations: LEITURA,
    },
    protegido(async ({ mes }: { mes?: string }) => {
      const hoje = ctx.hoje();
      const periodo = resolverPeriodo(mes ? { mes } : { periodo: 'mes_atual' }, hoje);

      const [patrimonio, instituicoes, gastos, cartoes, faturas, emprestimos] = await Promise.all([
        levantarPatrimonio(ctx.provider),
        ctx.provider.listarInstituicoes(),
        levantarGastos(ctx.provider, periodo),
        ctx.provider.listarCartoes(),
        ctx.provider.listarFaturas(),
        ctx.provider.listarEmprestimos(),
      ]);

      const emAberto = faturas.filter((f) => f.status === 'aberta' || f.status === 'fechada' || f.status === 'atrasada');
      const parcelaMensal = soma(emprestimos.map((e) => e.valorParcela));
      const topCategorias = porCategoria(gastos.saidas).slice(0, 5);

      const composicao = tabela(
        ['Componente', 'Valor'],
        [
          ['Saldo em conta', brl(patrimonio.emConta)],
          ['Investimentos', brl(patrimonio.investido)],
          ['Faturas em aberto', brl(-patrimonio.faturasEmAberto)],
          ['Emprestimos e financiamentos', brl(-patrimonio.dividas)],
          ['**Patrimonio liquido**', `**${brl(patrimonio.liquido)}**`],
        ],
        ['esq', 'dir'],
      );

      const alertas: string[] = [];
      const inativas = instituicoes.filter((i) => i.status !== 'ativa');
      if (inativas.length) {
        alertas.push(
          `${inativas.map((i) => i.nome).join(', ')} ${inativas.length > 1 ? 'estao fora' : 'esta fora'} deste ` +
          `panorama: consentimento ${statusConsentimento(inativas[0]!.status)}. Os numeros acima nao incluem esses bancos.`,
        );
      }
      if (patrimonio.dividas > 0 && patrimonio.investido > 0) {
        const jurosCaros = emprestimos.filter((e) => e.taxaJurosMensal >= 1.5);
        if (jurosCaros.length) {
          alertas.push(
            `Ha divida a ${jurosCaros.map((e) => `${e.taxaJurosMensal.toFixed(2)}% a.m.`).join(' e ')} convivendo com ` +
            `${brl(patrimonio.investido)} investidos. Vale comparar essa taxa com o que a carteira rende antes de ` +
            `decidir entre aportar e amortizar.`,
          );
        }
      }
      if (gastos.totalSaidas > gastos.totalEntradas && periodo.de.slice(0, 7) !== mesDe(hoje)) {
        alertas.push(`Em ${periodo.rotulo} as saidas superaram as entradas em ${brl(gastos.totalSaidas - gastos.totalEntradas)}.`);
      }
      const semLimite = cartoes.filter((c) => c.limiteTotal > 0 && c.limiteDisponivel / c.limiteTotal < 0.15);
      if (semLimite.length) {
        alertas.push(`${semLimite.map((c) => c.apelido).join(', ')} com menos de 15% do limite disponivel.`);
      }

      const md = [
        titulo(`Panorama financeiro — ${periodo.rotulo}`),
        `Patrimonio liquido: **${brl(patrimonio.liquido)}**`,
        composicao,
        titulo('O mes', 3),
        lista([
          `Entradas: ${brl(gastos.totalEntradas)}`,
          `Saidas (conta + cartao, sem contar duas vezes): ${brl(gastos.totalSaidas)}`,
          `Resultado: **${resultado(gastos.totalEntradas - gastos.totalSaidas)}**`,
          `Compromisso fixo com parcelas de emprestimo: ${brl(parcelaMensal)}/mes`,
          emAberto.length
            ? `Faturas a pagar: ${emAberto.map((f) => `${f.cartao} ${brl(f.valorTotal)} (vence ${formatarDia(f.dataVencimento)})`).join('; ')}`
            : 'Nenhuma fatura em aberto.',
        ]),
        topCategorias.length
          ? `${titulo('Para onde foi o dinheiro', 3)}\n${tabela(
              ['Categoria', 'Total', '%'],
              topCategorias.map((g) => [g.chave, brl(g.total), `${g.percentual.toFixed(0)}%`]),
              ['esq', 'dir', 'dir'],
            )}`
          : '',
        alertas.length ? `${titulo('Pontos de atencao', 3)}\n${lista(alertas)}` : '',
        `\n_Consolidado de ${instituicoes.filter((i) => i.status === 'ativa').length} instituicoes conectadas. ` +
        `Nao inclui bens fora do sistema financeiro (imovel, veiculo) nem contas em bancos nao conectados._`,
        procedencia(ctx.provider.origem),
      ].filter(Boolean).join('\n\n');

      return texto(md);
    }),
  );
};
