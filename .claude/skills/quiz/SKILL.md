---
name: quiz
description: Build and grade an assessment for a stage or topic, record the score, and gate stage completion on passing. Use when the user runs /quiz, says "test me", "give me a quiz", "am I ready to move on", or finishes a stage.
---

# /quiz [topic]

Assess mastery. Default scope = the current stage; an argument can narrow to a topic.

## Procedure
1. Build a 5–10 question quiz from `assessments/TEMPLATE.md`, mixing types suited to
   the subject: **recall**, **predict/produce a result**, **debug/critique**,
   **design/choose-and-justify**, **transfer**. Pull from what the stage covered
   (check its stage file + logs).
2. Present questions **one at a time** (CLAUDE.md §10). Let the learner answer before
   any hints. Do not lead them.
3. Grade **strictly**. For every miss, explain the correct reasoning fully — a quiz
   is also a teaching moment.
4. Compute the score. **Pass = ≥80%.**
5. Save to `assessments/Stage-NN-<date>.md`; increment `quizzes_taken` in
   `progress.json`. Log missed concepts into `review/to-review.md` and make targeted
   flashcards.
6. **Gate:** a stage is complete only when its quiz passes ≥80% **and** its milestone
   project/deliverable is built. On pass, mark the stage ✅, advance `current_stage`,
   and re-render `DASHBOARD.md` + `skill-tree.md`. On retry, point to the weak areas
   and suggest `/learn`/`/review` before re-testing.
7. **Always end with the "What next?" menu (CLAUDE.md §13).** On pass: start next
   stage, generate class materials for the completed stage, keep practicing, review
   weak cards. On fail: re-learn weak topics, review cards, retry quiz. Never go
   silent after grading.
