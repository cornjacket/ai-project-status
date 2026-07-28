# CLAUDE.md — project-status operating directives

## Purpose

This repo summarizes development activity across other `ai-*` repos. See `DESIGN.md` for the full design.

You are NOT doing AI development here. You are reading other repos' git commit telemetry (structured commit messages) and producing an interpretive, daily-resolution rollup in `summary.md`.

## Add a new tracked repo

When the user asks to add a repo to the tracker, run the full workflow — don't stop after editing `repos.yml`. All four steps are required for the repo to actually be summarized:

1. **Bootstrap the target repo.** Run `./setup-new-repo.sh <remote-url> [branch]`. This clones the repo to a tmp dir, ensures it has `daily-plan.md`, the kernel rule block in its `CLAUDE.md`, `project-status-guide.md` at the repo root (the on-demand reference half of those rules), the SessionStart hook script at `.claude/hooks/check-daily-plan.py`, and a merged `.claude/settings.json` registering the hook — then commits and pushes. Idempotent — safe to re-run. The guide and hook are upstream-managed and always refreshed; pass `--update` to also replace the `CLAUDE.md` rule block in place after editing the templates. Without this, the repo lacks the commit-message discipline that makes `new-work.py`'s git telemetry useful, and `aggregate-plans.py` has no `daily-plan.md` to read. (To migrate an already-tracked repo off the old `log.md` workflow, run `./migrate-target-telemetry.sh <local-checkout>`.)
2. **Register in `repos.yml`.** Append an entry under `repos:` with `name` and `remote` (and `branch` if non-default). Order matters — repos appear in `summary.md` in `repos.yml` order.
3. **Regenerate the umbrella `CLAUDE.md`.** Run `python3 tools/gen-umbrella-claude.py` so the workspace-root roster reflects the new repo. Local-only (the umbrella path doesn't exist in the remote run), so it is deliberately not part of `tools/run.py`.
4. **Add to the daily `/schedule` routine's `sources`.** Routine ID: `trig_01BLz2BYyE95n44TCDKaFcnA`. Use the `RemoteTrigger` tool — `action: "get"` to fetch the current config, then `action: "update"` with the full `job_config` and an extra `{"git_repository": {"url": "https://github.com/cornjacket/<repo>"}}` appended to `session_context.sources`. Send back the entire `job_config` (don't rely on partial-merge semantics) to avoid clobbering other fields. Browser URL for human verification: https://claude.ai/code/routines/trig_01BLz2BYyE95n44TCDKaFcnA. Skip this step only if the user confirms they run the pipeline locally only — without it, the sandbox's egress proxy blocks the remote routine from cloning the new repo.

## Run an update cycle

