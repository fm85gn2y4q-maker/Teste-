import { z } from 'zod';
import { brl, soma } from '../util/dinheiro.js';
import { diferencaEmDias, formatarDia } from '../util/datas.js';
import { lista, procedencia, statusConsentimento, tabela, titulo } from '../formato.js';
import { LEITURA, protegido, texto, type Registrador } from './base.js';

const TIPOS_CONTA = ['corrente', 'poupanca', 'pagamento', 'investimento'] as const;

export const registrarContas: Registrador = (server, ctx) => {
  server.registerTool(
    'listar_conexoes',
    {
      title: 'Listar bancos conectados',
      description:
        'Lista as instituicoes financeiras conectadas via Open Finance, com status do consentimento, ' +
        'escopos autorizados e data da ultima sincronizacao. Use antes de qualquer analise para saber ' +
        'quais bancos entram na conta e quais ficaram de fora por consentimento expirado.',
      inputSchema: {},
      annotations: LEITURA,
    },
    protegido(async () => {
      const instituicoes = await ctx.provider.listarInstituicoes();
      const hoje = ctx.hoje();

      const linhas = instituicoes.map((i) => {
        const diasRestantes = i.consentimentoExpiraEm
          ? diferencaEmDias(hoje, i.consentimentoExpiraEm)
          : null;
        const situacao =
          i.status === 'ativa'
            ? diasRestantes !== null && diasRestantes <= 30
              ? `ativa (expira em ${diasRestantes} dias)`
              : 'ativa'
            : i.status;
        return [
          i.nome,
          i.tipo,
          situacao,
          i.escopos.join(', '),
          i.ultimaSincronizacao ? i.ultimaSincronizacao.slice(0, 16).replace('T', ' ') : '-',
        ];
      });

      const inativas = instituicoes.filter((i) => i.status !== 'ativa');
      const expirando = instituicoes.filter(
        (i) => i.status === 'ativa' && i.consentimentoExpiraEm && diferencaEmDias(hoje, i.consentimentoExpiraEm) <= 30,
      );

      const avisos: string[] = [];
      for (const i of inativas) {
        avisos.push(
          `**${i.nome}**: consentimento ${statusConsentimento(i.status)}. Os dados desse banco NAO entram em nenhuma ` +
          `analise ate voce reautorizar a conexao.`,
        );
      }
      for (const i of expirando) {
        avisos.push(
          `**${i.nome}**: consentimento vence em ${formatarDia(i.consentimentoExpiraEm!)}. ` +
          `Consentimento de Open Finance dura no maximo 12 meses e precisa ser renovado.`,
        );
      }

      const md = [
        titulo(`${instituicoes.filter((i) => i.status === 'ativa').length} instituicoes ativas`),
        tabela(['Instituicao', 'Tipo', 'Consentimento', 'Escopos', 'Ultima sincronizacao'], linhas),
        avisos.length ? `\n${titulo('Atencao', 3)}\n${lista(avisos)}` : '',
        procedencia(ctx.provider.origem),
      ].join('\n\n');

      return texto(md);
    }),
  );

  server.registerTool(
    'listar_contas',
    {
      title: 'Listar contas',
      description:
        'Lista as contas de todas as instituicoes conectadas (corrente, poupanca, pagamento e investimento) ' +
        'com saldo, saldo disponivel e limite de cheque especial. Use quando precisar do identificador de uma ' +
        'conta para filtrar extrato, ou para ver onde o dinheiro esta distribuido.',
      inputSchema: {
        instituicaoId: z.string().optional().describe('Filtra por instituicao, ex.: "itau".'),
        tipo: z.enum(TIPOS_CONTA).optional().describe('Filtra por tipo de conta.'),
      },
      annotations: LEITURA,
    },
    protegido(async ({ instituicaoId, tipo }: { instituicaoId?: string; tipo?: (typeof TIPOS_CONTA)[number] }) => {
      const todas = await ctx.provider.listarContas();
      const contas = todas.filter(
        (c) => (!instituicaoId || c.instituicaoId === instituicaoId) && (!tipo || c.tipo === tipo),
      );

      if (contas.length === 0) {
        return texto(
          `Nenhuma conta encontrada com esse filtro. Contas disponiveis: ` +
          `${todas.map((c) => `${c.id} (${c.instituicao})`).join(', ') || 'nenhuma'}.`,
        );
      }

      const linhas = contas.map((c) => [
        `\`${c.id}\``,
        c.instituicao,
        c.apelido ?? c.tipo,
        c.tipo,
        c.numero,
        brl(c.saldo),
        c.limiteChequeEspecial ? brl(c.limiteChequeEspecial) : '-',
      ]);

      const md = [
        titulo(`${contas.length} contas`),
        tabela(
          ['ID', 'Instituicao', 'Apelido', 'Tipo', 'Numero', 'Saldo', 'Cheque especial'],
          linhas,
          ['esq', 'esq', 'esq', 'esq', 'esq', 'dir', 'dir'],
        ),
        `\nSaldo somado: **${brl(soma(contas.map((c) => c.saldo)))}**`,
        procedencia(ctx.provider.origem, contas[0]?.atualizadoEm.slice(0, 16).replace('T', ' ')),
      ].join('\n\n');

      return texto(md);
    }),
  );

  server.registerTool(
    'consultar_saldos',
    {
      title: 'Consultar saldos consolidados',
      description:
        'Soma o saldo de todas as contas conectadas, agrupado por instituicao, e aponta contas negativas ou ' +
        'em uso de cheque especial. Responde direto a pergunta "quanto eu tenho hoje?".',
      inputSchema: {
        instituicaoId: z.string().optional().describe('Restringe a uma instituicao.'),
      },
      annotations: LEITURA,
    },
    protegido(async ({ instituicaoId }: { instituicaoId?: string }) => {
      const contas = (await ctx.provider.listarContas()).filter(
        (c) => !instituicaoId || c.instituicaoId === instituicaoId,
      );
      const total = soma(contas.map((c) => c.saldo));

      const porInst = new Map<string, number>();
      for (const c of contas) {
        porInst.set(c.instituicao, (porInst.get(c.instituicao) ?? 0) + c.saldo);
      }

      const linhas = [...porInst.entries()]
        .sort((a, b) => b[1] - a[1])
        .map(([nome, v]) => [nome, brl(v), total === 0 ? '-' : `${((v / total) * 100).toFixed(1)}%`]);

      const negativas = contas.filter((c) => c.saldo < 0);
      const alertas = negativas.map(
        (c) =>
          `Conta ${c.apelido ?? c.id} (${c.instituicao}) esta negativa em ${brl(-c.saldo)} — ` +
          `isso e cheque especial, a linha de credito mais cara do banco.`,
      );

      const md = [
        titulo(`Saldo consolidado: ${brl(total)}`),
        tabela(['Instituicao', 'Saldo', 'Participacao'], linhas, ['esq', 'dir', 'dir']),
        alertas.length ? `\n${titulo('Atencao', 3)}\n${lista(alertas)}` : '',
        `\n_Consolidado de ${contas.length} contas em ${porInst.size} instituicoes. ` +
        `Nao inclui investimentos nem fatura de cartao — para o quadro completo use \`panorama_financeiro\`._`,
        procedencia(ctx.provider.origem, contas[0]?.atualizadoEm.slice(0, 16).replace('T', ' ')),
      ].join('\n\n');

      return texto(md);
    }),
  );
};
