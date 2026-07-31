---
name: review
description: Run the spaced-repetition review — quiz the learner on flashcards due today, grade with the SM-2-lite scheduler, and revisit flagged weak spots. Use when the user runs /review, says "review", "do my cards", "what's due", or starts a study session.
---

# /review

Run due reviews and revisit weak spots. `/learn` auto-routes here via the
**Consolidation Gate** (`review/CONSOLIDATION-GATE.md`) whenever there's review
debt; you can also invoke `/review` directly to force a revision session.

## Procedure
1. Read `flashcards/review-queue.md` (and recompute from `deck.md` against today's
   date) → the cards due today/overdue. Also read `review/to-review.md`.
2. For each due card: present a question, let the learner answer, then reveal the
   **back**. **Do NOT read the stored `front` verbatim** — reword or re-angle it so
   it probes the same `back`/`topic` in a fresh surface form (CLAUDE.md §7a,
   "variation on recall"). Vary scenario/example/type across reviews. **You** assign
   the grade (**Again / Hard / Good / Easy**) from the answer they gave, judging the
   underlying fact not the wording — never ask them how hard it felt (CLAUDE.md §6
   rubric). State the grade + a one-line reason; the learner may override.
   - **Merge & escalate (CLAUDE.md §7b — REQUIRED, not optional).** Don't drill
     cards one-by-one in isolation. Fold related due cards into **compound,
     connective questions**, and **escalate difficulty as the learner answers
     correctly** (chain to another concept, ask "why", transfer to a new scenario).
     Drop back to a plain single-concept question only when a clear misunderstanding
     surfaces. **Cover every due card's fact** — merging changes delivery, never
     coverage; track which cards each compound question covers and grade each
     underlying card individually (§6). Strong synthesis is a bonus toward Easy.
3. Apply the SM-2-lite scheduler (CLAUDE.md §6): update `interval`, `ease`, `reps`,
   `lapses`, and `due` for each card in `flashcards/deck.md`.
   **Persist incrementally (CLAUDE.md §6a):** write each card's new fields to
   `deck.md` the moment you grade it — *before* presenting the next question — so a
   half-finished review is still banked. Don't batch these writes to the end.
   **Re-queue rule (CLAUDE.md §12):** any card graded Again or Hard is immediately
   appended to the end of this session's queue for a second attempt. SM-2 scheduling
   uses the first-attempt grade only; the re-queue pass is a correction pass
   (ungraded). If still missed on re-queue, add to `review/to-review.md` and briefly
   re-explain before moving on.
4. For any **Again**/weak card, briefly re-teach the underlying idea — don't just
   flip the card. If shaky, ensure it's in `review/to-review.md`.
5. Work through `review/to-review.md` weak spots: re-explain, verify with a quick
   check, mark `re-taught`/`verified` (delete verified rows).
6. Regenerate `flashcards/review-queue.md`; update `progress.json` stats
   (`flashcards_due`, streak, last_session_date); re-render `DASHBOARD.md`.
7. **Feed the gate (required).** Compute
   `accuracy = (cards graded Good or Easy on first attempt) / (cards reviewed)`
   and recompute `consolidated` / `consolidation_ratio` (cards with `reps >= 2` and
   not overdue ÷ total). Write `last_review_accuracy`, `last_review_date`,
   `cards_consolidated`, `consolidation_ratio` into `progress.json → review_tracking`.
8. Log the review in today's session log (or create one).

Keep momentum — reviews should be fast. Re-teach only where a miss reveals a gap.

## After close-out — always present the "What next?" menu (CLAUDE.md §13)
Never go silent. Present forward options, e.g.: Keep learning (next concept),
Practice, Quiz me, Make materials, Another review pass, Feynman. The learner
decides when the session ends — not the command.
