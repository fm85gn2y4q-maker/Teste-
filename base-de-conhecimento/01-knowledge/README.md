# 01-knowledge — conhecimento destilado

A parte permanente. Todo arquivo aqui foi lido, reescrito e aprovado por você.
É isto que a IA carrega como contexto.

## Subpastas

- `perfil/` — quem você é, como trabalha, o que prefere. Curto e sempre lido.
- `dominios/` — conhecimento por assunto. Um assunto por arquivo.
- `decisoes/` — decisões tomadas, com data e motivo. É o que evita rediscutir
  a mesma coisa em três meses.

## Formato

Use `_template-nota.md`. O cabeçalho YAML é o que o `scripts/indexar.sh` lê para
montar o `INDEX.md`, então mantenha os campos.

## Critério para uma nota entrar

Vale a nota se ela responde sim a alguma destas:

- vou precisar disso mais de uma vez?
- se eu esquecer, refazer custa caro?
- é uma preferência minha que a IA erraria sozinha?

Se é fato público que qualquer modelo já sabe, não vale nota. A base é sobre
**você**, não sobre o mundo.

## Manutenção

- `scripts/indexar.sh` regenera o `INDEX.md`.
- `02-agents/curador.md` revisa a base atrás de duplicata, contradição e nota
  vencida.
