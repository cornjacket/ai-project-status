# Task: Draft next-day daily-plans from each repo's task state (human-reviewed, never auto-pushed)

- **Created:** 2026-07-27
- **Status:** PLANNED — not yet started. Design captured here for a later build pass.
- **Owner:** David Taylor
- **Scope decision:** DRAFT-ONLY. The tool **generates candidate `daily-plan.md`
  files for human review and never pushes** — approval and pushing are always the
  human's, always out of band. (See Decisions.)

## Goal

Give the umbrella (cross-repo) operator one command that regenerates **draft**
`daily-plan.md` files for the next day across every locally-checked-out tracked
repo, so the human reviews a batch of proposed plans instead of hand-visiting each
repo. The command fans out one `claude -p` **per repo, rooted in that repo's
checkout**, so the repo's own `CLAUDE.md`, skills, and task-system load naturally —
the context the umbrella session structurally lacks.

This is the *generate* side of the forward-looking loop. Its complement is the
*nudge* side already designed in
[`2026-06-29-daily-plan-reminder.md`](2026-06-29-daily-plan-reminder.md): that task
notifies when a plan is missing/stale; this task drafts the replacement. Together:
**evening reminder → human curates tasks → this tool drafts plans → human reviews
& pushes.**

## Core principle — the plan is *read* from task state, not invented

A daily-plan encodes **intent**, and intent is the human's, not the agent's. The
resolution (operator's decision): **the human expresses intent by curating each
repo's task system; the agent derives tomorrow's plan by inspecting that current
task state** (+ recent git log). The agent is a *reader* of human-encoded intent,
not a forecaster of it.

Consequences for the prompt:

- The agent's job is: read the repo's task system (backlog / in-progress /
  priorities / what just completed) and the recent git log, then write a plan that
  **reflects what the task state says is next**.
- **Conservative default:** if the task state does not clearly indicate a next
  step, **keep the current plan and only roll the date forward** — never
  manufacture a new direction. (This mirrors the keep-vs-advance calls made by
  hand on 2026-07-27: advance only where landed work + task state made the next
  step unambiguous; otherwise re-date.)
- The agent does **not** curate tasks. If the plan can't be derived because the
  tasks are stale, that is a signal for the human to update tasks — surface it,
  don't paper over it.

## Design

### Roster & local-path mapping (the first real gap)

- Roster comes from `repos.yml` (single source), same as the rest of the toolkit.
- But `repos.yml` holds **remotes, not local paths**, and drafts must land in the
  human's **working checkouts** under the umbrella — **not** the gitignored
  `tracked/` clone cache. The tool needs a repo → local-checkout-path resolution
  that:
  - handles the **worktree layout** (`create-ai-builder/main`, not
    `create-ai-builder`);
  - **skips repos not checked out locally** (e.g. `customer-req-responder`, which
    is exactly why it stayed STALE on 2026-07-27) and reports them as skipped.
- Reuse the sibling-checkout resolution precedent already established by
  `tools/gen-umbrella-claude.py` (local sibling first) rather than inventing a new
  one.

### Local-only, like `gen-umbrella-claude.py`

The tool writes to local working checkouts and shells out to `claude -p`, so — like
`gen-umbrella-claude.py` — it is **local-only** and must **NOT** be wired into the
remote aggregate cycle (`tools/run.py` / the cloud `/schedule` routine). It is a
**human-invoked** command, not a scheduled job. (That also sidesteps the
vendor-lock concern in the reminder task: the LLM step is inherently Claude-coupled
by nature, but nothing here binds to hosted `/schedule` infra.)

### Per-repo invocation

For each resolved repo, run `claude -p` with **cwd = the repo's checkout** and a
standard prompt (see below). Rooting in the repo is the whole point: it is what
loads that repo's `CLAUDE.md`, its `task-system` skill, and lets the agent read its
own `project/tasks/` tree and git log.

### Prompt lives in a template, not the umbrella CLAUDE.md

Per the `agent-instruction-placement` convention (kernel vs. reference): a
multi-step "how to draft a plan" procedure is reference/how-to shaped and must not
bloat the always-on umbrella `CLAUDE.md`. So:

- The agent prompt lives in a versioned **`templates/replan-prompt.md`** (single
  source of truth) that the tool passes to each invocation.
- The umbrella `CLAUDE.md` gets only a **one-line pointer** (added via
  `gen-umbrella-claude.py`): *"Draft next-day daily-plans for review:
  `python3 project-status/tools/replan.py`."*

### Where drafts land / the review surface — resolve at build time

The tool produces **multiple drafts for one batch review**, then stops. How the
drafts are staged is the main open decision (see Decisions):

- **Option A — staging dir (leaning toward this):** write drafts to a review area
  (e.g. `project-status/drafts/<date>/<repo>.md`, gitignored) and print a summary
  table. Working trees stay clean until the human approves; an optional `--apply`
  step copies approved drafts into their repos. Cleanest separation; partial
  approval is trivial.
- **Option B — in-place, uncommitted:** overwrite each repo's `daily-plan.md` in
  the working tree and let the human review via `git diff` per repo, then commit &
  push what they approve. Uses git as the review surface but leaves N dirty working
  trees; rejecting some means reverting those.
- **Never:** commit-and-push, or commit at all without explicit human direction.

### Resumability / robustness

The 2026-07-27 hand-run's subagent fan-out **died mid-batch on a login-expiry API
error**. A batch tool must therefore be **per-repo idempotent and re-runnable**,
reporting a per-repo status line (`drafted` / `kept (re-dated)` / `skipped: not
checked out` / `failed: <reason>`) and never leaving a repo half-written. Prefer a
clear per-repo loop with isolated failures over one all-or-nothing parallel spawn.

## Sources / prior art to reuse (do not reimplement)

- `repos.yml` + `tools/_lib.py:load_repos()` / `enabled_repos()` — the roster.
- `tools/gen-umbrella-claude.py` — sibling-checkout path resolution + local-only,
  not-in-remote-cycle precedent + the `gen-umbrella-claude.py` one-line-pointer
  splice into the umbrella `CLAUDE.md`.
- `tools/aggregate-plans.py:parse_plan()` / `most_recent_weekday()` — plan header
  date parsing and weekend-tolerant freshness, if the tool wants to decide
  keep-vs-advance or label drafts.
- Each repo's `task-system` skill + `project/tasks/` layout — the intent source the
  prompt reads.

## Out of scope

- Any change to the remote aggregate cycle (`tools/run.py`, cloud routine).
- Curating tasks on the human's behalf (the agent reads task state; it never
  edits it).
