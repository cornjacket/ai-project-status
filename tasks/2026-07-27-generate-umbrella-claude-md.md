# Task: Generate an umbrella CLAUDE.md for the workspace root

- **Created:** 2026-07-27
- **Status:** IN-PROGRESS — sketching the tool + static block.
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
