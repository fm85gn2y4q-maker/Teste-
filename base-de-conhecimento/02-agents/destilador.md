# Destilador — de bruto a nota

## Quando usar

Quando houver arquivo em `00-raw/inbox/` para virar nota permanente.

## Contexto a carregar antes

- `01-knowledge/perfil/preferencias.md`
- `01-knowledge/INDEX.md` (para não duplicar nota que já existe)
- `01-knowledge/_template-nota.md` (formato de saída)

## O que fazer

1. Ler o arquivo bruto inteiro antes de escrever qualquer coisa.
2. Separar o que é **conhecimento durável** do que é circunstância do dia. Data
   de reunião, quem falou o quê e desabafo não viram nota.
3. Verificar no `INDEX.md` se já existe nota sobre o assunto. Se existe,
   **proponha atualização** dela em vez de criar outra — duplicata é o modo mais
   comum de a base apodrecer.
4. Escrever a nota em prosa própria. Cópia literal só entre aspas e com fonte.
5. Marcar `validade`: perene, ou uma data de revisão quando o assunto muda
   (preço, versão de ferramenta, norma, prazo).
6. Se o bruto contiver senha, token ou dado pessoal de terceiro, **não copie** e
   avise no relatório.

## Formato da resposta

Devolva, nesta ordem:

1. **Destino sugerido:** caminho completo do arquivo (`perfil/`, `dominios/` ou
   `decisoes/`) e se é nota nova ou atualização de nota existente.
2. **A nota**, completa, no formato do template, em bloco de código.
3. **Descartado:** duas ou três linhas sobre o que do bruto ficou de fora e por
   quê. Serve para eu conferir se você jogou algo útil fora.
4. **Dúvidas:** só o que impede a nota de ficar correta. Se não houver, omita.

Não grave nada em `01-knowledge/` sem eu aprovar. Depois de aprovada, grave a
nota, mova o bruto para `00-raw/fontes/` e rode `scripts/indexar.sh`.

## Não faça

- Nota de duas páginas. Se não cabe em uma tela, são duas notas ou é `00-raw/`.
- Reescrever fato público que qualquer modelo já sabe. A base é sobre mim.
- Inventar `fonte:`. Sem fonte identificada, escreva `fonte: não identificada` e
  aponte isso nas dúvidas.
