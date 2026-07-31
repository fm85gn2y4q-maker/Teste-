# 🎓 AI-TUTOR — a personal tutor for *anything*, inside Claude Code

AI-TUTOR is a self-contained, AI-powered private tutor that takes one learner from
**absolute beginner to expert in any subject they choose** — programming, a
foreign language, statistics, music theory, history, law, cooking, anything.

You don't configure it by hand. You open the folder, say what you want to learn,
and it **researches the field, builds a full curriculum**, and then teaches you
day by day — with rigorous step-by-step lessons, spaced-repetition flashcards,
the Feynman technique, exercises, graded quizzes, a visual progress dashboard,
and auto-generated podcasts / videos / mind maps for every topic you finish.

It runs inside [Claude Code](https://claude.com/claude-code) and remembers
everything between sessions in plain files you own.

---

## ✨ What makes it different

- **Teaches any subject.** The curriculum isn't hard-coded — it's generated for
  *your* goal during a one-time setup.
- **Adapts to how *you* learn.** It keeps a living `learner-profile/` (pace,
  cognitive style, grit, recurring mistakes) and adjusts every lesson to it.
- **Never lets you forget.** A deterministic spaced-repetition engine (SM-2-lite)
  schedules reviews; a **Consolidation Gate** decides each day whether you should
  learn something new or shore up what's shaky.
- **Active, not passive.** You do ~half the talking — predicting, solving,
  explaining ideas back. Wrong answers stop the lesson and get re-taught.
- **Rich media on demand.** Stuck on something? It can spin up a visual HTML
  explainer, an audio "podcast," a video overview, or a mind map (via NotebookLM).
- **Everything is yours.** Progress, notes, flashcards, and logs are all local
  Markdown/JSON files — portable, inspectable, and version-controllable.

---

## 🚀 Quick start

1. **Install [Claude Code](https://claude.com/claude-code)** and unzip this folder.
2. **Open the folder in Claude Code** (`cd` into it, run `claude`).
3. **Say hello.** On the very first run it auto-detects a fresh copy and will:
   - run **`/setup`** — install and verify its tools (it will ask you to log in
     where needed), then
   - run **`/onboarding`** — ask *what you want to learn* and your goal, research
     that field, run a short placement diagnostic so you skip what you already
     know, and generate your personal curriculum.
4. **Each day after that, just run `/learn`** — it figures out whether to teach
   something new or run your due reviews. Check `/progress` any time.

That's it. No manual configuration.

---

## 🧭 Commands

| Command | What it does |
|---|---|
| `/setup` | First-run install & verify tools (NotebookLM, Playwright, media) |
| `/onboarding` | Capture your goal + subject, research it, build your curriculum |
| `/learn [topic]` | The daily entry point — teaches next topic *or* routes to review |
| `/review` | Run flashcards due today + revisit flagged weak spots |
| `/flashcards [add\|due\|list]` | Manage the spaced-repetition deck |
| `/quiz [topic]` | Take a graded assessment (stage gate at ≥80%) |
| `/feynman [topic]` | Explain a concept back; get a gap analysis |
| `/exercise [topic]` | Get a practice problem and have your solution reviewed |
| `/progress` | Render the progress dashboard + skill tree |
| `/log` | Write or view the session log |

---

## 🗂️ How it's organized

```
curriculum/     ROADMAP.md + per-stage files (generated for your subject)
progress/       progress.json (source of truth) + DASHBOARD + skill-tree
logs/           one dated log per session + INDEX
flashcards/     deck.md + due review-queue (SM-2-lite spaced repetition)
feynman/        explain-it-back attempts and gap analyses
exercises/      problems, with solutions in exercises/solved/
assessments/    quizzes/tests and scores
review/         to-review.md (weak spots) + the Consolidation Gate rules
learner-profile/ the living model of *how you* learn (read every session)
materials/      per-topic "class kits": podcast + video + mind map
visuals/        on-the-fly HTML explainers when text isn't landing
workspace/      scratch space where you actually do the work
.claude/skills/ the slash commands above
```

---

## 🔧 Requirements

- **Claude Code.** Everything runs through it.
- **Python 3.10+** — used to install the NotebookLM media tool (`/setup` handles
  the rest). Get it from [python.org](https://www.python.org/downloads/) or
  `brew install python`.
- **A Google account** — only if you want the optional audio/video/mind-map media
  (NotebookLM). You log in once, in a browser, when `/setup` asks. Everything else
  works without it.
- **Node.js** — for the Playwright browser tool (live docs/research); Claude Code
  fetches it on first use via `npx`.

The media features are **optional**. If you skip the Google login, you still get
the full tutoring engine; you just won't get auto-generated podcasts/videos.

---

## 🔒 Privacy

This is a clean, shareable template. It ships with **no personal data, no
credentials, and no API keys**. Your learning data (profile, progress, notes) is
created locally as you use it and never leaves your machine unless *you* share it.
The optional NotebookLM login is stored by Google's own tooling under your home
directory, not inside this folder.

---

## 🌱 Make it your own / track it in Git

To version your learning journey:
```bash
git init && git add -A && git commit -m "Start my AI-TUTOR journey"
```
If you share *your* copy afterward, remember it will then contain your personal
progress and notes — share the original template, not your filled-in copy, unless
you mean to.

---

## 📜 License

MIT — see [LICENSE](LICENSE). Free to use, share, and adapt.
