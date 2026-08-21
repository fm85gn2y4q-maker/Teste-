# 02-agents — papéis reutilizáveis

Prompt bom não se joga fora. Cada arquivo aqui é um papel que a IA assume
quando você aponta para ele:

```
Siga base-de-conhecimento/02-agents/destilador.md para o arquivo <x>.
```

Se a sua ferramenta suporta subagentes, comandos ou skills próprios, estes
arquivos são a fonte: copie o conteúdo para o formato dela e mantenha a versão
canônica aqui, que é portátil entre ferramentas.

## Papéis prontos

- `destilador.md` — transforma bruto de `00-raw/` em nota de `01-knowledge/`.
- `curador.md` — revisa a base atrás de duplicata, contradição e nota vencida.

## Criar um novo

Copie `_template-agente.md`. Regra prática: só vira agente o que você já pediu
três vezes com o mesmo formato de resposta.
