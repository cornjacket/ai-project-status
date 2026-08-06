# Task: Mothball project-status

- **Created:** 2026-08-06
- **Status:** IN PROGRESS
- **Owner:** _unassigned_

## Goal

Retire `project-status`, superseded by `create-git-workspace` (which has already
generated `dev-workspace/` and `personal-workspace/`, and taken over the rollup —
`dev-workspace/summary.md` and `dev-workspace/daily-plan-summary.md` are live).

Stop the daily remote routine, strip project-status machinery from every repo
that still carries it, mark the GitHub repo archived. **The remote is kept** —
`summary.md` and `daily-plan-archive/` hold historical value and must stay
readable. Deleting the local checkout is done by hand, outside this task.

## Order matters

Everything requiring the repo's own tooling, or requiring a push, happens before
the local checkout is removed. Once it's gone, so is the ability to push, and the
remote becomes the only copy.

## Steps

### 1. Turn off the remote routine — DONE 2026-08-06

Routine `trig_01BLz2BYyE95n44TCDKaFcnA`, cron `13 12 * * *`.

- [x] `RemoteTrigger` `action: "update"`, full `job_config`, `enabled: false`.
      **Emptying `sources` is not enough** — the trigger keeps firing on its cron
      and fails, since `project-status` is itself a source. Disabling the trigger
      is what actually stops it. Renamed to `project-status daily (mothballed
      2026-08-06)`. `job_config` and `sources` left intact for the record.
- [ ] Confirm on 2026-08-07 that it did not fire (`next_run_at` still showed a
      timestamp after disabling; `enabled: false` is the authoritative field).

### 2. Strip project-status machinery from tracked repos — DONE 2026-08-06

The workspace migration to `dev-workspace/` had already cleared most repos. Only
two still carried it:

- [x] `dev-workspace/second-brain-test` — `be7239a`
- [x] `dev-workspace/create-ai-builder` `workspace-mgmt` worktree — `a0d1f2a`
      (its `main` worktree was already clean)

Already clean, no action: second-brain-devkit, create-project-system,
customer-req-responder, create-ai-builder/main, captains-log (offboarded
2026-08-03, `ff066ec`).

Artifacts removed per repo: the `<!-- ai-project-status:begin/end -->` block in
`CLAUDE.md`, `project-status-guide.md`, `daily-plan.md`,
`.claude/hooks/check-daily-plan.py`, the `SessionStart` entry in
`.claude/settings.json`; plus a `.project-status-ignore` added. Other
generators' blocks (`<!-- task-system:begin -->`, `.claude/skills/`) left alone.

### 3. Unregister the user-level hook

- [ ] Remove the `SessionStart` entry in `~/.claude/settings.json` running
      `project-status/hooks/check-repo-bootstrap.py`. Without this, every session
      in the workspace errors at startup once the checkout is deleted.

### 4. Freeze the umbrella CLAUDE.md

`~/src/github.com/cornjacket/CLAUDE.md` is a build artifact of
`tools/gen-umbrella-claude.py`.

- [ ] Strip the generated-artifact header, the `<!-- project-status:begin/end -->`
      markers, and the "do not hand-edit" notice, so it reads as a hand-owned
      file. Keep the content.
- [ ] Rewrite "Where to look first" — it points at
      `project-status/daily-plan-summary.md`, `summary.md`, `repos.yml`, and two
      tool commands that will not exist locally. Point at `dev-workspace/`
      instead.

### 5. Mark the repo mothballed

- [ ] `README.md`: banner at the top — mothballed 2026-08-06, superseded by
      [`create-git-workspace`](https://github.com/cornjacket/create-git-workspace),
      remote retained as historical record.
- [ ] GitHub repo description: same, one line.
- [ ] Final push.
- [ ] **Archive on GitHub** (Settings → Archive this repository) — read-only,
      with a banner on every page. Stronger than a README line alone, and must
      come after the final push, since archiving blocks writes.

## Not in scope

**Deleting the local checkout is done by hand**, after every step above is
complete and `git status` is clean with nothing unpushed. See the note at the
bottom of this file.

## Done when

The routine no longer fires, no repo in the workspace carries project-status
machinery or hooks, no session errors at startup, and the GitHub repo is archived
and clearly marked superseded — with its history still readable.

## Deleting the local checkout (manual, last)

Only after steps 1–5 are done. Two things to verify first, because after this the
GitHub remote is the only copy:

```bash
cd ~/src/github.com/cornjacket/project-status
git status --porcelain        # must be empty
git log origin/main..HEAD     # must be empty — nothing unpushed
```

Then:

```bash
rm -rf ~/src/github.com/cornjacket/project-status
```

Re-clone any time with `git clone https://github.com/cornjacket/project-status`
— archiving makes it read-only, not private or deleted.

## Related

- `README.md` → "Removing a tracked repo" (the hard-removal procedure)
- `CLAUDE.md` → "Remove a tracked repo"
- Precedent: captains-log offboarding, `ff066ec` / `8860251`
