# ai-project-status — Design

## Purpose

`ai-project-status` is a meta-repo that tracks development progress across a portfolio of other `ai-*` repos. It is **not** an aggregator of raw logs — it is a status reporter. The deliverable is a single `summary.md` that gives a high-level, human-readable picture of what has been built across the tracked repos, with the most recent activity at the top.

This repo does no AI development work itself. It observes other repos, summarizes their activity at a daily resolution, and stays in sync via a scheduled daily run.

## Theory of operation

Deterministic plumbing (Python) gathers facts. Non-deterministic summarization (Claude) is isolated to per-repo prompt invocations plus a final cross-repo polish pass. The orchestrator (`tools/run.py`) is the single entry point — it is the only thing that touches `summary.md` and triggers `state.json` advancement.

```
+---------------+    +---------------+
|   repos.yml   |    |  state.json   |   (config + durable record)
+-------+-------+    +-------+-------+
        |                    |
        v                    v
+---------------------------------------+
|           tools/sync.py               |  git clone / git pull --ff-only
|  -- refreshes tracked/<name>/ caches  |
+----------------+----------------------+
                 |
                 v
+---------------------------------------+
|         tools/new-work.py             |  per-repo classification:
|  -- ACTIVE:   log.md diff + --stat    |    ACTIVE  (new commits)
|               + commits since         |    INACTIVE (no new commits)
|               last_commit             |    INACTIVE_SUPPRESSED
|  -- INACTIVE: days-since-activity     |    NOT_SYNCED
+----------------+----------------------+
                 |
                 v
+---------------------------------------+
|           tools/run.py                |  orchestrator (single entry point)
+----------------+----------------------+
                 |
       +---------+---------+
       |                   |
  inactive repo       active repo
  (deterministic)     (LLM-generated)
       |                   |
       v                   v
  one-liner:        +--------------------+
  "No activity      |   claude -p        |  prompt: prompts/per-repo.md
   for N days..."   |   per-repo summary |  input:  that repo's slice
                    +---------+----------+
                              |
                              v
                  per-repo markdown blob
       |                      |
       +----------+-----------+
                  v
+---------------------------------------+
| collected day section (drafts)        |
| -- inactivity lines + per-repo blobs, |
|    in repos.yml order                 |
+----------------+----------------------+
                 |
                 v
+---------------------------------------+
|  claude -p (cross-repo polish)        |  prompt: prompts/polish.md
|  -- input:  per-repo drafts           |  merges cross-repo themes,
|  -- output: polished day section      |  tightens prose
|  -- skipped when <2 active repos      |
+----------------+----------------------+
                 |
                 v
+---------------------------------------+
|    prepend to summary.md              |
+----------------+----------------------+
                 |
                 v
+---------------------------------------+
|      tools/commit-state.py            |  advance state.json,
| -- git commit summary.md + state.json |  single atomic commit
+---------------------------------------+
```

The polish step is the only place where cross-repo context exists; per-repo summary calls only see their own repo's slice, which keeps each prompt small and focused.

## Inputs and contract with tracked repos

Every tracked repo MUST maintain a `log.md` in its root. Each entry in `log.md` is expected to be at daily or per-commit granularity and describe feature implementation work.

This repo treats `log.md` as the source of truth for *what* was done, and the repo's git history as the source of truth for *when* and *how much* (file counts, hashes).

If a tracked repo does not have a `log.md`, it is flagged in `summary.md` and skipped until one exists.

## Components

### 1. `repos.yml` — the tracked-repo registry

A single config file listing every repo to monitor. Tracked by **remote URL**, not local path, so this tool can run anywhere.

```yaml
repos:
  - name: ai-foo
    remote: git@github.com:cornjacket/ai-foo.git
    branch: main             # optional, defaults to main
    enabled: true            # optional, defaults to true. If false, repo is skipped entirely.
    report_inactivity: true  # optional, defaults to true. If false, repo is omitted from the daily section when it has no new work.
  - name: ai-bar
    remote: git@github.com:cornjacket/ai-bar.git
```

