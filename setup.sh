#!/usr/bin/env bash
# AI-TUTOR — one-time environment setup.
# Installs the tools the tutor uses: the NotebookLM media CLI (in its own venv)
# and a browser for it. The Playwright MCP is handled by Claude Code via npx.
# Safe to re-run (idempotent). Login steps are interactive and prompted, not here.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "==> AI-TUTOR setup"
echo "    Repo: $ROOT"
echo ""

# 1. Python 3 check (needed for the NotebookLM media tool)
if ! command -v python3 >/dev/null 2>&1; then
  echo "WARNING: python3 not found."
  echo "  The core tutoring engine works without it, but the optional"
  echo "  podcast/video/mind-map media needs Python 3.10+."
  echo "  Install from https://www.python.org/downloads/ or 'brew install python',"
  echo "  then re-run this script."
else
  echo "    Python: $(python3 --version)"
  # 2. Install the NotebookLM CLI via the bundled skill setup (creates ~/.notebooklm-venv)
  NB_SETUP="$ROOT/.claude/skills/notebooklm/setup.sh"
  if [ -f "$NB_SETUP" ]; then
    echo ""
    echo "==> Installing the NotebookLM media tool..."
    bash "$NB_SETUP" || echo "    (NotebookLM setup had a problem — media features may be unavailable; the tutor still works.)"
  fi
fi

# 3. Node / npx check (for the Playwright browser tool used for live docs/research)
echo ""
if command -v npx >/dev/null 2>&1; then
  echo "    Node/npx: present (Playwright MCP will load on first use)."
else
  echo "    Node/npx not found — install Node.js (https://nodejs.org) for the"
  echo "    live-docs browser tool. Optional; the tutor works without it."
fi

echo ""
echo "==> Base setup done."
echo "    Next, in Claude Code:"
echo "      • /setup       finishes any logins (NotebookLM) — optional"
echo "      • /onboarding  picks your subject and builds your curriculum"
