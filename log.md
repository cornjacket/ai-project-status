# Work log

Task-granularity record of work in this repo, indexed by short commit hash. See `CLAUDE.md` → "Work log (log.md)" for the rule. Each entry is one line:

```
- **YYYY-MM-DD** — <one or two sentences of what changed and why>. Task: `<task-name>`. [Subtask: `<subtask-name>`.] Commit: `<short-hash>`.
```

Newest entries at the bottom.

- **2026-05-02** — Made `tools/sync.py` reuse pre-cloned source repos at `/home/user/<name>` when running inside a Claude remote routine, since direct `https://github.com` clones are intercepted by an Anthropic egress TLS-inspection proxy and return 401 even for public repos. End-to-end verified by re-arming `trig_01BLz2BYyE95n44TCDKaFcnA` with `document-analyzer` declared as a second source: sync linked the pre-cloned tree, `tools/run.py --skip-commit` produced a real `## 2026-05-02` section in `summary.md`, exit 0. Task: `remote-routine`. Subtask: `egress-proxy-fix`. Commit: `0793a90`.
