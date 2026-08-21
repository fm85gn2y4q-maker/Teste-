import { z } from 'zod';
import { brl, soma } from '../util/dinheiro.js';
import { diferencaEmDias, formatarDia, mesPorExtenso } from '../util/datas.js';
import { barra, lista, procedencia, tabela, titulo } from '../formato.js';
import { porCategoria } from '../analise/gastos.js';
import { LEITURA, protegido, texto, type Registrador } from './base.js';

export const registrarCartoes: Registrador = (server, ctx) => {
  server.registerTool(
    'listar_cartoes',
    {
      title: 'Listar cartoes de credito',
      description:
        'Lista os cartoes de credito conectados com limite total, limite disponivel, percentual usado e as ' +
        'datas de fechamento e vencimento. Use para saber quanto de limite sobra e quando cada fatura fecha.',
      inputSchema: {
        instituicaoId: z.string().optional().describe('Restringe a uma instituicao.'),
      },
      annotations: LEITURA,
    },
    protegido(async ({ instituicaoId }: { instituicaoId?: string }) => {
      const cartoes = (await ctx.provider.listarCartoes()).filter(
        (c) => !instituicaoId || c.instituicaoId === instituicaoId,
      );
      if (cartoes.length === 0) {
        return texto('Nenhum cartao de credito nas conexoes ativas.' + procedencia(ctx.provider.origem));
      }

      const linhas = cartoes.map((c) => {
        const usado = c.limiteTotal - c.limiteDisponivel;
        const uso = c.limiteTotal === 0 ? 0 : (usado / c.limiteTotal) * 100;
        return [
          `\`${c.id}\``,
          `${c.apelido} (${c.bandeira} •${c.finalNumero})`,
          brl(c.limiteTotal),
          brl(c.limiteDisponivel),
          `${uso.toFixed(0)}% ${barra(uso, 8)}`,
          `fecha ${c.diaFechamento} · vence ${c.diaVencimento}`,
        ];
      });

      const apertados = cartoes.filter(
        (c) => c.limiteTotal > 0 && c.limiteDisponivel / c.limiteTotal < 0.2,
      );

      const md = [
        titulo(`${cartoes.length} cartoes`),
        tabela(
          ['ID', 'Cartao', 'Limite', 'Disponivel', 'Uso', 'Ciclo'],
          linhas,
          ['esq', 'esq', 'dir', 'dir', 'esq', 'esq'],
        ),
        apertados.length
          ? `\n${titulo('Atencao', 3)}\n` +
            lista(apertados.map((c) => `${c.apelido}: resta ${brl(c.limiteDisponivel)} de ${brl(c.limiteTotal)}.`))
          : '',
        `\n_Limite disponivel ja desconta fatura aberta e fatura fechada ainda nao paga._`,
        procedencia(ctx.provider.origem),
      ].join('\n\n');

      return texto(md);
    }),
  );

  server.registerTool(
    'consultar_fatura',
    {
      title: 'Consultar fatura do cartao',
      description:
        'Fatura de cartao de credito: valor total, minimo, datas de fechamento e vencimento, quebra por ' +
        'categoria e os maiores lancamentos. Sem argumentos, traz a fatura corrente de cada cartao. ' +
        'Use para "quanto vem na fatura", "o que pesou nessa fatura" e conferencia de compra.',
      inputSchema: {
        cartaoId: z.string().optional().describe('Cartao especifico (veja listar_cartoes).'),
        mes: z.string().regex(/^\d{4}-\d{2}$/).optional()
          .describe('Mes de referencia YYYY-MM. Padrao: a fatura aberta ou a mais recente.'),
        detalhar: z.boolean().optional().describe('Lista todos os lancamentos, nao so os maiores. Padrao: false.'),
      },
      annotations: LEITURA,
    },
    protegido(async ({ cartaoId, mes, detalhar }: { cartaoId?: string; mes?: string; detalhar?: boolean }) => {
      const todas = await ctx.provider.listarFaturas(cartaoId, mes);
      if (todas.length === 0) {
        const cartoes = await ctx.provider.listarCartoes();
        return texto(
          `Nenhuma fatura encontrada${mes ? ` para ${mesPorExtenso(mes)}` : ''}. ` +
          `Cartoes disponiveis: ${cartoes.map((c) => `\`${c.id}\` (${c.apelido})`).join(', ') || 'nenhum'}.` +
          procedencia(ctx.provider.origem),
        );
      }

      // Sem mes informado: uma fatura por cartao — a aberta, ou a mais recente.
      const selecionadas = mes
        ? todas
        : [...new Map(
            [...todas]
              .sort((a, b) => {
                const peso = (s: string) => (s === 'aberta' ? 0 : s === 'fechada' ? 1 : 2);
                return peso(a.status) - peso(b.status) || b.mesReferencia.localeCompare(a.mesReferencia);
              })
              .map((f) => [f.cartaoId, f]),
          ).values()];

      const hoje = ctx.hoje();
      const blocos = selecionadas.map((f) => {
        const dias = diferencaEmDias(hoje, f.dataVencimento);
        const prazo =
          f.status === 'paga' ? 'ja paga'
          : dias < 0 ? `**vencida ha ${-dias} dias**`
          : dias === 0 ? '**vence hoje**'
          : `vence em ${dias} dias`;

        const categorias = porCategoria(f.lancamentos).slice(0, 6).map((g) => [
          g.chave, brl(g.total), `${g.percentual.toFixed(0)}%`, barra(g.percentual, 10),
        ]);

        const lancamentos = detalhar
          ? [...f.lancamentos].sort((a, b) => a.data.localeCompare(b.data))
          : [...f.lancamentos].sort((a, b) => Math.abs(b.valor) - Math.abs(a.valor)).slice(0, 10);

        const linhasLanc = lancamentos.map((t) => [
          formatarDia(t.data),
          t.descricao.length > 40 ? `${t.descricao.slice(0, 39)}…` : t.descricao,
          t.categoria,
          brl(-t.valor),
        ]);

        return [
          titulo(`${f.cartao} — fatura de ${mesPorExtenso(f.mesReferencia)}`),
          lista([
            `Total: **${brl(f.valorTotal)}** (${f.status}, ${prazo})`,
            `Minimo: ${brl(f.valorMinimo)} — pagar o minimo joga o resto para o rotativo, a linha de credito mais cara que existe.`,
            `Fechou em ${formatarDia(f.dataFechamento)}, vence em ${formatarDia(f.dataVencimento)}`,
            `${f.lancamentos.length} lancamentos`,
          ]),
          categorias.length ? `${titulo('Por categoria', 3)}\n${tabela(['Categoria', 'Total', '%', ''], categorias, ['esq', 'dir', 'dir', 'esq'])}` : '',
          linhasLanc.length
            ? `${titulo(detalhar ? 'Lancamentos' : 'Maiores lancamentos', 3)}\n${tabela(['Data', 'Descricao', 'Categoria', 'Valor'], linhasLanc, ['esq', 'esq', 'esq', 'dir'])}`
            : '',
        ].filter(Boolean).join('\n\n');
      });

      const total = soma(selecionadas.map((f) => f.valorTotal));
      const rodape = selecionadas.length > 1
        ? `\n**Somando os ${selecionadas.length} cartoes: ${brl(total)}.**`
        : '';

      return texto(`${blocos.join('\n\n---\n\n')}${rodape}${procedencia(ctx.provider.origem)}`);
    }),
  );
};
