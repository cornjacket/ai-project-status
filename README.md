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

## Removing a tracked repo

Two levels. **Soft removal** stops the rollup from including the repo but leaves it bootstrapped. **Hard removal** also un-bootstraps the target so it no longer carries any project-status machinery. Hard removal builds on soft — do those steps first.

### Soft removal — stop tracking

1. **`repos.yml`** — set `enabled: false` on the entry, or delete it. `enabled: false` keeps a record of what was once tracked; deleting is cleaner when the repo is gone for good.
2. **Regenerate the umbrella `CLAUDE.md`** — `python3 tools/gen-umbrella-claude.py`, so the workspace-root roster drops the repo. Local-only, deliberately not part of `tools/run.py`.
3. **Remove it from the daily routine's `sources`** — see below. Skipping this leaves the platform pre-cloning a repo that nothing reads.

Optional housekeeping, cosmetic and safe to skip:

- Prune the repo's key from `state.json`. Nothing prunes it automatically, so stale keys accumulate.
- `rm -rf tracked/<name>` — `sync.py` clones and pulls but never prunes. It's a cache; re-created on demand.

Leave `summary.md` and `daily-plan-archive/` alone. They are the historical record and should keep showing the repo for the period it was actually tracked.

### Hard removal — un-bootstrap the target

Reverses `setup-new-repo.sh`. There is no `--remove` flag, so this is done by hand in a session rooted at the target repo, on a clean tree. Remove exactly these five artifacts:

| artifact | action |
|---|---|
| `CLAUDE.md` | delete the block between `<!-- ai-project-status:begin -->` and `<!-- ai-project-status:end -->`, markers included |
| `project-status-guide.md` | `git rm` |
| `daily-plan.md` | `git rm` |
| `.claude/hooks/check-daily-plan.py` | `git rm` |
| `.claude/settings.json` | remove the `SessionStart` entry running `check-daily-plan.py`; `git rm` the file only if it holds nothing else |

Then **add a `.project-status-ignore` file at the repo root.** Without it, the user-level `hooks/check-repo-bootstrap.py` hook sees a workspace repo whose `CLAUDE.md` has no project-status block and nudges you to bootstrap it at every session start — an un-bootstrapped repo is indistinguishable from a never-bootstrapped one except by that file.

**Do not touch other generators' blocks.** A target may also carry a `<!-- task-system:begin -->` block and `.claude/skills/` from `create-project-system`. Those are unrelated machinery and must survive.

### Removing it from the daily routine's `sources`

The mirror of step 3 in "Adding a tracked repo". Routine ID `trig_01BLz2BYyE95n44TCDKaFcnA`. Use the `RemoteTrigger` tool: `action: "get"` to fetch the current config, drop the `{"git_repository": {"url": "https://github.com/cornjacket/<repo>"}}` entry from `session_context.sources`, then `action: "update"` with the **entire** `job_config` — send the whole thing rather than relying on partial-merge semantics, which clobbers other fields. Verify at https://claude.ai/code/routines/trig_01BLz2BYyE95n44TCDKaFcnA.