Both `enabled` and `report_inactivity` default to `true` so the common case (track everything, surface silence) needs no extra config.

### 2. `tracked/` — gitignored working copies

On each run, the tool clones any new repo and `git pull`s existing ones into `tracked/<name>/`. This directory is in `.gitignore`. It is a cache; deleting it must not lose any state.

### 3. `state.json` — what we've already seen

For each tracked repo, store the last commit hash that has been incorporated into `summary.md` and the date of the most recent observed activity (used to compute "no activity for N days"):

```json
{
  "ai-foo": {
    "last_commit": "abc1234",
    "last_synced": "2026-04-30",
    "last_activity_date": "2026-04-30"
  },
  "ai-bar": {
    "last_commit": "def5678",
    "last_synced": "2026-04-30",
    "last_activity_date": "2026-04-22"
  }
}
```

A single commit hash per repo drives change detection: `git diff <last_commit>..HEAD -- log.md` gives new log entries, and `git diff --stat <last_commit>..HEAD` gives file change counts. `last_activity_date` is updated only when there *is* new work; it lets the inactivity message be precise without re-scanning history. This file IS committed — it is the durable record of progress.

### 4. `summary.md` — the deliverable

Reverse-chronological, daily-resolution summary across all tracked repos. Newest day at the top. Each day has a section per **enabled** repo. Repos with new activity get a substantive summary; repos with no new activity (and `report_inactivity: true`) get a one-liner:

```markdown
## 2026-04-30

### ai-foo
- Added vector store backend (commits abc1234..bcd2345; 12 files added, 3 changed, 0 deleted)
- Refactored prompt cache layer to use TTL config

### ai-bar
- No activity for 8 days (last activity 2026-04-22)
```

Activity summaries are *interpretive*, not copy-paste — they capture intent at a level a stakeholder skimming the file can understand in seconds. Important details get pulled out; everything else is left in the source `log.md`. Git hashes are always referenced so a reader can drill in.

### 5. `tools/` — scripts that do the boring work

Small, composable scripts so the orchestrator and individual `claude -p` calls each do exactly one thing:

- `tools/sync.py` — clone or `git pull` every **enabled** repo in `repos.yml` into `tracked/`
- `tools/diff.py <repo>` — print the new `log.md` lines and `--stat` since the recorded `last_commit` for that repo (debugging aid)
- `tools/new-work.py` — emit a single structured report covering every enabled repo. Active repos get diffs + `--stat` + commit list; inactive repos get `last_activity_date` and computed days-since-activity. The orchestrator parses this report and dispatches per-repo work.
- `tools/run.py` — orchestrator and single entry point. Calls `sync.py`, parses `new-work.py` output, writes inactivity lines deterministically, spawns one `claude -p` per active repo, runs the cross-repo polish pass when ≥2 repos are active, prepends the result to `summary.md`, and calls `commit-state.py`.
- `tools/commit-state.py` — advance `state.json` (bump `last_commit`, `last_synced` always; bump `last_activity_date` only when there was new work) and commit `summary.md` + `state.json` in one commit
- `tools/_lib.py` — shared helpers (config/state I/O, git wrapper, paths)

### 6. `prompts/` — versioned prompt templates

Prompt templates live in files so they can be reviewed, diffed, and edited without changing code:

- `prompts/per-repo.md` — instructions for the per-repo summary call. Variables substituted by `run.py`: repo name, the repo's slice from `new-work.py`, and the summarization rules from `CLAUDE.md`.
- `prompts/polish.md` — instructions for the cross-repo polish pass. Variables: today's date, the concatenated per-repo drafts.

### 7. `CLAUDE.md` — operating directives

Tells Claude (in future sessions) exactly how to run an update cycle, the rules for summarization (high-level, no copy-paste, reference hashes, daily resolution, newest-on-top, inactivity formatting), and where state lives. Short and prescriptive.

