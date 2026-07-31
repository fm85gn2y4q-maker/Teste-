# NotebookLM — Browser fallback (Playwright)

> ⚠️ **Fallback only.** The primary path is the `notebooklm` CLI (see `SKILL.md`).
> Use these browser steps only when the CLI doesn't cover a feature. For
> list/create/ask/audio, always prefer the CLI.

All steps use Playwright MCP. Always run `browser_snapshot` before clicking to get
current element refs (the UI changes IDs on every load).

## 0. Session setup

1. `browser_navigate` → `https://notebooklm.google.com`
2. `browser_snapshot` — confirm you're logged in.
   - If a Google login screen appears, authenticate with the user's Google
     account (they must approve any 2FA prompt on their phone).
3. Close any promo banner/popup (Escape or the X) before interacting.

## 1. Create a notebook

1. Click **"Create new"** / **"+ New notebook"**.
2. The "Add source" modal opens — pick a source type (see workflow 2).
3. After the first source finishes processing, the notebook exists.
4. Rename: click the title (top-left) → type the new name.
5. Note the ID in the URL (`/notebook/<ID>`) if you'll reuse it.

## 2. Add a source

Click **"Add source"** (or the "+" in the Sources panel). Types:

- **PDF / file:** "Upload" → `browser_file_upload` with the local path.
- **Google Drive:** "Google Docs" / "Google Slides" → pick it in the picker.
- **URL / site:** "Website" → paste URL → "Insert".
- **YouTube:** "YouTube" → paste link → "Insert".
- **Pasted text:** "Copied text" / "Paste text" → paste → "Insert".

After inserting: `browser_wait_for` until the source shows in the list without a
processing spinner. Large sources can take 30s–2min.

## 3. Ask a question

1. Make sure you're on the notebook page (`/notebook/<ID>`).
2. `browser_type` into the chat box (bottom center) with the question.
3. Submit (Enter or the send button).
4. `browser_wait_for` until the response finishes streaming.
5. `browser_snapshot` and extract the answer text + citations.

## 4. Audio Overview (podcast)

1. Open the **Studio** panel (right side).
2. Click **"Audio Overview"** → **"Generate"** (optionally "Customize" first for
   focus/language).
3. **Poll:** it's asynchronous (3–15 min). The button shows a "Generating…"
   state. `browser_wait_for time:25` + re-`browser_snapshot` repeatedly until the
   finished card appears (title + play/"Open" + a "More"/⋮ menu).
4. Download: the audio card → **"More" (⋮)** → **"Download"**. File is **.m4a**.
   Move it to where the user expects.

## 5. Briefing doc / Study guide / Mind map / etc.

1. **Studio** panel → choose the artifact type.
2. Wait for generation (`browser_wait_for`).
3. The result appears in Notes — open and copy, or "Convert to source".

## 6. Open an existing notebook

`browser_navigate` → `https://notebooklm.google.com/notebook/<ID>`, then
`browser_snapshot` to confirm the sources loaded.

## Troubleshooting

- **Stale refs / UI frozen:** re-run `browser_snapshot` (refs expire).
- **Button missing:** a sidebar may be collapsed — find the expand icon.
- **Logged out:** sign in again; most actions fail silently when logged out.
- **Audio "stuck":** wait longer — large notebooks can exceed 10 min; don't
  regenerate too early.
