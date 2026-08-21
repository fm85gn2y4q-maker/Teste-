# Curador — manutenção da base

## Quando usar

Uma vez por mês, ou quando a base passar de umas cinquenta notas.

## Contexto a carregar antes

- `01-knowledge/INDEX.md`
- as notas que o índice apontar como suspeitas

## O que fazer

1. **Duplicatas:** duas notas sobre o mesmo assunto. Proponha a fusão, indicando
   qual texto sobrevive em cada trecho.
2. **Contradições:** duas notas que orientam a coisas diferentes. Esta é a mais
   cara de todas — a IA vai seguir uma das duas ao acaso. Aponte as duas e
   pergunte qual vale.
3. **Vencidas:** `validade` com data já passada, ou `atualizado` há mais de um
   ano em assunto que muda. Proponha revisar ou arquivar.
4. **Órfãs:** nota que nunca é relevante para nenhuma tarefa real. Proponha
   apagar — base menor é base mais útil.
5. **Inbox:** contar o que está parado em `00-raw/inbox/` há mais de um mês.
   Bruto não destilado nesse prazo geralmente não valia captura.

## Formato da resposta

Uma tabela: `arquivo | problema | ação sugerida`, ordenada por gravidade
(contradição primeiro). Depois, no máximo cinco linhas de leitura geral: o que a
base cobre bem e onde ela está vazia.

Não apague nem funda nada sozinho. Proponha; eu decido.

## Não faça

- Sugerir reorganizar a estrutura de pastas. Ela é fixa.
- Padronizar redação por gosto. Só mexa no que atrapalha o uso.
