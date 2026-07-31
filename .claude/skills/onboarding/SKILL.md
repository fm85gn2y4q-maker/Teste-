---
name: onboarding
description: First-run setup for AI-TUTOR — capture the learner and the SUBJECT they want to learn, research that field, generate a full curriculum (ROADMAP + stages), run a placement diagnostic, and initialize all state. Use on first use, when progress.json is uninitialized, or when the user runs /onboarding or says "let's start", "set me up", "I want to learn X".
---

# /onboarding

Run this once, after `/setup`. This is where AI-TUTOR becomes a tutor for *this
learner's chosen subject*. It captures the goal, **researches the field**, and
**generates the entire curriculum** from scratch. Take it seriously — the quality
of everything downstream depends on this step.

## Step 1 — Meet the learner & capture the subject
Briefly explain how AI-TUTOR works (learn → review → track, adapting to them).
Then ask, **one question at a time** (CLAUDE.md §10):
1. Their **name** (what to call them).
2. **What they want to learn** — the subject. Encourage specificity ("Spanish for
   travel", "Python for data analysis", "music theory to write songs", "European
   history 1900–1945"). This is the most important answer.
3. Their **goal / why** — what success looks like ("hold a conversation", "pass an
   exam", "ship a product", "understand the news").
4. Their **starting point** — total beginner, some exposure, or returning.
5. **Weekly time budget** and **preferred language** for lessons (default: the
   language they're writing in).

## Step 2 — Confirm the teaching contract
Confirm the contract from `CLAUDE.md`: rigorous, step-by-step, nothing assumed
known, everyday analogies first, you do ~half the work, everything logged and
reviewed.

## Step 3 — Research the subject (DO NOT skip)
Before generating a curriculum, **research the field** so the roadmap reflects how
experts actually structure it — not a guess from memory:
- Use **WebSearch / WebFetch** and the **Playwright MCP** to read authoritative
  sources: standard syllabi, university course outlines, respected textbooks'
  tables of contents, official documentation, well-regarded learning roadmaps.
- If the **`deep-research`** skill is available, use it for a thorough,
  source-grounded survey of "how to learn <subject> from beginner to expert".
- Identify: the major **stages** (beginner → expert), the **prerequisite order**,
  the **core topics** per stage, common **milestone projects/deliverables**, and
  the typical **misconceptions** beginners hit.
- Briefly tell the learner what authoritative structure you found.

## Step 4 — Generate the curriculum
Write real files modeled on the conventions in `CLAUDE.md` §5 and §10:
1. **`curriculum/ROADMAP.md`** — a single linear path of ~6–14 stages, beginner →
   expert, each with a theme and status (start all ⬜). Include: how to use the
   roadmap, **milestone projects/deliverables** grouped into phases, and a
   **mastery rubric** (Recall → Apply → Predict/Produce → Transfer; a topic is
   ✅ mastered only at Transfer). Replace any programming-specific wording with the
   subject's natural equivalents.
2. **`curriculum/stages/NN-<slug>.md`** — one file per stage, from
   `curriculum/stages/TEMPLATE-stage.md`. Each lists: objectives, a checklist of
   topics (each `- [ ] ⬜ <topic>`), a **milestone**, and a **definition of done**
   (all topics mastered + stage quiz ≥80% + milestone built). Number stages `00..`.
   Aim for ~6–12 topics per stage.
Keep the breadth honest: enough to reach real expertise, not so much it's
unusable. The learner can always re-plan later.

## Step 5 — Placement diagnostic
Walk the roadmap stage by stage. For each, ask **1–3 sharp diagnostic questions**
(define-precisely, predict/produce, choose-and-justify), **one at a time**. Grade
honestly:
- Confident + correct + can *transfer* → mark topics ✅ mastered, skip.
- Partial/shaky → 🟡, keep in scope.
- Unknown → ⬜.
Stop deepening once you hit a stage they clearly cannot pass — that's their real
starting line. Don't over-credit; when unsure, keep it in scope.

## Step 6 — Seed initial state
1. **`progress/progress.json`** — set `learner` (name, subject, goal, background,
   preferred_language, weekly_time_budget, `started` = today), build the `stages`
   array from the generated roadmap (with placement statuses/mastery),
   `current_stage` = first non-mastered stage, zeroed `stats`, a `review_tracking`
   block, the `media` block from `/setup`, and **`"initialized": true`**.
2. **`learner-profile/PROFILE.md`** — seed it from what you observed during
   onboarding (name, goal, starting point, any early signals about pace/style).
   Keep it short and conclusion-level; it grows over time. Bump "Last updated".
3. **`learner-profile/observations.md`** — add a dated first entry.
4. **Seed retention cards** — for topics they tested out of, create a few
   flashcards in `flashcards/deck.md` to confirm long-term retention; refresh
   `flashcards/review-queue.md`.
5. Re-render `progress/DASHBOARD.md` and `progress/skill-tree.md`.
6. **First log** — create `logs/sessions/<today>-01.md` from the template and add a
   row to `logs/INDEX.md`.
7. If `/setup` deferred it, now create/rename the media notebook to
   "AI-TUTOR — <subject>" and store its id in `progress.json → media`.

## Step 7 — Point forward
Show the dashboard, name their placed starting point, and tell them to run
**`/learn`** to begin. End with the "What next?" menu (CLAUDE.md §13). Never stop
the session.

Keep it brisk but rigorous — the research and the diagnostic are the most valuable
parts.
