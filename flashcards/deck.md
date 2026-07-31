# 🃏 Flashcard Deck

Spaced-repetition deck (SM-2-lite — algorithm defined in `CLAUDE.md` §6). Add cards
via `/flashcards add` or automatically at the end of a learning session. Keep one
fact per card. Dates are ISO `YYYY-MM-DD`.

**Fields:** `id` · `front` (question) · `back` (answer) · `topic` · `stage` ·
`created` · `due` · `interval` (days) · `ease` · `reps` · `lapses`

> **`front` is a *seed*, not a script.** The fact tested = `back` + `topic`. At
> review time the question is **reworded/re-angled** so it probes the same fact
> without being the stored `front` verbatim — comprehension, not rote recognition.
> See CLAUDE.md §7a. The stored rows never change during review; only the spoken
> question varies.

| id | front | back | topic | stage | created | due | interval | ease | reps | lapses |
|----|-------|------|-------|-------|---------|-----|----------|------|------|--------|
<!-- Cards appear here as you learn. Example row shape:
| C0001 | <seed question> | <answer/fact> | <topic-slug> | 00 | 2026-01-01 | 2026-01-02 | 1 | 2.30 | 0 | 0 |
-->
