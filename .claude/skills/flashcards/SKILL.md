---
name: flashcards
description: Manage the spaced-repetition flashcard deck — add cards, list due cards, or browse the deck. Use when the user runs /flashcards, says "make a card", "add a flashcard", "show my cards", or "what's in my deck".
---

# /flashcards [add | due | list]

Manage `flashcards/deck.md` (schema & scheduler in CLAUDE.md §6–7).

## Subcommands
- **add** — create one or more cards. Each must be atomic (one fact), tagged with
  `topic` + `stage`. Prefer "why/how/when" and predict-the-result cards over rote
  recall; adapt card types to the subject. Assign `id` (next `Cxxxx`), `created` =
  today, `due` = tomorrow, `interval` = 1, `ease` = 2.30, `reps` = 0, `lapses` = 0.
  Append to the table and bump `flashcards_total` in `progress.json`.
- **due** — recompute and show cards due today/overdue from `deck.md`; refresh
  `flashcards/review-queue.md`. (To actually study them, use `/review`.)
- **list** — show the deck, optionally filtered by `stage` or `topic`, with each
  card's next due date and stats.

If no subcommand is given, infer intent from what the user said. Cap new cards at
~6 per learning session to avoid review debt.
