# Base de Conhecimento para LLM

Estrutura de arquivos para que qualquer IA (Claude Code, Codex, Gemini CLI)
trabalhe com o **seu** contexto em vez de recomeçar do zero a cada conversa.

A ideia por trás: a ferramenta é descartável, o contexto não. Trocar de CLI por
ganho marginal custa tempo; o que se acumula e não se perde é a base de
conhecimento. Ela fica em arquivos de texto, versionados no Git, legíveis por
qualquer modelo — hoje e daqui a três trocas de ferramenta.

## As três pastas

| Pasta | O que entra | Quem escreve | Qualidade |
|---|---|---|---|
| `00-raw/` | material bruto: transcrições, PDFs, e-mails colados, prints, links, anotações soltas | você, rápido e sem cuidado | descartável |
| `01-knowledge/` | notas destiladas: um assunto por arquivo, em prosa própria, com fonte | a IA propõe, você aprova | permanente |
| `02-agents/` | instruções reutilizáveis: prompts, papéis, checklists de tarefa | você, com ajuda da IA | permanente |

A separação é o que faz funcionar. `00-raw/` pode ser bagunçado justamente
porque nada lê ele direto na hora de trabalhar. `01-knowledge/` é limpo porque
é o que a IA carrega como contexto todo dia.

## O fluxo, em três passos

1. **Capturar** — jogue tudo em `00-raw/inbox/`, sem organizar.
   ```
   ./base-de-conhecimento/scripts/captura.sh "reuniao cliente X"
   ```
2. **Destilar** — peça à IA para transformar o bruto em nota:
   ```
   Leia base-de-conhecimento/00-raw/inbox/2026-08-21-reuniao-cliente-x.md
   e siga base-de-conhecimento/02-agents/destilador.md
   ```
   Ela devolve uma nota candidata; você corrige e move para `01-knowledge/`.
3. **Reutilizar** — em qualquer sessão nova:
   ```
   Leia base-de-conhecimento/CLAUDE.md antes de responder.
   ```
   Se estiver usando Claude Code na raiz do projeto, o `CLAUDE.md` já é lido
   automaticamente.

Depois de destilar, apague ou arquive o bruto em `00-raw/fontes/`. O bruto que
sobra vira ruído.

## Por que não deixar tudo em `00-raw/`

Porque contexto tem custo e teto. Trinta transcrições cruas gastam a janela de
contexto inteira e ainda entregam informação contraditória — a versão antiga e
a nova da mesma decisão, com o mesmo peso. Uma nota destilada de 20 linhas vale
mais que a transcrição de uma hora, e é ela que faz o aprendizado ser cumulativo
em vez de repetido.

## Regras que valem a pena manter

- **Um assunto por arquivo.** Se a nota trata de duas coisas, são duas notas.
- **Sempre com fonte.** Toda nota em `01-knowledge/` declara de onde veio e
  quando. Sem isso não dá para saber, seis meses depois, se ainda vale.
- **Prosa própria, não recorte.** Copiar o texto original devolve o problema do
  bruto. Reescrever é o que destila.
- **Data em tudo.** Preferência muda, decisão é revista. Nota sem data envelhece
  sem avisar.
- **Nada de segredo aqui.** Senha, token, dado de cliente identificável e
  documento sob sigilo não entram — este diretório é versionado e vai junto em
  todo prompt.

## Estrutura

```
base-de-conhecimento/
├── CLAUDE.md              # o que a IA lê primeiro
├── 00-raw/
│   ├── inbox/             # captura do dia, ainda não destilada
│   └── fontes/            # bruto já destilado, guardado por referência
├── 01-knowledge/
│   ├── perfil/            # quem você é, como trabalha, o que prefere
│   ├── dominios/          # conhecimento por assunto
│   ├── decisoes/          # decisões tomadas e o porquê
│   └── _template-nota.md
├── 02-agents/
│   ├── destilador.md      # bruto -> nota
│   ├── curador.md         # revisa e poda a base
│   └── _template-agente.md
└── scripts/
    ├── captura.sh         # cria arquivo em 00-raw/inbox com cabeçalho
    └── indexar.sh         # gera 01-knowledge/INDEX.md a partir das notas
```

## Rotina mínima

- **Diária:** capturar no inbox. Nada mais.
- **Semanal:** destilar o inbox até zerar; rodar `scripts/indexar.sh`.
- **Mensal:** rodar o `curador.md` para achar nota duplicada, vencida ou
  contraditória.

## Usar fora deste repositório

A base não é específica deste projeto. Duas formas de levá-la para todo lugar:

**Como repositório próprio.** Mova `base-de-conhecimento/` para um repo só dela
(`~/conhecimento`, por exemplo) e aponte cada projeto para lá, no `CLAUDE.md`
da raiz:

```
Antes de responder, leia ~/conhecimento/CLAUDE.md.
```

**Global, para toda sessão.** No Claude Code, o arquivo `~/.claude/CLAUDE.md` é
lido em qualquer diretório. Uma linha basta:

```
Antes de responder, leia ~/conhecimento/CLAUDE.md e siga o que estiver lá.
```

Em outras ferramentas o nome do arquivo muda (`AGENTS.md`, `GEMINI.md`,
`.cursorrules`), mas o conteúdo é o mesmo — é justamente por isso que a base
mora em Markdown puro: ela sobrevive à troca de ferramenta.
