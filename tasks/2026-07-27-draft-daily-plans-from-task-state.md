# Task: Draft next-day daily-plans from each repo's task state (human-reviewed, never auto-pushed)

- **Created:** 2026-07-27
- **Status:** DONE — 2026-07-27. `tools/replan.py` shipped with `prompts/replan.md`
  and `tests/test_replan.py` (38 tests); plans rewritten **in place, uncommitted**,
  with git as the review surface; `local_checkout` lifted into `_lib.py` so the
  roster and the drafts resolve the same paths; documented in `CLAUDE.md`,
  `README.md`, and the umbrella pointer. Smoke-tested live against `captains-log`
  (verdict `kept`, correctly conservative).
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

The tool produces **multiple drafts for one batch review**, then stops.

**Resolved: Option B — in-place, uncommitted.** Each repo's `daily-plan.md` is
overwritten in its working tree and left unstaged. The human reviews the batch in
VS Code's Source Control view (which already lists every modified
version-controlled file across the workspace) or via `git diff` per repo, then
commits and pushes what they approve, from inside each repo. The run's last line
says exactly that.

The staging-dir alternative (Option A: `drafts/<date>/<repo>.md` + `--apply`) was
built first and reversed: it kept working trees clean, but at the cost of putting
the artifact somewhere the human's review tool doesn't look, plus a copy step
between the two. Dirty working trees are not a side effect here — they *are* the
notification.

**Never:** commit-and-push, or stage or commit at all. Approval is the human's.

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

**Resolved at build time (2026-07-27):**

1. **Review surface — Option B, in place.** Built as Option A (staging dir +
   `--apply`) first and **reversed by the operator the same day**: the review tool
   is already open. VS Code's Source Control view lists every modified
   version-controlled file across the workspace, so writing the plan straight into
   each repo's working tree *is* the batch review — a staging dir just added a
   second place to look and a copy step between them. So: rewrite `daily-plan.md`
   in place, leave it uncommitted, and end the run with "review the daily-plans,
   commit, and push." Never stage, never commit, never push. The clobber guard
   survives from Option A — a `daily-plan.md` with uncommitted changes is skipped
   (`--force` overrides), because that is work git cannot give back.

   *Lesson worth keeping:* when the human's review already happens in a tool that
   watches the working tree, a staging area is not neutral overhead — it moves the
   artifact **out of** the surface they actually read. ✅
2. **Target date — next business day, `--date` overrides.** Fri/Sat/Sun all point
   at Monday, matching the aggregator's weekend tolerance: a Friday plan stays
   fresh through Sunday, so Monday's is the one actually missing. ✅
3. **Fan-out — sequential.** The failure mode that actually bit is *shared* (an
   expired login kills every concurrent call at once), so parallelism would buy
   wall-clock at the cost of legible output and re-run clarity. Resumability comes
   from the plan files themselves: a re-run skips any repo whose plan is already
   dated for the target (`--force` redrafts), failures are isolated per repo, and
   writes are atomic (temp file + rename) so no repo is ever left half-written.
   Deriving idempotency from the plan's own header rather than a sidecar ledger
   means the tool can't disagree with what's on disk. ✅
4. **Keep-vs-advance — the agent decides, conservatively.** It reports
   `advanced` / `kept` / `blocked` and the tool passes that straight into the
   status table, so the human sees *which* repos actually moved. ✅

**Amended:**

- **Prompt lives in `prompts/replan.md`, not `templates/replan-prompt.md`.** The
  substance of the decision (versioned single-source file, one-line pointer in the
  umbrella `CLAUDE.md`) is unchanged; only the directory moved. `templates/` holds
  files *installed into* tracked repos — `check-targets.py` diffs every one of
  them against the checkouts — while `prompts/` is already the home for `claude -p`
  templates (`per-repo.md`, `polish.md`). A prompt in `templates/` would blur what
  that directory means.

## To-do checklist

- [x] Add repo → local-checkout-path resolution (worktree-aware; skip
      not-checked-out repos). Rather than reuse `gen-umbrella-claude.py`'s copy,
      `local_checkout` was lifted into `_lib.py`: the roster and the drafts must
      resolve to the same path, and two copies would eventually be two answers.
- [x] Author the prompt (`prompts/replan.md`): read the repo's task system + git
      log → draft a `daily-plan.md` for the target date; conservative
      keep-and-re-date default; never edit tasks; surface "tasks too stale to
      derive a plan" as `blocked`.
- [x] Build `tools/replan.py`: resolve roster → per-repo `claude -p` (cwd = repo)
      → stage drafts → per-repo status report. Never pushes; never commits.
- [x] Decide + implement the review surface (in-place + uncommitted; git and the
      editor's source-control view are the review surface).
- [x] Add the one-line pointer to the umbrella `CLAUDE.md` template in
      `gen-umbrella-claude.py` (and to the live artifact, which sits outside the
      generated markers).
- [x] Make the batch re-runnable / per-repo idempotent (isolated failures,
      atomic draft writes, status persisted after every repo).
- [x] Document the command in `CLAUDE.md` (its own section), `README.md`, and the
      umbrella pointer.
- [x] Resolve the remaining build-time decisions (above).

## Enforced, not merely asked

The "never edits tasks" rule is a CLI flag, not a sentence in the prompt: the
agent runs with `--disallowedTools Write,Edit,NotebookEdit,…` and an allowlist of
read-only `Bash(git log:*)`-style commands. The prompt still states the rule (the
agent should understand *why* it is read-only), but the guarantee doesn't depend
on it complying. Its whole output is text on stdout; the tool owns every write.

## Follow-on

The *nudge* side — [`2026-06-29-daily-plan-reminder.md`](2026-06-29-daily-plan-reminder.md)
— is now the only half of the loop still unbuilt. `replan.py --report` already
prints the state a notifier would send, so the reminder can lean on it rather than
re-deriving freshness.
