---
name: setup
description: First-run environment setup for AI-TUTOR — install and verify the tools the tutor needs (NotebookLM media CLI, Playwright browser, Python), prompting the learner to log in where required. Use on the very first session, when progress.json is uninitialized, or when the user runs /setup or says "set up the tools", "install", "fix my tools".
---

# /setup

Run once, on the first session (the §0 bootstrap routes here automatically). Goal:
get every tool the tutor uses working, with the learner logged in where needed, so
the experience is frictionless from then on. Be friendly and concrete — explain
each step in one line before doing it.

## Steps

1. **Welcome.** In 2–3 lines, say what AI-TUTOR is (a personal tutor for any
   subject that researches the field, builds a curriculum, and teaches + reviews
   you over time) and that setup is a one-time thing.

2. **Run the base installer.** Execute the repo's `setup.sh`:
   ```bash
   bash ./setup.sh
   ```
   It checks Python, installs the **NotebookLM** media CLI into `~/.notebooklm-venv`,
   and checks Node/npx for the browser tool. Report what succeeded and what didn't,
   plainly. The **core tutoring engine needs none of this** — it's all for the
   optional rich-media and live-docs features. Don't block onboarding if a tool is
   missing; just note it.

3. **Playwright browser tool (live docs/research).** It's declared in `.mcp.json`
   and loads via `npx` on first use — no install step. If `npx` was missing in
   step 2, tell the learner Node.js is optional but enables reading authoritative
   sources live; they can install it later.

4. **NotebookLM login (OPTIONAL — only if they want podcasts/videos/mind maps).**
   Ask: *"Do you want auto-generated audio/video/mind-map study materials? It needs
   a one-time Google login in a browser. (You can skip and add it later.)"*
   - If **no** → skip; record `media.enabled = false` (see step 6). The tutor works
     fully without it.
   - If **yes** → check and log in:
     ```bash
     NB="$HOME/.notebooklm-venv/bin/notebooklm"
     "$NB" doctor          # is auth already good?
     "$NB" login --browser chrome   # opens a browser ONCE; tell them to sign in + approve 2FA
     ```
     Tell the learner exactly what to do: a Chrome window opens → sign in to their
     Google account → approve any 2FA → the session saves automatically.

5. **Create the media notebook (only if media enabled & logged in).** Create one
   dedicated NotebookLM notebook to act as this repo's media factory, then store
   its ID so it's never hardcoded:
   ```bash
   "$NB" create "AI-TUTOR"        # or "AI-TUTOR — <subject>" after onboarding
   "$NB" list                      # capture the new notebook's id
   ```
   Save `media.notebook_title` and `media.notebook_id` into `progress/progress.json`
   (the `media` block). The subject's curriculum/logs get added as sources later by
   the teaching skills. If onboarding hasn't picked a subject yet, you may defer the
   create to the end of onboarding and just name it "AI-TUTOR" for now.

6. **Record setup state in `progress/progress.json`.** Ensure a `media` block exists:
   ```json
   "media": { "enabled": true|false, "notebook_title": "AI-TUTOR", "notebook_id": "" }
   ```
   Do NOT set `"initialized": true` here — that happens at the end of `/onboarding`.

7. **Hand off.** Tell the learner setup is done and immediately continue into
   **`/onboarding`** to pick what they'll learn. Never stop here.

Keep it light. If everything but media is ready, that's enough to start learning.
