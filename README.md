# project-status

Tracks development activity across a portfolio of `ai-*` repos and produces two cross-repo rollups: a retrospective `summary.md` (newest activity at the top, daily resolution) and a forward-looking `daily-plan-summary.md` (today's plan from each repo, overwritten daily). Backward-looking activity is read directly from each repo's git commit telemetry (structured commit messages — title + `[Context]`/`[Impact]`); forward-looking intent comes from each repo's `daily-plan.md` (one day's intent). This tool reads those, summarizes activity per repo via `claude -p`, runs a cross-repo polish pass when more than one repo has new work, and aggregates the per-repo plans deterministically.

**Current rollup: [`summary.md`](summary.md).** &nbsp; **Today's plan: [`daily-plan-summary.md`](daily-plan-summary.md).**

> **Note:** this system assumes **one human developer per tracked repo**. With multiple developers contributing to the same repo, `daily-plan.md` will conflict. See [`DESIGN.md` — Known limitations](DESIGN.md#known-limitations) for the proposed `status/<username>/...` mitigation.

For the architecture and rationale, see [`DESIGN.md`](DESIGN.md). For the rules an AI follows when running the update cycle, see [`CLAUDE.md`](CLAUDE.md).

## Setup

Requires `python3`, `git`, `claude` (the Claude Code CLI), and the `pyyaml` package.

```bash
git clone git@github.com:cornjacket/project-status.git
cd project-status
pip install pyyaml
```

## Adding a tracked repo

Three steps: bootstrap the target repo, register it, and (if you use the `/schedule` daily flow) add it to the routine's `sources`.

### 1. Bootstrap the target

```bash
./setup-new-repo.sh git@github.com:cornjacket/ai-foo.git
```

This clones `ai-foo` to a temp directory, drops in a starter `daily-plan.md` file, injects a git-automation + daily-plan rule block into `CLAUDE.md` (between `<!-- ai-project-status:begin -->` markers), installs a `SessionStart` hook at `.claude/hooks/check-daily-plan.py` (with a merged `.claude/settings.json` registering it), commits, pushes, and cleans up. The rule tells Claude — when working in `ai-foo` — to write structured, telemetry-bearing commit messages at task granularity and to keep `daily-plan.md` fresh; the hook prompts for a fresh plan at session start when the file is stale or missing.

To migrate a repo that was previously bootstrapped with the old `log.md` workflow, run `./migrate-target-telemetry.sh <local-checkout>` against a local clone — it removes `log.md`, swaps the managed `CLAUDE.md` block for the git-automation rules, and leaves `daily-plan.md` untouched. Review the diff and commit.

The script is idempotent: re-running on an already-bootstrapped repo only adds anything that's missing. Pass `--update` to refresh the rule block and the hook script in place after editing `templates/claude-rule.md` or `templates/check-daily-plan.py`.

Optional second argument selects a non-`main` branch:

```bash
./setup-new-repo.sh git@github.com:cornjacket/ai-bar.git develop
```

### 2. Register it in `repos.yml`

```yaml
repos:
  - name: ai-foo
    remote: git@github.com:cornjacket/ai-foo.git
  - name: ai-bar
    remote: git@github.com:cornjacket/ai-bar.git
    branch: develop
    report_inactivity: false   # optional, default true
```

### 3. Add it to the daily routine's `sources` (remote `/schedule` flow only)

Direct `https://github.com` clones from inside the routine sandbox are blocked by an Anthropic egress TLS-inspection proxy. The platform pre-clones every declared `source` at `/home/user/<name>` via an authenticated local proxy, and `tools/sync.py` symlinks those into `tracked/`. So every entry in `repos.yml` must also be listed as a routine `source`, alongside `project-status` itself.

Open the routine at https://claude.ai/code/routines/trig_01BLz2BYyE95n44TCDKaFcnA and add `https://github.com/cornjacket/<repo>` to the sources list. Skip this step if you only run the pipeline locally (`tools/sync.py` will clone normally outside the sandbox).

Per-repo flags:

| flag | default | effect |
|---|---|---|
| `branch` | `main` | branch to clone/pull |
| `enabled` | `true` | when `false`, repo is skipped entirely |
| `report_inactivity` | `true` | when `false`, repo is omitted from `summary.md` on days it has no new work |

## Running an update cycle

```bash
python3 tools/run.py
```

Internally:

1. `tools/sync.py` clones any new repo and fast-forward-pulls the rest into `tracked/`.
2. `tools/new-work.py` classifies each repo as `ACTIVE`, `INACTIVE`, `INACTIVE_SUPPRESSED`, or `NOT_SYNCED`.
3. For each `ACTIVE` repo, one `claude -p` call produces a per-repo summary; all reportable `INACTIVE` repos collapse into a single `### No updates` block at the bottom of the day section.
4. If two or more repos are active, a final `claude -p` polish pass merges cross-repo themes.
5. The polished day section is prepended to `summary.md`.
6. `tools/aggregate-plans.py` overwrites `daily-plan-summary.md` with each tracked repo's current `daily-plan.md`, applying a weekend-tolerant staleness check (missing or stale plans are visibly flagged), and snapshots the result into `daily-plan-archive/YYYY-MM-DD.md`.
7. `tools/commit-state.py` advances `state.json` and commits `summary.md`, `daily-plan-summary.md`, `daily-plan-archive/`, and `state.json` together.

### Useful flags

```bash
python3 tools/run.py --dry-run       # skip claude -p; emit deterministic placeholders
python3 tools/run.py --skip-sync     # don't clone/pull (useful when iterating locally)
python3 tools/run.py --skip-commit   # don't advance state.json or commit
python3 tools/run.py --skip-plans    # don't rebuild daily-plan-summary.md
```

`--dry-run --skip-sync --skip-commit` exercises the full pipeline shape against your existing `tracked/` checkouts without spending any tokens or modifying state — handy for sanity-checking after editing prompts or templates.

## Daily tracking (scheduled runs)

**TL;DR:** scheduled at 12:13 UTC daily via Claude Code `/schedule`, runs `tools/daily.sh`, lands on `main` via auto-merge.

Both deliverables are regenerated by this daily run: `summary.md` gets a new day section (when there's activity), and `daily-plan-summary.md` is rebuilt from each repo's current `daily-plan.md` and snapshotted into `daily-plan-archive/YYYY-MM-DD.md`. So the plan archive grows by one dated file per scheduled run.

`tools/run.py` is meant to be run once a day. Pick whichever of the two paths below fits your environment.

### Option A — Claude Code `/schedule` (recommended)

The current daily routine is at https://claude.ai/code/routines/trig_01BLz2BYyE95n44TCDKaFcnA — fires daily at 12:13 UTC. To create a fresh routine, in an interactive Claude Code session run `/schedule` and supply the prompt:

```
bash /home/user/project-status/tools/daily.sh
```

Declare every repo in `repos.yml` as a routine `source` (alongside `project-status` itself); the platform pre-clones each one at `/home/user/<name>` and `tools/sync.py` symlinks them into `tracked/`. Use `/schedule list` to see active routines.

`tools/daily.sh` checks out a side branch named `auto/status-YYYY-MM-DD`, runs `tools/run.py` (which commits `summary.md` + `state.json` via `tools/commit-state.py`), and pushes the side branch. The `.github/workflows/auto-merge-status.yml` workflow then fast-forwards `main` to that branch and deletes it — see "Why a side branch?" below.

### Option B — local cron / systemd timer

If you'd rather run on your own machine, the `claude` CLI must be installed and authenticated for the user that owns the cron job. A minimal crontab entry:

```cron
# Run project-status every day at 09:00
0 9 * * * cd /path/to/project-status && /usr/bin/python3 tools/run.py && git push >> run.log 2>&1
```

Local cron has full git push access, so it can write to `main` directly — no side branch needed.

### Why a side branch? (Claude remote-routine limitation)

When a `/schedule` routine pushes git refs, it goes through a local proxy that authenticates as the Claude GitHub App. **GitHub Apps cannot push directly to a repo's default branch** (this is a platform-level restriction intended to enforce the PR-review flow for code changes). The proxy surfaces this rejection as a misleading "non-fast-forward" error, even when the push genuinely is a fast-forward.

Pushes to *non-default* branches work fine, so the daily routine pushes to `auto/status-YYYY-MM-DD` and the auto-merge workflow lands the change on `main` using the runner's standard `GITHUB_TOKEN` (which is not subject to the App restriction). Because we're publishing status updates rather than code, the human-in-the-loop intent of the App restriction doesn't apply — at worst we'd publish a wrong status, easily fixed by re-running.

## Other tools

- `python3 tools/diff.py <repo-name>` — print the new commit telemetry and `git --stat` since the recorded `last_commit` for one repo. Debugging aid.
- `./migrate-target-telemetry.sh <local-checkout>` — migrate an already-tracked repo off the old `log.md` workflow onto git telemetry. Idempotent.
- `python3 tools/new-work.py` — emit the structured per-repo report `run.py` consumes.

## Tests

```bash
python3 -m pytest tests/
```

Covers the deterministic layer (status classification, state advance, summary insertion, end-to-end pipeline shape via `--dry-run`). The two `claude -p` calls are out of scope by design — non-deterministic prose isn't worth asserting on.

## Files

- `repos.yml` — tracked-repo registry (committed)
- `state.json` — last seen commit + activity date per repo (committed)
- `summary.md` — retrospective rollup, newest day at the top (committed)
- `daily-plan-summary.md` — forward-looking plan rollup, overwritten daily (committed)
- `daily-plan-archive/` — dated snapshots of `daily-plan-summary.md` (`YYYY-MM-DD.md`), one per run; the append-only history of the plan deliverable, for reviewing plan quality over time (committed)
- `tracked/` — gitignored cache of cloned repos
- `tools/` — Python plumbing
- `prompts/` — `claude -p` prompt templates (`per-repo.md`, `polish.md`)
- `templates/` — files injected into tracked repos by `setup-new-repo.sh` (`daily-plan.md`, `claude-rule.md`, `check-daily-plan.py`)
- `tests/` — pytest suite for the deterministic layer
