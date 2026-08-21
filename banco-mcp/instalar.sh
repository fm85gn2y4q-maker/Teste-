#!/usr/bin/env bash
# Instalador do Banco MCP: da maquina limpa ate o servidor registrado no Claude.
#
#   bash banco-mcp/instalar.sh          # dentro do repositorio ja clonado
#   curl -fsSL <url-deste-arquivo> | bash   # de qualquer lugar (ele clona)
set -euo pipefail

REPO="https://github.com/fm85gn2y4q-maker/Teste-.git"
BRANCH="claude/create-iphone-app-9YNOb"

azul()  { printf '\033[1;34m%s\033[0m\n' "$*"; }
erro()  { printf '\033[1;31m%s\033[0m\n' "$*" >&2; }
passo() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

# --- 1. Node ---------------------------------------------------------------
passo "Conferindo o Node"
if ! command -v node >/dev/null 2>&1; then
  erro "Node nao encontrado. Instale a versao 20 ou mais nova: https://nodejs.org"
  exit 1
fi
VERSAO=$(node -p "process.versions.node.split('.')[0]")
if [ "$VERSAO" -lt 20 ]; then
  erro "Node $(node -v) e antigo demais. Precisa da versao 20 ou mais nova."
  exit 1
fi
echo "Node $(node -v), ok."

# --- 2. Codigo -------------------------------------------------------------
if [ -f "banco-mcp/package.json" ]; then
  DIR="$(pwd)/banco-mcp"
elif [ -f "package.json" ] && [ -d "src/providers" ]; then
  DIR="$(pwd)"
else
  passo "Baixando o codigo"
  command -v git >/dev/null 2>&1 || { erro "git nao encontrado."; exit 1; }
  DESTINO="${HOME}/banco-mcp"
  if [ -d "$DESTINO/.git" ]; then
    git -C "$DESTINO" fetch origin "$BRANCH" --quiet
    git -C "$DESTINO" checkout --quiet "$BRANCH"
    git -C "$DESTINO" pull --quiet origin "$BRANCH"
  else
    git clone --quiet --branch "$BRANCH" "$REPO" "$DESTINO"
  fi
  DIR="$DESTINO/banco-mcp"
  echo "Clonado em $DESTINO"
fi
cd "$DIR"

# --- 3. Dependencias e build ----------------------------------------------
passo "Instalando dependencias e compilando"
npm install --no-audit --no-fund --loglevel=error
npm run build --silent
echo "Compilado."

# --- 4. Teste rapido: o servidor responde? ---------------------------------
passo "Testando o servidor em modo demonstracao"
RESUMO=$(BANCO_MCP_PROVEDOR=mock node -e '
import("./dist/providers/index.js").then(async ({ criarProvider }) => {
  const { carregarConfig } = await import("./dist/config.js");
  const p = criarProvider({ ...carregarConfig(), provedor: "mock" });
  const contas = await p.listarContas();
  console.log(`${contas.length} contas de demonstracao carregadas`);
});')
echo "$RESUMO"

# --- 5. Dados reais? -------------------------------------------------------
passo "Dados reais do seu banco?"
cat <<'TXT'
Para ligar nos seus bancos voce precisa de:
  - conta em meu.pluggy.ai com os bancos ja conectados
  - clientId e clientSecret do dashboard.pluggy.ai

Isso e gratuito para uso pessoal. Se ainda nao tiver, tudo bem: o servidor
funciona em modo demonstracao e voce liga depois rodando "npm run configurar".
TXT
printf '\nConfigurar credenciais agora? [s/N] '
# Le do terminal mesmo quando o script chega por pipe (curl | bash).
RESPOSTA="n"
if [ -t 0 ]; then
  read -r RESPOSTA || RESPOSTA="n"
elif read -r RESPOSTA 2>/dev/null </dev/tty; then
  : # leu do terminal
else
  RESPOSTA="n"
  echo "(sem terminal interativo — pulando; rode 'npm run configurar' depois)"
fi

if [ "${RESPOSTA:-n}" = "s" ] || [ "${RESPOSTA:-n}" = "S" ]; then
  node dist/configurar.js
  passo "Buscando as conexoes ja existentes na sua conta"
  node dist/conectar.js --listar || {
    echo
    echo "Nao consegui listar automaticamente. Para conectar pelo navegador:"
    echo "  cd $DIR && npm run conectar"
  }
  passo "Diagnostico"
  node dist/diagnostico.js || true
fi

# --- 6. Registro no Claude -------------------------------------------------
passo "Ultimo passo"
if command -v claude >/dev/null 2>&1; then
  claude mcp add banco -- node "$DIR/dist/index.js" && azul "Servidor registrado. Abra o Claude Code e pergunte: como estao minhas financas?"
else
  cat <<TXT
O comando "claude" nao esta no PATH. Quando instalar o Claude Code, rode:

  claude mcp add banco -- node $DIR/dist/index.js

Ou, no app de desktop / Cursor, acrescente ao arquivo de configuracao MCP:

  "banco": { "command": "node", "args": ["$DIR/dist/index.js"] }
TXT
fi
