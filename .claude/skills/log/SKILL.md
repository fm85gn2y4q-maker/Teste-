---
name: log
description: Write or view the session log — capture what was taught, practiced, and flagged this session, and append to the session index. Use when the user runs /log, says "log this session", "what did we cover", or "show my history".
---

# /log

Maintain the learning journal.

## Write (default at session end, or on demand)
1. Create/update `logs/sessions/<YYYY-MM-DD>-NN.md` from `logs/sessions/TEMPLATE.md`
   (NN = the day's session number).
2. Fill in: stage/topic, duration, what was taught (numbered, step by step), work
   produced (with `workspace/` paths), comprehension checks and outcomes, practice
   attempted, weak spots, flashcard ids created, mastery updates, and the plan for
   next time.
3. Add a row to `logs/INDEX.md` (newest first).
4. Ensure cross-updates happened: `progress.json` stats, `review/to-review.md`,
   `flashcards/deck.md`. The log is the audit trail tying it all together.

## View
If the user wants history, summarize from `logs/INDEX.md` and open specific logs.
Offer a quick "since last week" recap: concepts learned, cards added, quizzes,
exercises solved, and where momentum is strong or stalling.