`repos.yml` and the routine's `sources` are two separate registries and neither one implies the other: `repos.yml` decides what the code iterates, `sources` decides what the platform pre-clones into the sandbox. Removing only the first leaves a repo being cloned daily for nothing; removing only the second breaks the run for a repo still listed in `repos.yml`.

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
6. `tools/aggregate-plans.py` overwrites `daily-plan-summary.md` with each tracked repo's current `daily-plan.md`, applying a weekend-tolerant staleness check (missing or stale plans are visibly flagged), and snapshots the result into `daily-plan-archive/YYYY-MM-DD.md`. The file opens with an **At a glance** table — one row per repo (priority band, plan freshness, today's focus, days since the last commit), repos with a fresh plan first and each group ordered by band, so the portfolio is scannable before you read any section. The per-repo sections below follow that same order, so scanning the table and reading down the page are the same motion.
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
- `python3 tools/check-targets.py` — report tracked repos whose injected `CLAUDE.md` block or `project-status-guide.md` no longer matches `templates/`, and exit non-zero if any have. Run `tools/sync.py` first; it reads the `tracked/` checkouts. Drift is silent otherwise: `setup-new-repo.sh` always refreshes the guide and hook but only rewrites the `CLAUDE.md` block with `--update`, so a repo can carry a current guide beside a months-old kernel. The same finding is repeated in that repo's section of `daily-plan-summary.md`, which is the copy you actually read every day.
- `hooks/check-repo-bootstrap.py` — a **user-level** `SessionStart` hook (registered in `~/.claude/settings.json`). It nudges when you open a git repo under the workspace root whose `CLAUDE.md` has no project-status block, i.e. one that was never bootstrapped — the case a per-repo hook can't catch, because an un-bootstrapped repo has no hook. Silent for bootstrapped repos, for project-status itself, outside the workspace root (override with `PROJECT_STATUS_WORKSPACE`), and in any repo containing a `.project-status-ignore` file — the opt-out for deliberately untracked repos.
- `python3 tools/check-pending.py [--all] [--dirty-only] [--path DIR]` — report **uncommitted and unpushed** work for every repo in the workspace, run from anywhere. This is the companion to `replan.py`: no editor window can answer "did I commit and push everything?", because the sibling repos are separate git repos and aren't in that window's scope (VS Code needs the umbrella opened as a multi-root workspace *and* `git.repositoryScanMaxDepth ≥ 2` before it sees a nested worktree checkout). Reports both kinds of pending work, since tracking only edits would call a committed-but-never-pushed repo clean, and a branch with no upstream is reported rather than assumed clean. **Worktrees come from `git worktree list`**, not from directory shape, so one parked in a sibling directory or outside the workspace still gets checked. Roster is `repos.yml` plus project-status itself; `--all` sweeps every git repo under the workspace root, honoring the `.project-status-ignore` opt-out. Exits 1 when anything is pending, so it doubles as a gate.
- `python3 tools/replan.py [--date D] [--only a,b] [--force] [--dry-run] [--report]` — draft next-day `daily-plan.md` files for human review. One `claude -p` per tracked repo, run with cwd = **that repo's own local checkout**, so its `CLAUDE.md`, skills, and task system load — the context an umbrella session structurally lacks. The agent *reads* intent rather than inventing it: it derives the plan from the repo's task state plus its git log, and keeps the current plan (re-dated) whenever the next step isn't unambiguous. It runs read-only, so it cannot edit the tasks it reads. Each plan is rewritten **in place and left uncommitted**, so git is the review surface — the drafted plans are exactly the modified files in VS Code's Source Control view, and the run ends by telling you to review, commit, and push. **Nothing is ever staged, committed, or pushed**, and a `daily-plan.md` that already has uncommitted changes is never clobbered without `--force`. Re-runnable: a repo whose plan is already dated for the target is skipped and per-repo failures are isolated, so a batch that dies partway (an expired login, say) resumes without re-spending calls. Local-only and deliberately not part of `tools/run.py` — it writes to checkouts the routine sandbox doesn't have.
- `python3 tools/gen-umbrella-claude.py [--path DIR] [--dry-run]` — (re)generate the **umbrella** `CLAUDE.md` at the workspace root, the directory above every repo checkout. That directory isn't a git repo, so the file is a build artifact: this tool owns the roster block (name · one-line purpose · local path, sourced from `repos.yml` + each repo's `daily-plan.md`) and leaves everything outside the `<!-- project-status:begin/end -->` markers hand-written. Local-only and deliberately not part of `tools/run.py` — the umbrella path doesn't exist in the routine sandbox. Re-run it when a repo is added to or removed from `repos.yml`.

## Tests

```bash
python3 -m pytest tests/
```

Covers the deterministic layer (status classification, state advance, summary insertion, end-to-end pipeline shape via `--dry-run`, and — for `replan.py` — date math, checkout resolution, response parsing, resumability, and apply's guards). The `claude -p` calls themselves are out of scope by design — non-deterministic prose isn't worth asserting on; the tests stub the call and assert on everything around it.

## Files

- `repos.yml` — tracked-repo registry (committed)
- `state.json` — last seen commit + activity date per repo (committed)
- `summary.md` — retrospective rollup, newest day at the top (committed)
- `daily-plan-summary.md` — forward-looking plan rollup, overwritten daily (committed)
- `daily-plan-archive/` — dated snapshots of `daily-plan-summary.md` (`YYYY-MM-DD.md`), one per run; the append-only history of the plan deliverable, for reviewing plan quality over time (committed)
- `tracked/` — gitignored cache of cloned repos
- `.replan-last-run.json` — gitignored ledger of `tools/replan.py`'s last batch, so `--report` can re-print it; the plans themselves live in the repos that own them
- `tools/` — Python plumbing
- `prompts/` — `claude -p` prompt templates (`per-repo.md`, `polish.md`, `replan.md`)
- `templates/` — files injected into tracked repos by `setup-new-repo.sh` (`daily-plan.md`, `claude-rule.md`, `project-status-guide.md`, `check-daily-plan.py`). `claude-rule.md` is the **kernel** spliced into each repo's `CLAUDE.md` — only rules that would be too late if loaded on demand; `project-status-guide.md` is the on-demand reference half, installed at the tracked repo's root and read when writing a commit message or a plan. `tests/test_templates.py` holds the kernel to a size ceiling.
- `tests/` — pytest suite for the deterministic layer
