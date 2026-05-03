# ai-project-status

Tracks development activity across a portfolio of `ai-*` repos and produces a single, daily-resolution `summary.md` with newest activity at the top. Each tracked repo maintains a `log.md` of task-granularity entries; this tool reads those logs plus `git --stat`, summarizes per repo via `claude -p`, and runs a cross-repo polish pass when more than one repo has new work.

For the architecture and rationale, see [`DESIGN.md`](DESIGN.md). For the rules an AI follows when running the update cycle, see [`CLAUDE.md`](CLAUDE.md).

## Setup

Requires `python3`, `git`, `claude` (the Claude Code CLI), and the `pyyaml` package.

```bash
git clone git@github.com:cornjacket/ai-project-status.git
cd ai-project-status
pip install pyyaml
```

## Adding a tracked repo

Two steps: bootstrap the target repo, then register it.

### 1. Bootstrap the target

```bash
./setup-new-repo.sh git@github.com:cornjacket/ai-foo.git
```

This clones `ai-foo` to a temp directory, drops in a starter `log.md`, injects a work-log rule block into `CLAUDE.md` (between `<!-- ai-project-status:begin -->` markers), commits, pushes, and cleans up. The rule tells Claude — when working in `ai-foo` — to maintain `log.md` at task granularity and announce every log edit and every commit in chat.

The script is idempotent: re-running on an already-bootstrapped repo is a no-op. Pass `--update` to refresh the rule block in place after editing `templates/claude-rule.md`.

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
3. For each `ACTIVE` repo, one `claude -p` call produces a per-repo summary; for each reportable `INACTIVE` repo, a deterministic one-liner `No activity for N days (last activity YYYY-MM-DD)`.
4. If two or more repos are active, a final `claude -p` polish pass merges cross-repo themes.
5. The polished day section is prepended to `summary.md`.
6. `tools/commit-state.py` advances `state.json` and commits `summary.md` + `state.json` together.

### Useful flags

```bash
python3 tools/run.py --dry-run       # skip claude -p; emit deterministic placeholders
python3 tools/run.py --skip-sync     # don't clone/pull (useful when iterating locally)
python3 tools/run.py --skip-commit   # don't advance state.json or commit
```

`--dry-run --skip-sync --skip-commit` exercises the full pipeline shape against your existing `tracked/` checkouts without spending any tokens or modifying state — handy for sanity-checking after editing prompts or templates.

## Daily tracking (scheduled runs)

`tools/run.py` is meant to be run once a day. Pick whichever of the two paths below fits your environment.

### Option A — Claude Code `/schedule` (recommended)

In an interactive Claude Code session, run `/schedule` and create a daily routine whose prompt is:

```
bash /home/user/ai-project-status/tools/daily.sh
```

Declare every repo in `repos.yml` as a routine `source` (alongside `ai-project-status` itself); the platform pre-clones each one at `/home/user/<name>` and `tools/sync.py` symlinks them into `tracked/`. Use `/schedule list` to see active routines.

`tools/daily.sh` checks out a side branch named `auto/status-YYYY-MM-DD`, runs `tools/run.py` (which commits `summary.md` + `state.json` via `tools/commit-state.py`), and pushes the side branch. The `.github/workflows/auto-merge-status.yml` workflow then fast-forwards `main` to that branch and deletes it — see "Why a side branch?" below.

### Option B — local cron / systemd timer

If you'd rather run on your own machine, the `claude` CLI must be installed and authenticated for the user that owns the cron job. A minimal crontab entry:

```cron
# Run ai-project-status every day at 09:00
0 9 * * * cd /path/to/ai-project-status && /usr/bin/python3 tools/run.py && git push >> run.log 2>&1
```

Local cron has full git push access, so it can write to `main` directly — no side branch needed.

### Why a side branch? (Claude remote-routine limitation)

When a `/schedule` routine pushes git refs, it goes through a local proxy that authenticates as the Claude GitHub App. **GitHub Apps cannot push directly to a repo's default branch** (this is a platform-level restriction intended to enforce the PR-review flow for code changes). The proxy surfaces this rejection as a misleading "non-fast-forward" error, even when the push genuinely is a fast-forward.

Pushes to *non-default* branches work fine, so the daily routine pushes to `auto/status-YYYY-MM-DD` and the auto-merge workflow lands the change on `main` using the runner's standard `GITHUB_TOKEN` (which is not subject to the App restriction). Because we're publishing status updates rather than code, the human-in-the-loop intent of the App restriction doesn't apply — at worst we'd publish a wrong status, easily fixed by re-running.

## Other tools

- `python3 tools/diff.py <repo-name>` — print the new `log.md` lines and `git --stat` since the recorded `last_commit` for one repo. Debugging aid.
- `python3 tools/new-work.py` — emit the structured per-repo report `run.py` consumes.

## Tests

```bash
python3 -m pytest tests/
```

Covers the deterministic layer (status classification, state advance, summary insertion, end-to-end pipeline shape via `--dry-run`). The two `claude -p` calls are out of scope by design — non-deterministic prose isn't worth asserting on.

## Files

- `repos.yml` — tracked-repo registry (committed)
- `state.json` — last seen commit + activity date per repo (committed)
- `summary.md` — the deliverable, newest day at the top (committed)
- `tracked/` — gitignored cache of cloned repos
- `tools/` — Python plumbing
- `prompts/` — `claude -p` prompt templates (`per-repo.md`, `polish.md`)
- `templates/` — files injected by `setup-new-repo.sh` (`log.md`, `claude-rule.md`)
- `tests/` — pytest suite for the deterministic layer
