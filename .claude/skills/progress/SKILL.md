---
name: progress
description: Render the learning dashboard and skill tree from progress.json, showing stage bars, stats, due reviews, and what to do next. Use when the user runs /progress, says "how am I doing", "show my progress", "where am I", or "the dashboard".
---

# /progress

Show the learner where they stand, at a glance.

## Procedure
1. Read `progress/progress.json` (source of truth) and `flashcards/review-queue.md`.
2. Re-render `progress/DASHBOARD.md`:
   - Header: name, subject, goal, started, last session, streak.
   - Overall journey bar + phase rollups.
   - Per-stage 20-cell bars (each cell = 5%), status emoji, `(done/total)` topics.
   - Stats table (sessions, minutes, concepts, cards total/due, exercises, quizzes,
     feynman).
   - "Up next" line: the concrete next action.
3. Re-render `progress/skill-tree.md` to match current statuses.
4. Display the dashboard and call out: what's due for review, the current focus, and
   the nearest milestone.

Read-only on the curriculum — this command only reflects state, it doesn't teach.
Keep bars aligned and the output skimmable. End with the "What next?" menu
(CLAUDE.md §13).
