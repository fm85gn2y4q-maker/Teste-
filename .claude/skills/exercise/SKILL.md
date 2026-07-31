---
name: exercise
description: Generate a practice exercise for the current topic, have the learner solve it in the workspace, then review the solution for correctness, depth, clarity, and good form. Use when the user runs /exercise, says "give me a problem", "let me practice", or "I want to try something".
---

# /exercise [topic]

Hands-on practice. Default = current stage/topic; an argument can target a specific
one. An "exercise" means whatever active practice fits the subject — a coding
problem, a math problem set, a paragraph to write, a passage to translate, a chord
progression to build, an argument to construct.

## Procedure
1. Generate a problem from `exercises/TEMPLATE.md` at the right rung of the ladder
   (**intro** guided → **core** unaided → **stretch** combines earlier topics).
   Include a clear spec, a worked example, edge cases / common pitfalls, and a
   target standard for "good". Save it to `exercises/<title>.md`.
2. Have the learner produce the solution in `workspace/` and, where possible, make
   it real (run the code, check the answer, read it aloud). Encourage attempting
   before hints; give hints in escalating steps, not the answer.
3. Review the submitted solution on four axes adapted to the subject:
   **correctness** (does it actually work / is it right?), **depth/efficiency**
   (does it meet the target standard?), **clarity** (structure, naming, expression),
   and **good form** (is it idiomatic/conventional for the field?). Be specific.
4. If wrong, guide them to find the flaw (don't just fix it). Iterate to a correct,
   clean solution.
5. Move the problem + final solution + your review into `exercises/solved/`.
   Increment `exercises_solved` in `progress.json`; log it; make a flashcard if a
   reusable insight emerged. Add weak spots to `review/to-review.md`.
6. **Always end with the "What next?" menu (CLAUDE.md §13).** Options: try a harder
   exercise, learn the next concept, quiz me, Feynman, make materials. Never go
   silent after reviewing the solution.
