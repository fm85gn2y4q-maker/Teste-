#!/usr/bin/env bash
# NotebookLM skill — one-time setup.
# Creates a dedicated Python venv and installs the notebooklm-py CLI.
# Safe to re-run (idempotent).
set -euo pipefail

VENV="$HOME/.notebooklm-venv"
NB="$VENV/bin/notebooklm"

echo "==> NotebookLM skill setup"

# 1. Python 3 check
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.10+ first (https://www.python.org/downloads/ or 'brew install python')." >&2
  exit 1
fi
echo "    Python: $(python3 --version)"

# 2. Create venv if missing
if [ ! -x "$VENV/bin/python" ]; then
  echo "    Creating virtualenv at $VENV ..."
  python3 -m venv "$VENV"
else
  echo "    Virtualenv already exists at $VENV"
fi

# 3. Install / upgrade the library
echo "    Installing notebooklm-py (this may take a minute)..."
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet --upgrade "notebooklm-py[browser]"

# 4. Install Chromium for the one-time login (ignore failure; system Chrome also works)
echo "    Installing Chromium for login (optional)..."
"$VENV/bin/python" -m playwright install chromium >/dev/null 2>&1 || \
  echo "    (Chromium install skipped — you can log in with --browser chrome instead)"

echo ""
echo "==> Installed: $("$NB" --version)"
echo ""

# 5. Auth status
if "$NB" doctor 2>/dev/null | grep -q "All checks passed"; then
  echo "==> You are already logged in. Setup complete."
else
  echo "==> Next step — log in once (a browser window will open):"
  echo "      $NB login --browser chrome"
  echo "    Sign in to your Google account and approve the 2FA prompt."
fi

echo ""
echo "==> Quick start:"
echo "      NB=\"$NB\""
echo "      \$NB list                       # see your notebooks"
echo "      \$NB ask \"hello\" -n <id>        # ask a notebook"
echo "      \$NB generate audio -n <id>      # make a podcast"
