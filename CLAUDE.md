# CLAUDE.md — ai-project-status operating directives

## Purpose

This repo summarizes development activity across other `ai-*` repos. See `DESIGN.md` for the full design.

You are NOT doing AI development here. You are reading other repos' `log.md` files and producing an interpretive, daily-resolution rollup in `summary.md`.

## Run an update cycle

1. `python3 tools/sync.py` — clone or fast-forward-pull every enabled repo into `tracked/`.
2. `python3 tools/new-work.py` — produce a per-repo report. Capture stdout (e.g., into a temp file) and read it.
3. Prepend a new `## YYYY-MM-DD` section to the top of `summary.md` (just below the title block):
   - For each repo marked `ACTIVE` in the report: write a `### <repo-name>` subsection with a short, interpretive bullet list. Reference short commit hashes from the `### commits` block. Mention file counts from `### file stat` when the change size is meaningful.
   - For each repo marked `INACTIVE`: write one line under `### <repo-name>`: `No activity for N days (last activity YYYY-MM-DD)` (or `No activity recorded yet`).
   - For each repo marked `INACTIVE_SUPPRESSED`: omit it entirely.
   - For each repo marked `NOT_SYNCED`: omit it (sync should have fixed this; if it didn't, the prior step printed the error).
4. `python3 tools/commit-state.py` — advances `state.json` and commits `summary.md` + `state.json` together.

## Summarization rules

- **Daily resolution.** One `## YYYY-MM-DD` section per run.
- **Newest at the top.** Always insert above the previous day's section.
- **One subsection per repo per day**, in the order repos appear in `repos.yml`.
- **Be interpretive, not literal.** A reader scanning `summary.md` should understand what's happening across the portfolio in under a minute. Do NOT copy `log.md` lines verbatim — distill them.
- **Always reference git hashes** (short form, e.g. `abc1234` or a range `abc1234..bcd2345`) so the reader can drill in.
- **File counts are signal, not noise.** Mention `--stat` totals only when they convey scale (e.g., "12 files added"). Skip them for trivial diffs.
- **Inactivity wording** is fixed: `No activity for N days (last activity YYYY-MM-DD)`. Keep it terse.

## Config and state

- `repos.yml` — tracked repo registry. Per-repo flags: `enabled` (default true), `report_inactivity` (default true), `branch` (default `main`).
- `state.json` — `last_commit`, `last_synced`, `last_activity_date` per repo. Committed.
- `tracked/` — gitignored cache of cloned repos.

## Tools

- `tools/sync.py` — clone/pull every enabled repo
- `tools/diff.py <repo-name>` — diff for one repo since its `last_commit` (debugging aid)
- `tools/new-work.py` — full structured report you consume to write `summary.md`
- `tools/commit-state.py` — advance `state.json`, commit
