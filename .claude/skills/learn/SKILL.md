---
name: learn
description: Teach the next roadmap topic (or a specific one) step by step, following the AI-TUTOR teaching loop. Use when the user runs /learn, says "teach me X", "continue", "next topic", or wants a new concept explained.
---

# /learn [topic]

`/learn` is the **single entry point** for a study day. It does not always teach
new material — it first runs the **Consolidation Gate** and may route you into a
review session instead. Just type `/learn` daily and trust the router.

> If `progress/progress.json` is missing/uninitialized, this is a fresh copy — run
> `/setup` then `/onboarding` first (CLAUDE.md §0), not the steps below.

## Step 0 — Run the Consolidation Gate (MANDATORY, before anything else)

Read `review/CONSOLIDATION-GATE.md` and follow it exactly:
1. Compute the signals (`overdue`, `due_today`, `weak_open`, consolidation ratio
   `C`, unconsolidated load `U`, `last_review_accuracy`) from `flashcards/deck.md`,
   `review/to-review.md`, and `progress.json` against today's date.
2. Apply the **decision ladder** (R0–R7, first match wins).
3. **Print the readout** (§4 of the gate doc) so the choice is visible and
   overridable.
4. Route:
   - **Decision = REVIEW** → run the **`/review`** procedure. When it finishes, if
     appetite remains and the gate would now pass, you may continue into new
     material.
   - **Decision = LEARN** → proceed to the teaching procedure below. If a handful
     of cards are due (R7), open with a quick retrieval warm-up of them first.

A topic argument (`/learn <topic>`) or "teach me X" / "new" is rule **R0** — honor
it, but still print a one-line warning if review debt exists.

## Procedure (per concept, from CLAUDE.md §3)
1. **WHY** — the problem this concept solves (1–3 sentences, motivate it).
2. **EXPLAIN** — numbered steps; define every term before use; no jargon debt.
   Use one everyday analogy max, then plain mechanism.
3. **SHOW** — put a minimal concrete example in `workspace/stage-XX/…` and make it
   real (run the code, work the problem, write the sentence — whatever the subject
   allows). Use the Playwright MCP to open authoritative sources when helpful.
4. **CHECK** — ask a quick question or "predict the result" before revealing it.
   If wrong, diagnose and re-teach; do not move on.
5. **PRACTICE** — have the learner produce something themselves, unaided.
6. **REFLECT** — a short Feynman prompt: "explain that back simply."

Cover 1–3 concepts per session — depth over breadth. Stop when comprehension dips;
better to end solid than rushed.

## Close out (mandatory — CLAUDE.md §4 end-of-session)
- Append today's `logs/sessions/<date>-NN.md`; update `logs/INDEX.md`.
- Create ≤6 flashcards in `flashcards/deck.md`; set due dates; refresh
  `flashcards/review-queue.md`.
- Mark topic status in the stage file; update `progress.json` (mastery, stats,
  current_stage); re-render `DASHBOARD.md` and `skill-tree.md`.
- Add any weak spots to `review/to-review.md`.
- If this session **completed** a topic, build its media class kit (CLAUDE.md §9b).
- Give a 5-line recap: taught / practiced / next time.
- **Always end with the "What next?" menu (CLAUDE.md §13).** Never go silent.
