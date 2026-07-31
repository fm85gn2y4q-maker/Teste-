---
name: feynman
description: Run the Feynman technique — have the learner explain a concept in plain language, then deliver a gap analysis and re-teach only the gaps. Use when the user runs /feynman, says "let me explain X", "check my understanding of X", or after learning a tricky concept.
---

# /feynman [topic]

Force active recall and expose hidden gaps. Default topic = the most recent concept
learned; an argument can pick any mastered/learning topic.

## Procedure
1. Prompt: "Explain *<topic>* to a smart 12-year-old, in your own words, with a
   concrete analogy. Define any technical term you use."
2. **Stay silent** while they explain. Do not interrupt or hint.
3. Deliver a gap analysis (use `feynman/TEMPLATE.md`): what was ✅ correct,
   🟡 vague/hand-waved, 🔴 wrong or missing, and any ❓ undefined terms used.
4. **Re-teach only the gaps** — step by step, then ask them to redo just that part.
5. Save the attempt + analysis to `feynman/<topic>-<date>.md`; increment
   `feynman_attempts` in `progress.json`.
6. If gaps were serious: add the topic to `review/to-review.md`, make targeted
   flashcards, and consider downgrading its mastery in `progress.json`.

The goal isn't a perfect explanation — it's surfacing what they only *thought* they
understood. Be honest and specific about the gaps. End with the "What next?" menu
(CLAUDE.md §13).
