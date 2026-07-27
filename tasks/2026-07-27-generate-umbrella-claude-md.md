# Task: Generate an umbrella CLAUDE.md for the workspace root

- **Created:** 2026-07-27
- **Status:** DONE — 2026-07-27. `tools/gen-umbrella-claude.py` shipped with
  tests (`tests/test_gen_umbrella_claude.py`); artifact generated at
  `~/src/github.com/cornjacket/CLAUDE.md`.
- **Owner:** _unassigned_

## Goal

Give the "umbrella" Claude session — the one run from the parent directory that
sits *above* all tracked repos (`~/src/github.com/cornjacket/`) — a purpose-built
`CLAUDE.md` so it behaves as a **read-only cross-repo dashboard/orchestrator**,
not a workbench. Today that directory has no `CLAUDE.md`, so an umbrella session
runs with none of the workspace's repos, roles, or guardrails in context.

## Why a generator (not a hand-written file)

The umbrella directory is **not a git repo**, so the file cannot be version
controlled there — it must be a **regenerable build artifact**. The generator
(`tools/gen-umbrella-claude.py`) lives here in `project-status` (version
controlled) and writes the artifact out to the umbrella path.

## Design

- **Local-only tool.** It writes to the local umbrella directory, which does not
  exist in the remote scheduled run. It therefore **must NOT** be wired into the
  remote aggregate cycle (`aggregate-plans.py` / `tools/run.py`, which run in the
  cloud routine).
- **Trigger:** re-run whenever a repo is **added to or removed from** `repos.yml`
  (the roster changed). A manual `python3 tools/gen-umbrella-claude.py` for now;
  optionally a thin wrapper in the "add a repo" workflow.
- **Preflight:** first check whether a `CLAUDE.md` already exists at the umbrella
  path. If it exists, only rewrite the **managed block** (see below) and leave any
  hand-written content intact. If it does not exist, create it from the template.
- **Managed-block split** (same pattern as `setup-new-repo.sh`): a static role /
  guardrail / pointers section that a human owns, plus a
  `<!-- project-status:begin/end -->` block holding the **generated repo roster**
  (name + one-line purpose + path per repo). Regeneration only ever touches the
  block.

## Sources

- Repo list + remotes → `repos.yml`.
- One-line "what this repo is" per repo → each repo's `daily-plan.md`
  "What this repo is (for a newcomer)" line (the same field `aggregate-plans.py`
  already parses). Fall back gracefully when a repo has no plan yet.

## Content the umbrella CLAUDE.md should carry

1. **Role + read-only guardrail** (static) — "you are above N repos; do edits and
   commits *inside* the owning repo, not here; this session is a dashboard."
2. **Generated repo roster** (block) — name, one-line purpose, local path.
3. **Pointers to the review layer** (static) — `daily-plan-summary.md`,
   `summary.md`; link, don't inline (stays fresh via the aggregator).
4. **Genuinely cross-repo conventions** (static) — shared commit schema, naming,
   "consult second-brain before designing."

Keep the block **thin** — it is always-on context for every umbrella session.
Names + one-liners, not full plans; point at the aggregate for depth.

## Out of scope

- Any change to the remote aggregate cycle.
- Per-repo build directives (those stay in each repo's own `CLAUDE.md`).

## Notes

- Related: task capture from the umbrella session is an accepted exception to the
  read-only guardrail (capture is planning, not code mutation) — the guardrail is
  "no code/commits in *target* repos," not "no writes at all."

## As built (2026-07-27)

`tools/gen-umbrella-claude.py`, `--path` / `--dry-run`, default path = the
project-status parent directory. Decisions that went beyond the sketch:

- **Purpose source precedence:** local sibling checkout's `daily-plan.md` first,
  then `tracked/<repo>/daily-plan.md`, then a `_(no daily-plan.md yet)_`
  placeholder. The sibling wins because it's the working copy the umbrella
  session actually sees, and it's the path the roster points at.
- **Purpose length:** first sentence, but a second is folded in when the first is
  under 60 chars (`"foo is a generator."` alone carries no signal); hard cap 160
  chars with an ellipsis. The block is always-on context, so it stays thin.
- **Untracked siblings are deliberately excluded.** `repos.yml` is the only
  source of the roster: if a directory isn't tracked by project-status, the
  umbrella `CLAUDE.md` doesn't consider it. (A filesystem-derived "also present
  here" line was tried and removed — it made the artifact describe things the
  tracker has no view of.) The block heading says "Repos tracked by
  project-status" so the scope is explicit.
- **Guardrails:** refuses to write to project-status itself; splice is idempotent
  and preserves everything outside the markers; a marker-less hand-written file
  gets the block appended rather than clobbered.
- Registered as step 3 of the "Add a new tracked repo" workflow in `CLAUDE.md`.
  Still not wired into `tools/run.py` (remote run has no umbrella path).
