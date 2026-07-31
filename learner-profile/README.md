# 🧠 Learner Profile — the living model of *how the learner learns*

This folder is AI-TUTOR's memory of the **learner as a person**, separate from
`progress/` (which tracks *what* has been learned). Here we track *how* they learn:
behaviors, preferences, posture under challenge, pace, motivation, and the recurring
mistakes worth anticipating. The goal is that every future session adapts to the
real human, not a generic beginner.

## Files
| File | What it is | Update cadence |
|---|---|---|
| `PROFILE.md` | The **canonical living model** — synthesized, dimension-by-dimension, each with an **actionable teaching implication**. **MUST be read at every session start** (enforced in `CLAUDE.md` §4 / §4a). Seeded at `/onboarding`. | End of every session (and whenever a clear pattern emerges) |
| `observations.md` | Append-only **raw log** of dated, concrete behaviors ("today the learner did X"). The evidence pool that `PROFILE.md` is distilled from. | Every session — add 1–4 bullets |

## How to use it (for the tutor)
1. **Start of session:** read `PROFILE.md`. Let it shape tone, pace, analogy choice,
   challenge level, and which misconceptions to pre-empt.
2. **During:** notice behaviors against the dimensions below. Jot them mentally.
3. **End of session:** append concrete bullets to `observations.md`; if a stable
   pattern has formed, promote it into the matching `PROFILE.md` dimension and bump
   "Last updated". Keep `PROFILE.md` **synthesized and short** — move detail to
   observations, keep conclusions in the profile.

## The framework (why these dimensions) — grounded in learning science
The dimensions in `PROFILE.md` come from three well-established bodies of research:

- **Self-Regulated Learning (SRL):** learning is driven by the interplay of
  *motivation, metacognition, and learning strategies* across plan → perform →
  reflect phases; a key skill is **calibration** (how well "I know this" matches
  reality). (Zimmerman; Cambridge Handbook of the Learning Sciences, ch. 5.)
- **Engagement & Grit:** engagement has *behavioral, cognitive, and emotional*
  facets; **grit/persistence** predicts long-run success more than raw aptitude, and
  links to a **mastery** (vs performance) goal orientation. (Duckworth; Fredricks et
  al.)
- **Affective tutoring & productive struggle:** good tutors track
  **confusion/frustration** and adapt, because a *moderate* level of difficulty — the
  **zone of proximal development**, the ~85%-success "desirable difficulty" zone —
  drives the best learning, while overwhelm shuts it down. (D'Mello & Graesser;
  Vygotsky; Bjork; VanLehn.)

## Sources
- [Metacognition & Self-Regulated Learning — Cambridge Handbook of the Learning Sciences, ch.5](https://www.cambridge.org/core/books/abs/cambridge-handbook-of-the-learning-sciences/metacognition-and-selfregulated-learning/D974BC55B2728E18D3F2A2E1B144709C)
- [TEAL Center Fact Sheet No.3: Self-Regulated Learning (US Dept. of Education)](https://lincs.ed.gov/federal-initiatives/teal/guide/selfregulated)
- [Grit, affect balance & learning engagement](https://pmc.ncbi.nlm.nih.gov/articles/PMC10968423/)
- [More confusion and frustration, better learning (erroneous examples)](https://www.cs.cmu.edu/~bmclaren/pubs/RicheyEtAl-MoreConfusionAndFrustrationBetterLearningImpactOfErrEx-CompAndEd2019.pdf)
- [A comprehensive review of AI-based Intelligent Tutoring Systems](https://arxiv.org/html/2507.18882v1)