- Pushing, or committing without explicit human direction.
- The missing-plan *notification* (that's `2026-06-29-daily-plan-reminder.md`).

## Decisions

**Settled:**

- **Draft-only; the tool never pushes.** It emits candidate plans for human
  review; the human approves and directs all pushing, out of band. ✅
- **Intent lives in the task system.** The human curates tasks; the agent derives
  the plan by inspecting current task state (+ git log), defaulting to
  keep-and-re-date when the next step isn't clear. The agent never invents
  direction and never edits tasks. ✅
- **One `claude -p` per repo, rooted in the repo's checkout** (so its
  `CLAUDE.md`/skills/task-system load). ✅
- **Local-only, human-invoked; not wired into the remote cycle.** ✅
- **Prompt lives in `templates/replan-prompt.md`; umbrella `CLAUDE.md` gets a
  one-line pointer only.** ✅

**Remaining (resolve at build time):**

1. **Review surface** — staging dir + optional `--apply` (Option A, leaning) vs.
   in-place uncommitted `git diff` (Option B).
2. **Draft target date** — default to the next business day (forward-looking,
   reuse the weekday-skipping logic) vs. an explicit `--date` argument; confirm
   Friday → Monday behavior.
3. **Parallel vs. sequential fan-out** — given the login-expiry failure mode,
   decide whether isolated-failure parallelism is worth it over a simpler
   sequential loop with per-repo status.
4. **Keep-vs-advance authority** — does the agent decide per repo from task state
   (preferred), or does the tool always draft and let the human decide? Preferred:
   agent decides, conservative default = keep.

## To-do checklist

- [ ] Add repo → local-checkout-path resolution (worktree-aware; skip
      not-checked-out repos), reusing `gen-umbrella-claude.py`'s sibling logic.
- [ ] Author `templates/replan-prompt.md`: read the repo's task system + git log →
      draft a `daily-plan.md` for the target date; conservative keep-and-re-date
      default; never edit tasks; surface "tasks too stale to derive a plan."
- [ ] Build `tools/replan.py`: resolve roster → per-repo `claude -p` (cwd = repo)
      → stage drafts → per-repo status report. Never pushes; never commits without
      explicit direction.
- [ ] Decide + implement the review surface (staging dir + `--apply`, or in-place).
- [ ] Add the one-line pointer to the umbrella `CLAUDE.md` template in
      `gen-umbrella-claude.py`.
- [ ] Make the batch re-runnable / per-repo idempotent (isolated failures, clean
      partial state) — motivated by the 2026-07-27 login-expiry mid-batch failure.
- [ ] Document the command in `CLAUDE.md` (its own section; local-only, draft-only,
      not part of the remote cycle) and cross-link the reminder task.
- [ ] Resolve the remaining build-time decisions (review surface, target-date
      math, fan-out shape, keep-vs-advance authority).
