# 00-raw — material bruto

Zona de despejo. Aqui a única regra é capturar rápido; organizar é problema do
passo seguinte.

- `inbox/` — o que ainda não foi destilado. Deve tender a zero toda semana.
- `fontes/` — o bruto que já virou nota, guardado só para conferência posterior.

O que entra: transcrição de vídeo ou reunião, e-mail colado, trecho de PDF,
link com duas linhas de comentário, ideia solta às 23h, print descrito em texto.

O que **não** entra: senha, token, chave de API, dado pessoal de terceiro,
documento sob sigilo.

Nada aqui é lido automaticamente pela IA — só quando você apontar o arquivo.

## Capturar

```
./base-de-conhecimento/scripts/captura.sh "titulo curto"
```

Cria o arquivo com data e cabeçalho e abre o `$EDITOR`. Também aceita entrada
por pipe:

```
pbpaste | ./base-de-conhecimento/scripts/captura.sh "artigo sobre X"
```

## Destilar

```
Leia base-de-conhecimento/00-raw/inbox/<arquivo>.md e siga
base-de-conhecimento/02-agents/destilador.md
```

Aprovada a nota, mova o bruto para `fontes/` ou apague.