1. `python3 tools/sync.py` — clone or fast-forward-pull every enabled repo into `tracked/`.
2. `python3 tools/new-work.py` — produce a per-repo report. Capture stdout (e.g., into a temp file) and read it.
3. Prepend a new `## YYYY-MM-DD` section to the top of `summary.md` (just below the title block):
   - For each repo marked `ACTIVE` in the report: write a `### <repo-name>` subsection with a short, interpretive bullet list. Reference short commit hashes from the `### commits` block. Mention file counts from `### file stat` when the change size is meaningful.
   - All `INACTIVE` repos collapse into a single `### No updates` subsection at the END of the day section, one bullet per repo: `- <repo-name> (for N days)` (or `- <repo-name> (no activity recorded yet)`). Repos appear in `repos.yml` order. Omit the section entirely when no repos are inactive.
   - For each repo marked `INACTIVE_SUPPRESSED`: omit it entirely.
   - For each repo marked `NOT_SYNCED`: omit it (sync should have fixed this; if it didn't, the prior step printed the error).
4. `python3 tools/aggregate-plans.py` — overwrite `daily-plan-summary.md` with an "At a glance" table (one row per repo: priority band, plan freshness, today's focus, days idle — fresh plans first, then by band) followed by each tracked repo's current `daily-plan.md` **in that same order**, weekend-tolerant staleness check, missing/stale plans visibly flagged. Also snapshots the aggregated summary into `daily-plan-archive/YYYY-MM-DD.md` (keyed by the summary's own date) so each day's plan is preserved for later review; the canonical `daily-plan-summary.md` stays overwrite-only.
5. `python3 tools/commit-state.py` — advances `state.json` and commits `summary.md`, `daily-plan-summary.md`, `daily-plan-archive/`, and `state.json` together.

`tools/run.py` is the orchestrator that runs all five steps; the manual flow above is for understanding or for hand-running individual steps.

## Draft next-day daily-plans (local-only, human-invoked)

`python3 tools/replan.py` fans out one `claude -p` per tracked repo, each rooted
in that repo's own local checkout, and rewrites that repo's `daily-plan.md` in
place for the next business day. Two rules define it:

- **Draft-only — git is the review surface.** Plans are written to the working
  tree and left **uncommitted**; the tool never stages, commits, or pushes. Every
  drafted plan shows up as a modified file (VS Code's Source Control view,
  `git diff`), and the run ends by telling the human to review, commit, and push
  from inside each repo. It refuses to overwrite a `daily-plan.md` that already
  has uncommitted changes — that's work git can't give back (`--force` overrides).
- **The plan is read from task state, not invented.** The human encodes intent by
  curating each repo's task system; the agent derives the plan from that state
  plus the git log, and defaults to keeping the current plan re-dated whenever
  the next step isn't unambiguous. It runs read-only (no Write/Edit tools), so it
  cannot edit the tasks it reads and the tool owns every write. `blocked` in the
  report means the task state is too stale to derive a plan — that's a signal to
  curate tasks, not a bug.

Local-only, like `gen-umbrella-claude.py`: it writes to working checkouts that
don't exist in the routine sandbox, so it is deliberately **not** part of
`tools/run.py` or the cloud `/schedule` routine. The prompt lives in
`prompts/replan.md` (single source of truth); the umbrella `CLAUDE.md` carries
only a one-line pointer, spliced in by `gen-umbrella-claude.py`.

Re-runnable: a repo whose plan is already dated for the target is skipped
(`--force` to redraft) and per-repo failures are isolated, so a batch that dies
partway resumes without re-spending calls. The idempotency key is the plan's own
header date, so the tool can never disagree with what's on disk. Other flags:
`--date`, `--only`, `--dry-run`, `--report`, `--timeout`, `--model`.

## Summarization rules

- **Daily resolution.** One `## YYYY-MM-DD` section per run.
- **Newest at the top.** Always insert above the previous day's section.
- **One subsection per repo per day**, in the order repos appear in `repos.yml`.
- **Be interpretive, not literal.** A reader scanning `summary.md` should understand what's happening across the portfolio in under a minute. Do NOT copy commit messages verbatim — distill them.
- **Always reference git hashes** (short form, e.g. `abc1234` or a range `abc1234..bcd2345`) so the reader can drill in.
- **File counts are signal, not noise.** Mention `--stat` totals only when they convey scale (e.g., "12 files added"). Skip them for trivial diffs.
- **Inactivity is grouped, not per-repo.** All inactive (and reportable) repos go under a single `### No updates` subsection at the bottom of the day, with `- <repo-name> (for N days)` bullets (or `- <repo-name> (no activity recorded yet)`). Never give an inactive repo its own `### <repo-name>` subsection.

## Config and state

- `repos.yml` — tracked repo registry. Per-repo flags: `enabled` (default true), `report_inactivity` (default true), `branch` (default `main`), `priority` (default 3 — a band, lower = more important; sorts the "At a glance" table only, never `summary.md`).
- `state.json` — `last_commit`, `last_synced`, `last_activity_date` per repo. Committed.
- `daily-plan-archive/` — dated snapshots of `daily-plan-summary.md`, one per run (`YYYY-MM-DD.md`). Committed; append-only history of the aggregated plan. Per-repo `daily-plan.md` files are NOT archived here — they stay overwrite-only, with history in each repo's git log.
- `tracked/` — gitignored cache of cloned repos.

## Tools

- `tools/sync.py` — clone/pull every enabled repo
- `tools/diff.py <repo-name>` — diff for one repo since its `last_commit` (debugging aid)
- `tools/new-work.py` — full structured report you consume to write `summary.md`
- `tools/aggregate-plans.py` — rebuild `daily-plan-summary.md` from each repo's `daily-plan.md` (table and sections share one sort: fresh first, then band, then `repos.yml` order), and snapshot it into `daily-plan-archive/YYYY-MM-DD.md`
- `tools/commit-state.py` — advance `state.json`, commit `summary.md` + `daily-plan-summary.md` + `daily-plan-archive/` + `state.json`
- `tools/run.py` — orchestrator that runs the full update cycle
- `tools/gen-umbrella-claude.py` — regenerate the workspace-root (umbrella) `CLAUDE.md` from `repos.yml`. Local-only; NOT part of the update cycle. Re-run when a repo is added or removed.
- `tools/replan.py` — draft next-day `daily-plan.md` files for human review, one `claude -p` per locally checked-out repo. Local-only, draft-only; NOT part of the update cycle. See the section above.
- `tools/check-targets.py` — report tracked repos whose injected `CLAUDE.md` block or `project-status-guide.md` has drifted from `templates/`. Exits non-zero on drift. The same check is surfaced per repo in `daily-plan-summary.md`, so this is the one-shot whole-portfolio view. Fix with `./setup-new-repo.sh --update <remote>`.
- `hooks/check-repo-bootstrap.py` — user-level `SessionStart` hook (registered in `~/.claude/settings.json`, not in any target repo). Nudges when a git repo under the workspace root has no project-status block in its `CLAUDE.md` — i.e. it was never bootstrapped. Silent for bootstrapped repos, for project-status itself, outside the workspace root, and in any repo containing `.project-status-ignore`.
