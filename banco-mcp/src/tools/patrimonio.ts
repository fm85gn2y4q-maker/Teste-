import { z } from 'zod';
import { brl, pct, soma, variacao } from '../util/dinheiro.js';
import { formatarDia } from '../util/datas.js';
import { barra, lista, procedencia, tabela, titulo } from '../formato.js';
import { LEITURA, protegido, texto, type Registrador } from './base.js';
import type { Investimento } from '../providers/types.js';

const ROTULO_TIPO: Record<Investimento['tipo'], string> = {
  tesouro_direto: 'Tesouro Direto',
  cdb: 'CDB',
  lci_lca: 'LCI/LCA',
  fundo: 'Fundos',
  acao: 'Acoes',
  fii: 'Fundos imobiliarios',
  previdencia: 'Previdencia',
  cripto: 'Cripto',
  poupanca: 'Poupanca',
};

const RENDA_FIXA: Array<Investimento['tipo']> = ['tesouro_direto', 'cdb', 'lci_lca', 'poupanca'];

export const registrarPatrimonio: Registrador = (server, ctx) => {
  server.registerTool(
    'carteira_investimentos',
    {
      title: 'Consultar carteira de investimentos',
      description:
        'Carteira consolidada das corretoras e bancos conectados: posicao por ativo e por classe, valor aplicado ' +
        'contra valor atual, rentabilidade e liquidez. Use para "como esta minha carteira", "quanto rendeu" e ' +
        'para checar concentracao antes de decidir aporte.',
      inputSchema: {
        instituicaoId: z.string().optional().describe('Restringe a uma instituicao.'),
        tipo: z.enum(['tesouro_direto', 'cdb', 'lci_lca', 'fundo', 'acao', 'fii', 'previdencia', 'cripto', 'poupanca'])
          .optional().describe('Restringe a uma classe de ativo.'),
        detalhar: z.boolean().optional().describe('Lista ativo por ativo alem do resumo por classe. Padrao: true.'),
      },
      annotations: LEITURA,
    },
    protegido(async ({ instituicaoId, tipo, detalhar }: { instituicaoId?: string; tipo?: Investimento['tipo']; detalhar?: boolean }) => {
      const carteira = (await ctx.provider.listarInvestimentos()).filter(
        (i) => (!instituicaoId || i.instituicaoId === instituicaoId) && (!tipo || i.tipo === tipo),
      );
      if (carteira.length === 0) {
        return texto('Nenhum investimento nas conexoes ativas.' + procedencia(ctx.provider.origem));
      }

      const aplicado = soma(carteira.map((i) => i.valorAplicado));
      const atual = soma(carteira.map((i) => i.valorAtual));
      const rendimento = atual - aplicado;

      const porTipo = new Map<Investimento['tipo'], { aplicado: number; atual: number; n: number }>();
      for (const i of carteira) {
        const acc = porTipo.get(i.tipo) ?? { aplicado: 0, atual: 0, n: 0 };
        acc.aplicado += i.valorAplicado;
        acc.atual += i.valorAtual;
        acc.n += 1;
        porTipo.set(i.tipo, acc);
      }

      const linhasClasse = [...porTipo.entries()]
        .sort((a, b) => b[1].atual - a[1].atual)
        .map(([t, v]) => {
          const part = atual === 0 ? 0 : (v.atual / atual) * 100;
          const rent = variacao(v.aplicado, v.atual);
          return [
            ROTULO_TIPO[t],
            brl(v.atual),
            `${part.toFixed(1)}%`,
            barra(part, 10),
            rent === null ? '-' : pct(rent),
          ];
        });

      const partes: string[] = [
        titulo(`Carteira: ${brl(atual)}`),
        lista([
          `Aplicado: ${brl(aplicado)}`,
          `Resultado: **${brl(rendimento)}**${variacao(aplicado, atual) === null ? '' : ` (${pct(variacao(aplicado, atual)!)})`}`,
          `${carteira.length} posicoes em ${new Set(carteira.map((i) => i.instituicao)).size} instituicoes`,
        ]),
        titulo('Por classe', 3),
        tabela(['Classe', 'Valor atual', '%', '', 'Rentabilidade'], linhasClasse, ['esq', 'dir', 'dir', 'esq', 'dir']),
      ];

      if (detalhar ?? true) {
        const linhas = [...carteira]
          .sort((a, b) => b.valorAtual - a.valorAtual)
          .map((i) => {
            const rent = variacao(i.valorAplicado, i.valorAtual);
            return [
              i.nome,
              i.instituicao,
              i.quantidade ? String(i.quantidade) : '-',
              brl(i.valorAplicado),
              brl(i.valorAtual),
              rent === null ? '-' : pct(rent),
              i.liquidez.replace(/_/g, ' '),
            ];
          });
        partes.push(
          titulo('Posicoes', 3),
          tabela(['Ativo', 'Instituicao', 'Qtd', 'Aplicado', 'Atual', 'Rent.', 'Liquidez'], linhas,
            ['esq', 'esq', 'dir', 'dir', 'dir', 'dir', 'esq']),
        );
      }

      const rf = soma(carteira.filter((i) => RENDA_FIXA.includes(i.tipo)).map((i) => i.valorAtual));
      const liquidoAgora = soma(carteira.filter((i) => i.liquidez === 'diaria').map((i) => i.valorAtual));
      const maior = [...carteira].sort((a, b) => b.valorAtual - a.valorAtual)[0]!;
      const concentracao = atual === 0 ? 0 : (maior.valorAtual / atual) * 100;

      const observacoes = [
        `Renda fixa e poupanca: ${brl(rf)} (${atual === 0 ? 0 : ((rf / atual) * 100).toFixed(0)}% da carteira).`,
        `Resgatavel no mesmo dia: ${brl(liquidoAgora)}.`,
        concentracao > 25
          ? `Maior posicao (${maior.nome}) concentra ${concentracao.toFixed(0)}% da carteira.`
          : `Nenhuma posicao passa de 25% da carteira.`,
      ];
      partes.push(`${titulo('Leitura da carteira', 3)}\n${lista(observacoes)}`);
      partes.push(
        `\n_Rentabilidade aqui e valor atual contra valor aplicado, sem descontar imposto de renda, ` +
        `IOF nem come-cotas, e sem comparar com CDI. Nao e recomendacao de investimento._`,
      );
      partes.push(procedencia(ctx.provider.origem, carteira[0]?.atualizadoEm));

      return texto(partes.join('\n\n'));
    }),
  );

  server.registerTool(
    'listar_emprestimos',
    {
      title: 'Listar emprestimos e financiamentos',
      description:
        'Emprestimos, consignados e financiamentos em aberto: saldo devedor, parcela, taxa de juros, CET e ' +
        'quantas parcelas faltam. Use para "quanto eu devo", para comparar o custo da divida com o rendimento ' +
        'da carteira e para avaliar quitacao antecipada.',
      inputSchema: {
        instituicaoId: z.string().optional().describe('Restringe a uma instituicao.'),
      },
      annotations: LEITURA,
    },
    protegido(async ({ instituicaoId }: { instituicaoId?: string }) => {
      const emprestimos = (await ctx.provider.listarEmprestimos()).filter(
        (e) => !instituicaoId || e.instituicaoId === instituicaoId,
      );
      if (emprestimos.length === 0) {
        return texto('Nenhum emprestimo ou financiamento em aberto nas conexoes ativas.' + procedencia(ctx.provider.origem));
      }

      const saldoTotal = soma(emprestimos.map((e) => e.saldoDevedor));
      const parcelaTotal = soma(emprestimos.map((e) => e.valorParcela));

      const linhas = emprestimos.map((e) => {
        const faltam = e.parcelasTotais - e.parcelasPagas;
        return [
          e.descricao,
          e.instituicao,
          brl(e.saldoDevedor),
          brl(e.valorParcela),
          `${e.parcelasPagas}/${e.parcelasTotais}`,
          `${e.taxaJurosMensal.toFixed(2)}% a.m.`,
          e.cetAnual ? `${e.cetAnual.toFixed(1)}% a.a.` : '-',
          e.proximoVencimento ? formatarDia(e.proximoVencimento) : '-',
          String(faltam),
        ];
      });

      const observacoes = emprestimos.map((e) => {
        const faltam = e.parcelasTotais - e.parcelasPagas;
        const aPagar = faltam * e.valorParcela;
        const jurosRestantes = aPagar - e.saldoDevedor;
        return `**${e.descricao}**: faltam ${faltam} parcelas, somando ${brl(aPagar)}. ` +
          `O saldo devedor hoje e ${brl(e.saldoDevedor)}, ou seja, ainda ha ${brl(jurosRestantes)} de juros ` +
          `embutidos no caminho — quitar antecipadamente exige, por lei, desconto proporcional desses juros ` +
          `(art. 52, §2º do CDC).`;
      });

      const md = [
        titulo(`Divida total: ${brl(saldoTotal)}`),
        `Compromisso mensal com parcelas: **${brl(parcelaTotal)}**`,
        tabela(
          ['Contrato', 'Instituicao', 'Saldo devedor', 'Parcela', 'Pagas', 'Juros', 'CET', 'Proximo venc.', 'Faltam'],
          linhas,
          ['esq', 'esq', 'dir', 'dir', 'centro', 'dir', 'dir', 'esq', 'dir'],
        ),
        `${titulo('Leitura', 3)}\n${lista(observacoes)}`,
        `\n_Saldo devedor e o valor de quitacao informado pela instituicao na ultima sincronizacao; ` +
        `o valor exato do dia costuma sair so no canal do proprio banco._`,
        procedencia(ctx.provider.origem),
      ].join('\n\n');

      return texto(md);
    }),
  );
};
