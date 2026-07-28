# Daily plan summary — 2026-07-27

<!-- Auto-aggregated by tools/aggregate-plans.py from each tracked repo's daily-plan.md. Overwritten on every run. -->

## At a glance

<!-- Fresh plans first, then by priority band (P1 = highest, set in repos.yml). Idle = days since the newest commit. -->

| Repo | Pri | Plan | Focus | Idle |
| --- | --- | --- | --- | --- |
| [second-brain-devkit](https://github.com/cornjacket/second-brain-devkit) | P1 | 2026-07-27 | **Build #39 — embed-excluded block:** marker (reuse… | today |
| [create-project-system](https://github.com/cornjacket/create-project-system) | P1 | 2026-07-27 | **Task 07 — first real rollout: generate into… | today |
| [second-brain-test](https://github.com/cornjacket/second-brain-test) | P2 | 2026-07-27 | **Prototype #39 — the embed-excluded block — HERE by hand:** a… | today |
| [create-ai-builder](https://github.com/cornjacket/create-ai-builder) | P2 | 2026-07-27 | **Begin target composition… | today |
| [captains-log](https://github.com/cornjacket/captains-log) | P2 | 2026-07-27 | **Day 1 of the Kaggle intensive — *Introduction to Agents*:**… | today |
| [customer-req-responder](https://github.com/cornjacket/customer-req-responder) | P3 | **STALE** 2026-05-29 | — | today |

## [second-brain-devkit](https://github.com/cornjacket/second-brain-devkit) — plan for 2026-07-27

**What this repo is (for a newcomer):** `second-brain-devkit` is a *generator*. It builds a personal
"second brain" — a plain-Markdown notes vault a human edits in Obsidian, plus a local SQLite
semantic-search index an AI reads — and ships it as a ready-to-run repo. Every change goes
prototype → vendor → one command, `python3 tools/ci.py` (14 automated gates).

**Last implemented:** #38 (a permission-denied source folder is no longer reported as empty) shipped
2026-07-20. #39 — the *embed-excluded block* (strip decorative ASCII from a note's embedding + content
hash) — is filed but not yet built; it is the next build.

**Focus / plan:**
- **Build #39 — embed-excluded block:** marker (reuse `scripts/marked_block.py`) strips a
  decorative region from `canonical_body()` before embedding **and** from the content hash; prototype
  in golden → `vendor_golden.py` → `build_template.py` → `tools/ci.py` green + a new strip/hash gate.
- Parked (human): `add_pdf_guided` CLI form pass; Suite A Desktop; glossary Obsidian hand-test.

```
 build ▶ #39 embed-excluded block
   golden prototype ──▶ vendor_golden.py ──▶ build_template.py ──▶ tools/ci.py (+ strip/hash gate)
   guardrail: strip the decorative region from BOTH the embedding and the content hash
```

## [create-project-system](https://github.com/cornjacket/create-project-system) — plan for 2026-07-27

**What this repo is (for a newcomer):** A Cookiecutter-style *generator* that
installs a Markdown-based project-management workspace — a task tracker
(`tasks/`) plus periodic status reports (`status/`) — into any target repo at a
caller-chosen mount, non-destructively and re-runnably.

**Last implemented:** Option B — added the `--with-status` layer so the
generator reproduces the whole `project/` workspace (tasks + status), not just
the tasks pillar; renamed the repo `create-task-system` → `create-project-system`
to match. Self-test at 61 assertions green; new `project` golden fixture pins the
container layout.

**Focus / plan:**

- **Task 07 — first real rollout: generate into `second-brain/`.** Run at repo
  root (siblings of `vault/`, never inside it):
  `--tasks-dir project/tasks --epic main --with-status --with-skill`.
- Smoke-test the emitted scripts from the second-brain root; **review the diff
  before committing** anything into that live repo.
- Confirm no overlap with second-brain's own `install_skill.py` / `.claude/`.
- Low-priority cleanup: update the 3 second-brain notes that still cite the old
  `create-task-system` name.
- If 07 lands cleanly, tee up **task 08** (captains-log).

```
today ─┐
       ▼
   [07] second-brain  ──►  [08] captains-log  ──►  [09] task-free ai-builder
   generate @ root         (next)                  (closes the loop)
   project/{tasks,status}
```

## [second-brain-test](https://github.com/cornjacket/second-brain-test) — plan for 2026-07-27

**What this repo is (for a newcomer):** `second-brain-test` is the *golden reference* for the devkit
next door — a hand-built, known-good copy of a generated brain. Features are prototyped **here by
hand first**; once they behave, they are vendored into the devkit as its regression baseline. The
workbench, not the product.

**Last implemented:** #38 (permission-denied ≠ empty) prototyped and vendored; the golden is clean,
with no mid-prototype work parked.

**Focus / plan:**
- **Prototype #39 — the embed-excluded block — HERE by hand:** a marker that keeps decorative text
  (ASCII diagrams) out of `canonical_body()` for both embedding and the content hash.
- Prove the invariant: editing the marked region must **not** re-embed or flag the vector stale.
- Then hand it to the devkit loop: `vendor_golden.py` → `build_template.py` → `tools/ci.py` green.
- Keep the search backend on `test` so the vendored snapshot stays byte-for-byte stable.

```
 workbench: prototype #39 by hand → vendor into the devkit
   7/21 ▶ marked decorative block: strip from embed + hash · prove edit-doesn't-re-embed
   guardrail: backend = test; prototype → vendor → devkit CI stays green
```

## [create-ai-builder](https://github.com/cornjacket/create-ai-builder) — plan for 2026-07-27

**What this repo is (for a newcomer):** `create-ai-builder` is a generator that
installs an AI-agent **build pipeline** (an orchestrator plus ARCHITECT /
IMPLEMENTOR / TESTER role agents) into a target platform repo. The pipeline is
driven by a Markdown task system, so an installed ai-builder turns tracked tasks
into shipped code.

**Last implemented:** the `task-system-generator-migration` branch **merged to
main** (PR #4) — the task subsystem now rides on the `create-project-system`
generator instead of the 25 hand-built scripts. The three create-ai-builder-owned
follow-ups were then **re-homed into this repo's own tracker** (dogfooding the
migrated tooling): `29297c-relocate-pipeline-scripts` (task-tooling, MED),
`59ea60-repo-name-rename-audit` (workspace-mgmt, LOW), and
`15d940-target-setup-uses-generator-for-tasks` (workspace-mgmt, MED — renamed from
the old `target-composition-delegate-to-generate`).

**Focus / plan:**

- **Begin target composition — `15d940-target-setup-uses-generator-for-tasks`.**
  Make `target/setup-project.sh` **delegate** the task layer to a pinned
  `create-project-system` `generate.sh` instead of copying create-ai-builder's own
  scripts. Start the task (move to `in-progress`, worktree class `workspace-mgmt`),
  describe subtasks, and align before implementing.
- Design the pin: which `create-project-system` ref to pin to, and how the target
  setup invokes `generate.sh` (`--tasks-dir` / `--epic` / `--with-status`).
- Next in the re-homed queue (not today): `29297c-relocate-pipeline-scripts`
  (MED), then `59ea60-repo-name-rename-audit` (LOW).

```
PR #4 merged ─▶ follow-ups re-homed ─▶ [15d940] target composition (today)
                                          │  setup-project.sh delegates to
                                          │  a pinned create-project-system generate.sh
                                          ▼
                            then ▶ 29297c relocate pipeline scripts ▶ 59ea60 rename audit
```

## [captains-log](https://github.com/cornjacket/captains-log) — plan for 2026-07-27

**What this repo is (for a newcomer):** `captains-log` is a personal engineering log — learning
notes, design decisions, and roadmap thinking captured as dated entries, tracked by project-status so
the reasoning behind the portfolio is recorded alongside the code.

**Last implemented:** closed the **task-devkit** roadmap task as superseded — `create-project-system`
shipped the generator, and every remaining strand re-homed to the repo that owns it (2026-07-27) —
[task](project/tasks/main/complete/bb5b51-task-devkit-pluggable-subsystems/).

**Focus / plan:**
- **Day 1 of the Kaggle intensive — *Introduction to Agents*:** read the whitepaper front to back and
  work the day's material. Task: [`project/tasks/main/in-progress/5c0d5b-kaggle-5-day-ai-agents-intensive/`](project/tasks/main/in-progress/5c0d5b-kaggle-5-day-ai-agents-intensive/).

Carry-forwards cleared off this plan today: the **Pi harness** and **Claude Desktop custom
instructions** items became backlog tasks
([`7d5719`](project/tasks/main/backlog/7d5719-pi-coding-harness-end-to-end/),
[`cf94ee`](project/tasks/main/backlog/cf94ee-claude-desktop-without-per-prompt-reminders/)) rather
than rolling forward invisibly; **Agent Quality** and **The New SDLC With Vibe Coding** moved onto
the Kaggle task that owns them; **task-devkit** closed as superseded, with its one unowned strand
filed in `create-project-system` as task 22.

Reference links now live on the task that addresses each item, not here — a link on a daily plan is
gone tomorrow.

```
morning ──────────── midday ──────────── afternoon ────────── evening
 [Kaggle Day 1:      [Day 1 cont. —      [Day 1 material     [wrap up /
  Introduction to     finish the day's    cont.]              capture notes]
  Agents] read        material]
```

## [customer-req-responder](https://github.com/cornjacket/customer-req-responder) — STALE (last plan: 2026-05-29)

Decide the workflow methodology for this project going forward. Researched the field
(GSD, Superpowers, Claude Skills, chub, Everything Claude Code, paperclip, RooFlow, Open Design)
via parallel subagents. Decision: **switch to Superpowers** for this project (single framework,
not stacked with GSD). Rationale: small greenfield TS/Node pipeline is an ideal TDD fit, fresh
learning ground that feeds the homegrown ai-builder framework, and low-risk to trial at this size.
Two known gaps to own deliberately: (a) no LLM/eval phase like GSD's AI-SPEC / eval-review — will
hand-spec the eval or author an own eval skill; (b) draft-quality is non-deterministic, so TDD
covers the plumbing while a separate Gemini-as-judge eval loop covers generation. The log.md /
daily-plan.md / ai-project-status discipline is framework-agnostic and stays. Next: set up
Superpowers and start brainstorm on the 6 blocking open questions toward SPEC.md.

```
  workflow decision                    spec work (via Superpowers)
  ┌──────────────────────────┐        ┌─────────────────────────────┐
  │ research candidates   ok │        │ /superpowers:brainstorm  --> │
  │ score vs project      ok │   -->  │ answer blocking Qs           │ --> plan
  │ DECISION: Superpowers ok │        │ (2,4,5,7,9,11)               │
  └──────────────────────────┘        └─────────────────────────────┘
   replace GSD, keep ai-builder log     own the eval loop separately
```
