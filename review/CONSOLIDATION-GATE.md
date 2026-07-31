# 🚦 The Consolidation Gate — when to REVIEW vs. teach NEW

This is the single source of truth for how `/learn` decides, **before any teaching
happens**, whether this session should *consolidate what you already have* (review)
or *add new material* (teach). `/learn` and `/review` both run it.

The learner should be able to just type **`/learn`** every day and trust the router
to do the pedagogically correct thing: serve new content when the foundation is
solid, and switch to revision when too much is unconsolidated or slipping.

---

## 1. The research it's built on (why these rules)

This synthesizes well-established findings in learning science (named below); the
findings themselves are textbook and stable.

| Principle | Source (well-known) | What it tells the router |
|---|---|---|
| **Forgetting curve** — memory decays ~exponentially after learning | Ebbinghaus (1885) | A card past its due date is actively being forgotten → recovering it is urgent and gets harder the longer you wait. |
| **Spacing effect** — spread-out practice beats cramming | Cepeda et al. 2006 (meta-analysis) | Reviews should land *at* their due date, not early, not way late. Respect the schedule. |
| **Testing effect / retrieval practice** — recalling beats re-reading | Roediger & Karpicke 2006 | Reviewing = active recall of due cards, not re-explaining. Re-teach only on a miss. |
| **Spaced-repetition scheduling** toward a target retention | SM-2 (SuperMemo) · FSRS (desired retention ≈ 0.90) | "Due" means predicted retention has dropped to the target. Clearing due cards keeps real retention near the target. |
| **Desirable difficulty / the 85% Rule** — learning is fastest at ~85% success | Bjork & Bjork; Wilson et al. 2019 (*Nature Communications*) | If recent success rate falls below ~80–85%, you're past the productive-struggle zone → consolidate before adding load. |
| **Interleaving** — mixing old + new improves retention & discrimination | Rohrer & Taylor 2007 | Even a "new content" session opens with a short warm-up of a few due cards. |
| **Review debt (Leitner boxes)** | Leitner system | Overdue/lapsing cards pile into a debt that must be cleared first, or new learning sits on sand. |

**The one-line philosophy:** *new material is only safe to add when the prior layer
is consolidated.* The gate enforces that, numerically.

---

## 2. The signals it measures (all computable from this repo)

Compute these at session start. Today's date comes from the environment.

**From `flashcards/deck.md` (vs. today):**
- `overdue` — cards with `due` **<** today.
- `due_today` — cards with `due` **==** today.
- `due_total` = `overdue` + `due_today`.
- `total_cards` — all cards.
- `young` — cards with `reps < 2` (introduced but not yet survived a *spaced* recall
  → **not yet consolidated**).
- `consolidated` — cards with `reps >= 2` **and** not currently overdue.

**From `review/to-review.md`:**
- `weak_open` — rows whose status is `open` or `re-taught` (not yet `verified`).

**From `progress.json → review_tracking`:**
- `last_review_accuracy` — fraction graded **Good/Easy** (first try) in the most
  recent `/review`. `null` if never reviewed.
- `last_review_date`.

**Derived:**
- **Consolidation ratio** `C = consolidated / total_cards`
  → *"the fraction you are NOT still missing."* (`C = 1.0` if `total_cards == 0`.)
- **Unconsolidated load** `U = young + overdue`
  → *"the amount you did not consolidate yet."*

---

## 3. The decision ladder (first match wins)

Run top to bottom; the **first** rule that fires decides the session. Each rule
names itself in the readout so the choice is always explainable.

```
R0  OVERRIDE   user typed `/learn <topic>` or said "new"/"teach me X"
               → LEARN that topic. (Still print a one-line debt warning if
                 overdue >= 1 or weak_open >= 1.)

R1  COLD START total_cards == 0
               → LEARN. (Nothing to consolidate yet.)

R2  OVERDUE    overdue >= 1
               → REVIEW. Forgetting-curve debt is the highest-leverage action.

R3  WEAK SPOT  weak_open >= 1
               → REVIEW (targeted re-teach of those concepts first).

R4  ACCURACY   last_review_accuracy != null AND last_review_accuracy < 0.80
               → REVIEW. Below the desirable-difficulty floor; don't add load.

R5  LOAD       C < 0.67   (more than ~1/3 of all material is unconsolidated)
               → REVIEW. Too much wet cement to safely pour another layer.

R6  BIG DUE    due_today >= 8
               → REVIEW. A full due stack is a session's worth on its own.

R7  DEFAULT    none of the above
               → LEARN new. First interleave any `due_today` cards (1–7) as a
                 ~3–5 min retrieval warm-up, then teach.
```

### Same-day guard (never re-cram, NEVER suggest stopping)
Two overrides applied *before* routing the ladder's REVIEW outcomes:

- **Nothing actually due → don't force review.** If `due_total == 0`, there is
  nothing productive to review today (the spacing effect means re-testing
  not-yet-due cards teaches almost nothing). In that case **do not** let R3/R5 fire
  into a pointless same-day re-test — **default to LEARN** new material. Only run
  REVIEW if the learner explicitly asks for it.
- **A weak spot re-taught *today* is not fresh debt.** Rows in `to-review.md` whose
  status became `re-taught` earlier *today* are considered in-progress; they get
  re-verified at their card's next due date, not by cramming the same day.
- **Never propose ending the session** (CLAUDE.md §2 rule 11). The readout's only
  forward options are continue-learning or continue-reviewing. "Stop for today" is
  never offered.

### Thresholds & why these numbers
- **0.80 accuracy floor** — matches the repo's stage-pass bar (CLAUDE.md §11, quiz
  ≥80%) and sits just under the ~85% optimal-learning point, so the gate triggers
  *before* you fall deep into the struggle zone.
- **0.67 consolidation floor (≈ 2/3)** — lets you keep progressing while capping
  review debt at one-third of everything introduced.
- **8 due cards** — roughly one focused review sitting (~10–15 min); beyond it, fold
  the "new" plan into a review day.

Tune these here only — every skill reads this file.

---

## 4. The readout (print this at session start, every time)

```
🚦 Consolidation Gate
   Due / overdue ....... <due_total> (<overdue> overdue)
   Open weak spots ..... <weak_open>
   Consolidation ....... <C%>  (<consolidated>/<total_cards> cards firm)
   Unconsolidated load . <U>   (young <young> + overdue <overdue>)
   Last review accuracy  <last_review_accuracy or "—">
→ Decision: <REVIEW|LEARN> (<rule id>: <one-line reason>).
   (Type "new" to force new content, or "review" to force revision.)
```

Then proceed into `/review` or the `/learn` teaching loop accordingly.

---

## 5. How accuracy gets recorded (so R4 works next time)

At the **end of every `/review`**, compute
`accuracy = (cards graded Good or Easy on first attempt) / (cards reviewed)` and
write `last_review_accuracy` + `last_review_date` into `progress.json →
review_tracking`. Also recompute `consolidated` / `consolidation_ratio` there so the
next gate is instant and deterministic.
