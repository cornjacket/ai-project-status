# Work log

Task-granularity record of work in this repo, indexed by short commit hash. See `CLAUDE.md` → "Work log (log.md)" for the rule. Each entry is one line:

```
- **YYYY-MM-DD** — <one or two sentences of what changed and why>. Task: `<task-name>`. [Subtask: `<subtask-name>`.] Commit: `<short-hash>`.
```

Newest entries at the bottom.

- **2026-05-02** — Made `tools/sync.py` reuse pre-cloned source repos at `/home/user/<name>` when running inside a Claude remote routine, since direct `https://github.com` clones are intercepted by an Anthropic egress TLS-inspection proxy and return 401 even for public repos. End-to-end verified by re-arming `trig_01BLz2BYyE95n44TCDKaFcnA` with `document-analyzer` declared as a second source: sync linked the pre-cloned tree, `tools/run.py --skip-commit` produced a real `## 2026-05-02` section in `summary.md`, exit 0. Task: `remote-routine`. Subtask: `egress-proxy-fix`. Commit: `0793a90`.
- **2026-05-03** — Added `tools/daily.sh` and `.github/workflows/auto-merge-status.yml` to route the daily routine's status commit through a `auto/status-YYYY-MM-DD` side branch that the workflow fast-forwards onto `main`, working around the GitHub App's inability to push directly to the default branch. README rewritten to document the new architecture and the underlying limitation. Task: `remote-routine`. Subtask: `side-branch-flow`. Commit: `f9d36ca`.
- **2026-05-03** — Added `ai-builder` to `repos.yml` and the daily routine's `sources` list so the platform pre-clones it for tomorrow's run. Task: `add-tracked-repo`. Commit: `8f3fb3c`.
- **2026-05-07** — Corrected stale "09:13 UTC" references in README.md to "12:13 UTC", matching the routine's actual `cron_expression: 13 12 * * *` (verified via `RemoteTrigger get` for `trig_01BLz2BYyE95n44TCDKaFcnA`); 12:13 UTC = 5:13 AM PDT, the intended user-facing schedule. Two refs fixed (lines 96 + 102). Task: `fix-stale-utc-time`. Commit: `bd01159`.
- **2026-05-07** — Tightened daily-plan Rule 4 in `templates/claude-rule.md` from "End-of-session sign-off rule" to "Forward-write rule": now triggers only when the user *explicitly* asks to plan tomorrow (or signs off with forward-planning intent), not on ambiguous "let's stop here" signoffs. Companion to the user-global `TZ=America/Los_Angeles` fix in `~/.claude/settings.json` — together they remove the off-by-one daily-plan dating bug that was filing tomorrow's-plan-of-tomorrow when sessions ran past 17:00 PDT (UTC rollover) and Claude misread "let's stop" as a signoff. Friday → Monday weekend rule preserved. Will propagate via `setup-new-repo.sh --update` to tracked repos that have the rule block (currently gsd-walkthru). Task: `tighten-daily-plan-rule-4`. Commit: `_pending_`.
