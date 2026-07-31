---
name: notebooklm
description: >-
  Use when the user wants to work with Google NotebookLM — create notebooks, add
  sources (PDF, URL, text, YouTube, Google Drive), ask questions to a notebook,
  generate an Audio Overview (podcast), summaries/briefing docs, mind maps, or
  chat with a source-grounded notebook. Primary path is the `notebooklm` CLI
  (notebooklm-py) — fast and browser-free. Browser is only needed once, for login.
---

# NotebookLM

Drive Google NotebookLM from the command line. The **CLI is the primary path**
and needs **no browser** for day-to-day use. A browser opens only **once**, for
the initial Google login.

This skill works with **your own** NotebookLM account (notebooklm.google.com).

## First run: bootstrap (do this automatically if not set up)

Before any NotebookLM action, check setup and fix it if missing:

1. **Is the CLI installed?**
   ```bash
   test -x "$HOME/.notebooklm-venv/bin/notebooklm" && echo INSTALLED || echo MISSING
   ```
   If `MISSING`, run the bundled setup script (creates a venv + installs the lib):
   ```bash
   bash "<skill-dir>/setup.sh"
   ```
   (`<skill-dir>` is the folder this SKILL.md lives in.)

2. **Is the user logged in?**
   ```bash
   "$HOME/.notebooklm-venv/bin/notebooklm" doctor
   ```
   - If `Auth` ✓ pass → ready, proceed.
   - If auth is missing/expired → run login (see below). This is the ONLY browser step.

3. **Login (only when needed):**
   ```bash
   "$HOME/.notebooklm-venv/bin/notebooklm" login --browser chrome
   ```
   A Chrome window opens. **Tell the user to sign in to their Google account and
   approve any 2FA prompt.** The session saves automatically. Authentication is
   stored at `~/.notebooklm/profiles/default/storage_state.json`.
   - `--browser chrome` uses system Chrome (most reliable on macOS 15+). Drop the
     flag to use bundled Chromium, or use `--browser msedge` for SSO orgs.
   - Keep the session warm without a browser: `notebooklm auth refresh`
     (safe every ~15–20 min).

> Set `NB="$HOME/.notebooklm-venv/bin/notebooklm"` once, then use `$NB ...`.

## Essential commands

| Task | Command |
|------|---------|
| List your notebooks | `$NB list` |
| Create a notebook | `$NB create "Title"` |
| Set current notebook | `$NB use <partial-id>`  (or pass `-n <id>` per command) |
| Add a source (auto-detects url/file/youtube/text) | `$NB source add "<url\|path\|text>" -n <id>` |
| Add from Google Drive | `$NB source add-drive ... -n <id>` |
| List sources | `$NB source list -n <id>` |
| Ask a question | `$NB ask "your question" -n <id>` |
| Notebook summary | `$NB summary -n <id>` |
| Chat history | `$NB history -n <id>` |
| **Generate Audio Overview** | `$NB generate audio "optional focus" -n <id> [--format deep-dive\|brief\|critique\|debate] [--length short\|default\|long] [--language en\|pt-BR\|...]` |
| **Download audio** | `$NB download audio "<path.mp3>" -n <id>`  (defaults to latest) |
| Wait for an artifact | `$NB artifact wait -n <id>`  /  `$NB artifact poll` |
| Other artifacts | `$NB generate {mind-map\|report\|slide-deck\|flashcards\|quiz\|infographic\|data-table\|video} -n <id>` |

`-n` accepts **partial IDs** (e.g. `-n 1e6926`). Add `--json` for machine-readable
output when you need to parse results.

## Rules

1. **Audio Overview is asynchronous.** After `generate audio`, run `artifact wait`
   (or `poll`) before `download audio`. Large notebooks (~10 sources) can take
   **10–15 min**; small ones 3–7 min. Don't regenerate before it finishes.
2. Save downloaded files where the user expects (default: `~/Downloads/`).
3. To find a notebook's ID, run `$NB list` — never hardcode IDs.
4. If `doctor` reports expired auth → try `auth refresh` first; only re-run
   `login` (with 2FA) if refresh fails.

## Notes & limitations (be honest with the user)

- Built on **notebooklm-py**, an *unofficial* library — it can break if Google
  changes its backend. Update with: `"$HOME/.notebooklm-venv/bin/pip" install -U
  notebooklm-py`.
- Works with **consumer** NotebookLM accounts. (Google's official *Enterprise*
  API exists but only covers NotebookLM Enterprise / Google Agentspace, not
  consumer accounts.)
- The session expires periodically — when it does, just re-run `login`.

## Browser fallback

If the CLI can't do something (a brand-new UI feature), fall back to Playwright
against https://notebooklm.google.com (notebook at `/notebook/[ID]`). Detailed
browser steps are in `workflows.md`.