## Daily run procedure

A single command does the whole cycle:

```
python3 tools/run.py
```

Internally, `run.py`:

1. Calls `sync.py` to refresh local clones.
2. Calls `new-work.py` and parses the per-repo report.
3. For each repo:
   - `INACTIVE` + `report_inactivity: true` → write a deterministic one-liner `No activity for N days (last activity YYYY-MM-DD)`.
   - `INACTIVE_SUPPRESSED` or `enabled: false` → omit.
   - `ACTIVE` → spawn `claude -p` with `prompts/per-repo.md` and that repo's slice; capture the returned markdown.
4. If ≥2 repos are active, runs a final `claude -p` polish pass (`prompts/polish.md`) over the collected drafts to surface cross-repo themes and tighten prose. Otherwise uses the drafts as-is.
5. Prepends the polished `## YYYY-MM-DD` section to `summary.md`.
6. Calls `commit-state.py`, which advances `state.json` and creates a single atomic commit of `summary.md` + `state.json`.

If every enabled repo has no new work AND every such repo has `report_inactivity: false`, the run produces no commit.

## Scheduling

A daily scheduled agent (via `/schedule`) runs the procedure above. Local execution is also supported — the only required state lives in `repos.yml` and `state.json`, both committed.

## Build tasks

Roughly in order:

1. Create `.gitignore` for `tracked/` and any local-only files.
2. Create `repos.yml` (start empty or with one repo to validate the flow).
3. Create `state.json` (start as `{}`).
4. Create `tools/sync.py` — clone if absent, else `git -C tracked/<name> pull --ff-only`. Skips repos with `enabled: false`.
5. Create `tools/diff.py` — for one repo, `git -C tracked/<name> diff <last_commit>..HEAD -- log.md` plus `--stat`.
6. Create `tools/new-work.py` — emit a single structured report covering every enabled repo, including inactivity metadata.
7. Create `tools/commit-state.py` — update `state.json` to current HEADs (and `last_activity_date` where applicable), commit `summary.md` + `state.json`.
8. Create `summary.md` with just a top-level header.
9. Create `CLAUDE.md` documenting the run procedure and summarization rules (including the inactivity-line format).
10. Create `prompts/per-repo.md` and `prompts/polish.md` prompt templates.
11. Create `tools/run.py` orchestrator: parse `new-work.py` output, write inactivity lines deterministically, spawn `claude -p` per active repo, conditionally run polish pass, prepend to `summary.md`, call `commit-state.py`.
12. Add automated tests for the deterministic layer. The two `claude -p` calls themselves are non-deterministic and out of scope; `--dry-run` covers pipeline shape without LLM cost.
    1. `tests/test_lib.py` — unit tests for `gather_report()` against tmp git repos. Cover all four statuses (ACTIVE, INACTIVE, INACTIVE_SUPPRESSED, NOT_SYNCED), the empty-`state.json` case (first run uses `EMPTY_TREE`), and the `days_inactive` math.
    2. `tests/test_run.py` — unit tests for `prepend_to_summary()` (marker present, marker absent + existing day section, empty file) and `render_inactive()` (with and without `last_activity_date`).
    3. End-to-end `--dry-run` smoke test: build two tmp git repos with `log.md`, point a fixture `repos.yml`/`state.json` at them, run the orchestrator, assert a `## YYYY-MM-DD` section was prepended and `state.json` advanced.
13. Do a manual end-to-end run against one real tracked repo to validate prose quality from the live `claude -p` calls.
14. Set up the daily `/schedule` agent.

## Non-goals

- Not a CI system. Doesn't run tests or builds in tracked repos.
- Not a code reviewer. Reads `log.md`, not source diffs (beyond `--stat`).
- Not a real-time dashboard. Daily resolution is the design point.
- Doesn't enforce log format on tracked repos beyond "exists at `log.md`".
