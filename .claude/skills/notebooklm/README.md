# NotebookLM skill for Claude Code

Control Google NotebookLM from Claude Code — create notebooks, add sources, ask
questions, and generate Audio Overviews (podcasts) **from the command line, with
no browser** (a browser opens only once, for the initial Google login).

Works with your **own** NotebookLM account (notebooklm.google.com).

---

## Requirements

- **Claude Code** installed
- **Python 3.10+** (`python3 --version`)
- **Google Chrome** (used once for login)
- A Google account with access to NotebookLM

## Install (3 steps)

### 1. Copy the skill into Claude Code

```bash
mkdir -p ~/.claude/skills
cp -R notebooklm-skill ~/.claude/skills/notebooklm
```

### 2. Run the setup script (installs the NotebookLM CLI)

```bash
bash ~/.claude/skills/notebooklm/setup.sh
```

This creates a small Python environment at `~/.notebooklm-venv` and installs the
`notebooklm` command. Safe to run more than once.

### 3. Log in (one time)

```bash
~/.notebooklm-venv/bin/notebooklm login --browser chrome
```

A Chrome window opens — sign in to your Google account and approve the 2FA
prompt. The session is saved automatically. **You only do this once** (re-do it
if your session expires later).

---

## Using it

Just talk to Claude Code naturally — it will use the skill automatically:

- *"List my NotebookLM notebooks"*
- *"Create a notebook called Study Notes and add this YouTube video: <url>"*
- *"Ask my Biology notebook to summarize chapter 3"*
- *"Generate an audio overview (podcast) of my Marketing notebook and download it"*

Or use the CLI directly:

```bash
NB=~/.notebooklm-venv/bin/notebooklm
$NB list                                   # your notebooks
$NB create "Study Notes"
$NB source add "https://youtu.be/..." -n <id>
$NB ask "summarize the key points" -n <id>
$NB generate audio "deep dive" -n <id> --language en
$NB download audio ~/Downloads/episode.mp3 -n <id>
```

(`-n` accepts a partial notebook ID. Run `$NB list` to see IDs.)

---

## Troubleshooting

| Problem | Fix |
|--------|-----|
| `notebooklm: command not found` | Use the full path `~/.notebooklm-venv/bin/notebooklm`, or re-run `setup.sh`. |
| Auth errors / expired session | `~/.notebooklm-venv/bin/notebooklm login --browser chrome` |
| Keep a long session alive | `~/.notebooklm-venv/bin/notebooklm auth refresh` (every ~15–20 min) |
| Chromium crashes on login | Use `--browser chrome` (system Chrome), as shown above. |
| Check everything is OK | `~/.notebooklm-venv/bin/notebooklm doctor` |
| Update the tool | `~/.notebooklm-venv/bin/pip install -U notebooklm-py` |

---

## Notes

- Built on [`notebooklm-py`](https://github.com/teng-lin/notebooklm-py), an
  **unofficial** library. It can break if Google changes NotebookLM's backend —
  update with the command above if something stops working.
- Audio Overviews are generated asynchronously and can take 3–15 minutes
  depending on how many sources the notebook has.
- Your Google credentials are **never** stored by this skill — login is handled
  by Google in the browser, and only a session cookie is saved locally on your
  machine (`~/.notebooklm/`).
