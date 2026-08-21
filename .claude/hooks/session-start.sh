#!/bin/bash
# Prepara o servidor MCP de dados bancarios para a sessao: instala dependencias
# e compila, para que o servidor registrado em .mcp.json suba sem passo manual.
set -euo pipefail

# So no ambiente remoto (Claude Code na web). Localmente, quem manda e o dev.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PROJETO="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$PROJETO/banco-mcp"

# npm install (e nao ci) para aproveitar o cache do container entre sessoes.
npm install --no-audit --no-fund --loglevel=error
npm run build --silent

echo "banco-mcp compilado em $PROJETO/banco-mcp/dist"
