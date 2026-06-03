# Task: Migrate from `log.md` to automated Git telemetry

- **Created:** 2026-05-30
- **Status:** DONE — executed 2026-06-02 on branch `log-to-git-telemetry-migration` (8 commits). Deferred second-brain item remains open.
- **Owner:** David Taylor
- **Scope decision:** Full coherent migration (engine + setup script + tests + docs).

## Goal

Eliminate duplicate logging overhead. Deprecate `log.md` entirely for
**backward-looking** reporting and replace it with automated, high-level Git
telemetry driven by `CLAUDE.md` commit-message discipline.

**Hard constraint:** the `daily-plan.md` mechanism (forward-looking planning)
must remain COMPLETELY untouched. That includes:
- `tools/aggregate-plans.py`
- `daily-plan-summary.md`
- the "Daily plan (daily-plan.md)" section inside `templates/claude-rule.md`
- `templates/daily-plan.md`, `templates/check-daily-plan.py`
- the `SessionStart` hook + `.claude/settings.json` merge in `setup-new-repo.sh`

## Locked-in decisions

1. **Commit window: range-based default + configurable `--since` override.**
   Keep `last_commit..HEAD` (from `state.json`) as the primary selector — this
   preserves the durable per-repo state and the "missed a day → catch up next
   run" recovery (DESIGN.md:105) and keeps the pipeline deterministic. Add an
   opt-in `--window` / `--since` override for ad-hoc 24h-style queries. Do NOT
   make `--since="24 hours ago"` the primary selector (it silently drops work on
   any skipped daily run and reintroduces wall-clock non-determinism).
2. **Scope: full coherent migration** — also update `setup-new-repo.sh`, the
   tests, and the prose docs so nothing still references `log.md`.
3. **second-brain: deferred** (see To-do / Deferred below). Build it later as a
   one-off singleton; do NOT add it to `repos.yml` in this pass.

## Part 1 — Inventory of current targets (DONE — for reference)

Targets are registered ONLY in `repos.yml` (by remote URL). Currently tracked:

| name | remote | branch | flags |
|------|--------|--------|-------|
| `ai-builder` | https://github.com/cornjacket/ai-builder.git | main | defaults |
| `gsd-walkthru` | https://github.com/cornjacket/gsd-walkthru.git | main | defaults |
| `customer-req-responder` | https://github.com/cornjacket/customer-req-responder.git | main | defaults |

`state.json` confirms these same three. `second-brain` is NOT currently tracked.

## Part 2 — Update the monitoring engine

Key fact: change detection is ALREADY git-native — `gather_report()`
(`tools/_lib.py:113`) classifies ACTIVE/INACTIVE from `last_commit != HEAD`, not
from `log.md`. `log.md` is used ONLY to extract narrative content for ACTIVE
repos. So the migration is narrow and well-contained.

1. New helper in `tools/_lib.py`: `git_telemetry(repo_dir, rev_range)` →
   returns `list[{hash, title, context, impact, body}]`.
2. **Edge-case-safe parsing** (multi-line bodies): do NOT use the bare
   `--pretty=format:"%s%n%b"` (unparseable across multiple commits because
   bodies are multi-line). Use ASCII control-char delimiters instead:
   `--pretty=format:"%x1e%h%x1f%s%x1f%b"`
   - split stdout on `\x1e` (record separator) → per-commit records
   - split each record on `\x1f` (unit separator) → `[hash, subject, body]`
   - parse `%b` for the `- [Context]:` and `- [Impact]:` lines
   This honors the requested `%s` + `%b` intent while cleanly handling
   multi-line `[Context]`/`[Impact]` bodies.
3. In `gather_report()`: replace `entry["log_diff"]` (the
   `git diff <last>..HEAD -- log.md` at `tools/_lib.py:154`) with
   `entry["commit_telemetry"]`. KEEP `file_stat` and `commit_list`
   (`_lib.py:155-156`) — they are already git telemetry.
4. Update everything that consumes `log_diff` to display/feed Title / [Context] /
   [Impact]:
   - `tools/new-work.py:36-37` ("### log.md additions" → telemetry block)
   - `tools/run.py:42-47` (`format_slice` packs `log_diff` → telemetry)
   - `prompts/per-repo.md:4` ("the unified diff of `log.md`" → git telemetry)
   - `tools/diff.py:19-20` (debug aid)

## Part 3 — Update the `CLAUDE.md` blueprint template

In `templates/claude-rule.md`:
- DELETE the "Work log (log.md)" section (rules 1–5).
- KEEP the entire "Daily plan (daily-plan.md)" section VERBATIM.
- INSERT a new "Knowledge Extraction & Git Automation" section.

**Code-repo schema:**
```
<domain>(<scope>): <high-level functional summary>
- [Context]: Why this was done / what was learned.
- [Impact]: How it alters the project or system behavior.
```
Rule: title summarizes the overall functional change / architectural decision,
NOT individual file names. Automated staging + `git commit -m` must run before
session close.

**Second-brain schema (deferred — see below):**
```
docs(<scope>): <high-level functional summary of knowledge captured>
- [Context]: Brief summary of the core engineering lesson or telemetry recorded.
- [Impact]: How this note updates our global engineering principles.
```
Rule: auto-analyze markdown diffs, format the commit, and execute the Git commit
without prompting for human confirmation.

## Part 4 — `migrate-target-telemetry.sh`

Portable bash (`set -euo pipefail`), takes a target dir path:
1. Verify it's a valid git repo (`git -C "$dir" rev-parse`).
2. Remove `log.md`: `git rm -f log.md` if tracked, else `rm -f` if untracked,
   else skip.
3. `CLAUDE.md`:
   - if present: strip the old `<!-- ai-project-status:begin/end -->` block and
     any stray "append/write to log.md" lines, then inject the new
     "Knowledge Extraction & Git Automation" block (reuse the existing marker
     mechanism from `setup-new-repo.sh`).
   - if absent: create it with the new rules.
4. Idempotent. `--second-brain` flag (or auto-detect basename == `second-brain`)
   selects the docs() schema.
Handle edge cases gracefully (multi-line commit bodies, missing files).

## Part 5 — Coherence items (full-scope decision)

- **`setup-new-repo.sh`**: stop creating `log.md` and stop referencing
  `TEMPLATE_LOG`; inject the new git-automation block instead of the old
  work-log block. (Otherwise onboarding re-adds what the migration deletes.)
- **Tests**: `tests/conftest.py` `commit_log()` writes `log.md` and
  `tests/test_lib.py` asserts on `log_diff` — update to use structured commit
  messages and assert on `commit_telemetry`.
- **Docs**: update `DESIGN.md`, this repo's `CLAUDE.md`, and `README.md` so they
  describe git telemetry as the source of truth instead of `log.md`.
- Consider removing/repurposing `templates/log.md`.

## To-do checklist (superseded by "Execution plan" below — kept as a flat coverage map)

- [x] Part 2: add `git_telemetry()` helper + delimiter parsing to `_lib.py` (uses `%B` not `%s/%b` — see note below)
- [x] Part 2: swap `log_diff` → `commit_telemetry` in `gather_report()`
- [x] Part 2: update `new-work.py`, `run.py` `format_slice`, `diff.py`, `prompts/per-repo.md` (+ shared `format_telemetry()` helper)
- [x] Part 3: rewrite work-log section of `templates/claude-rule.md` → git-automation (daily-plan section kept byte-identical)
- [x] Part 4: write `migrate-target-telemetry.sh`
- [x] Part 5: update `setup-new-repo.sh` (drop log.md, inject new block)
- [x] Part 5: update tests (`conftest.py`, `test_lib.py`, **and `test_run.py`** — third file the spec missed)
- [x] Part 5: update docs (`DESIGN.md`, `CLAUDE.md`, `README.md`), removed `templates/log.md` AND this repo's own root `log.md`
- [x] Run `pytest` and verify the suite passes (155 passed, was 153 + 2 new tests)
- [x] Add `--window` / `--since` override + wire through CLI (`run.py`, `new-work.py`)

### Execution notes / deviations from spec
- **`%B`, not `%s%n%b`.** Live testing exposed that git treats the entire first
  paragraph as the subject `%s`, so the schema's no-blank-line `[Context]`/
  `[Impact]` lines got swallowed into `%s` and `%b` came back empty. Switched to
  the raw `%B` field and parse title/markers ourselves — robust whether or not
  the author leaves a blank line after the title. (Verified on all 3 variants.)
- **`--since` semantics.** When set, classification flips to "ACTIVE iff the time
  window has commits" (base = last commit before cutoff, `EMPTY_TREE` if none),
  independent of `state.json`. Default path unchanged.
- **Environmental, not a regression:** `diff.py`/`gather_report` crash if
  `state.json`'s `last_commit` isn't present in the local `tracked/` clone
  (stale state vs. re-clone). The old `git diff <base>..HEAD` path failed
  identically. Left as-is (pre-existing, out of scope) — flagged as a follow-up.
- Verified on real data: parsed 299 live `ai-builder` commits; old-style
  messages degrade gracefully to title-only.

## Execution plan

Ordered, dependency-aware sequence with a verification point per step. Each
numbered step is intended to be one atomic commit. Do them in order — later steps
depend on the engine contract (`commit_telemetry`) established in Step 2.

**Verified groundings (2026-06-02):** spec `file:line` refs are accurate.
Additional finds: tests touch **three** files, not two — `tests/test_run.py:80-97`
also asserts on `log_diff` / `## log.md additions`. The `commit_log()` helper
(`tests/conftest.py:30`) already commits; migrating it mainly means changing the
*commit message* it writes (and the assertions), not adding a commit step.

### Step 0 — Branch + green baseline (gate)
- Create a working branch off `main`.
- Run `pytest -q` and confirm the suite is **green before** any change. This is
  the regression baseline; if it's already red, stop and surface it.
- **Verify:** suite passes; note the count.

### Step 1 — Engine: add `git_telemetry()` helper (Part 2.1–2.2)
- Add `git_telemetry(repo_dir, rev_range)` to `tools/_lib.py` using the
  control-char format `--pretty=format:"%x1e%h%x1f%s%x1f%b"`; split on `\x1e`
  then `\x1f`; parse `%b` for `- [Context]:` / `- [Impact]:` lines. Return
  `list[{hash, title, context, impact, body}]`.
- Pure addition — does not yet touch `gather_report()`. No consumer depends on it
  yet, so nothing breaks.
- **Verify:** ad-hoc — call it against this repo's own history (multi-line body
  commit) in a scratch `python3 -c`; confirm multi-commit + multi-line bodies
  parse cleanly. (No pytest dependency yet.)

### Step 2 — Engine: swap `log_diff` → `commit_telemetry` (Part 2.3) ⟵ contract change
- In `gather_report()` (`tools/_lib.py:154`): replace the `log_diff` field with
  `entry["commit_telemetry"] = git_telemetry(d, f"{last}..HEAD")`. Update the
  field init at `:139` and the docstring field list at `:118`.
- **KEEP** `file_stat` and `commit_list` (`:155-156`) untouched.
- This **breaks** `new-work.py`, `run.py`, `diff.py`, and the tests until Steps
  4–5 — expected. That's why this is its own commit and the consumers follow.
- **Verify:** `python3 -c "from tools._lib import gather_report"` import-clean;
  full pytest will be red here (consumers/tests not yet updated) — acceptable
  intermediate state, do not commit Steps 2+4+5 separately if you want every
  commit green; otherwise group 2/4/5. (Decision below.)

### Step 3 — Engine: `--window` / `--since` override (promoted from checklist tail)
- Add the opt-in `--since` / `--window` override discussed in Locked decision #1
  (range-based stays the **primary** selector; override is ad-hoc only). Thread
  it from the CLI down into the rev-range passed to `git_telemetry`.
- Belongs here with the engine, not at the end — it changes the same `_lib`
  rev-range surface Step 2 just established.
- **Verify:** run-cycle entrypoint accepts the flag; absent flag → identical
  range-based behavior as before (default path unchanged).

### Step 4 — Update the four consumers (Part 2.4)
- `tools/new-work.py:36-37` — "### log.md additions" block → render Title /
  [Context] / [Impact] from `commit_telemetry`.
- `tools/run.py:41-47` (`format_slice`) — pack `commit_telemetry` instead of
  `log_diff` into the `{{REPO_SLICE}}` prompt.
- `tools/diff.py:19-20` — debug aid; show telemetry instead of `log.md` diff.
- `prompts/per-repo.md:4` — "the unified diff of `log.md`" → "git telemetry".
- **Verify:** `python3 tools/new-work.py` and `python3 tools/diff.py <repo>` run
  without error against synced `tracked/` repos.

### Step 5 — Update tests (Part 5 tests) ⟵ depends on Step 2 contract
- `tests/conftest.py:30` `commit_log()` — write structured commit **messages**
  (`<domain>(<scope>): … / - [Context]: / - [Impact]:`) instead of (or in
  addition to) appending to `log.md`.
- `tests/test_lib.py` — replace `log_diff` assertions (`:42,63,101-102`) with
  `commit_telemetry` assertions; keep `file_stat` assertions.
- `tests/test_run.py:80-97` — replace `log_diff` / `## log.md additions`
  fixtures + assertions with telemetry equivalents.
- **Verify (primary gate):** `pytest -q` is **green** again. This is the moment
  the engine migration is proven end-to-end.

> **Commit grouping note:** Steps 2, 4, and 5 form one logically atomic contract
> change. Either (a) keep them as three commits and accept a transient red middle
> commit, or (b) squash 2+4+5 into a single "swap log.md → git telemetry" commit
> so every commit on the branch is green. Recommend (b).

### Step 6 — Rewrite the blueprint template (Part 3)
- `templates/claude-rule.md`: DELETE the "Work log (log.md)" section (rules 1–5),
  KEEP the "Daily plan (daily-plan.md)" section **verbatim**, INSERT the new
  "Knowledge Extraction & Git Automation" section with the code-repo schema.
- Independent of the engine — could be done in parallel, but sequence it here so
  Step 7's migration script can reuse the finalized block text.
- **Verify:** diff shows daily-plan section byte-identical; new section present.

### Step 7 — Write `migrate-target-telemetry.sh` (Part 4)
- Portable bash `set -euo pipefail`, arg = target dir. rev-parse guard; remove
  `log.md` (`git rm -f` / `rm -f` / skip); strip old marker block + stray
  log.md lines from `CLAUDE.md` and inject the Step 6 block via the existing
  marker mechanism; idempotent; `--second-brain` flag stub (basename
  auto-detect) but **second-brain content stays deferred**.
- **Verify:** run against a throwaway copy of a tracked repo twice — second run
  is a no-op (idempotency); `log.md` gone; CLAUDE.md block swapped.

### Step 8 — Update `setup-new-repo.sh` (Part 5)
- Drop `TEMPLATE_LOG` (`:25`), the `log.md` creation block (`:63-68`), and
  `log.md` from the `git add` / commit message (`:143-145`). Inject the new
  git-automation block instead of the work-log block (`:77-93`). Leave the
  daily-plan + SessionStart hook merge untouched.
- Must follow Step 6 (reuses the same block text).
- **Verify:** `./setup-new-repo.sh` against a scratch remote (or dry inspection)
  no longer creates `log.md`; CLAUDE.md gets the new block.

### Step 9 — Docs + leftover template (Part 5 docs)
- Update `DESIGN.md`, this repo's `CLAUDE.md`, and `README.md` to describe git
  telemetry as the source of truth instead of `log.md`.
- Decide on `templates/log.md` — remove or repurpose.
- Parallelizable; no code depends on it. Can be fanned out to subagents.
- **Verify:** `grep -rn "log\.md" --include=*.md .` returns only intentional
  historical references (e.g. this task file, summary.md history).

### Step 10 — Full-suite + smoke verification (final gate)
- `pytest -q` green.
- Dry run of the orchestrator path (`python3 tools/run.py --dry-run` if
  supported, else `new-work.py`) against synced repos — no tracebacks.
- `grep -rn "log_diff" tools/ tests/` returns nothing.
- **Verify:** all green → ready to merge.

### Dependency summary
```
0 ─► 1 ─► 2 ─► 4 ─► 5(GATE) ─► 10(GATE)
          └─► 3 ┘
6 ─► 7
6 ─► 8
9 (independent)  ───────────────► 10
```
Step 2 is the linchpin contract change; 4 and 5 must follow it. 6→7 and 6→8
share the template block text. 3 rides with the engine. 9 is free-floating.
Everything funnels into the Step 10 gate.

## Deferred

- [ ] **second-brain (singleton).** Add `templates/claude-rule-second-brain.md`
      with the `docs(<scope>)` schema + auto-commit-without-confirmation rule.
      Wire `migrate-target-telemetry.sh --second-brain` (or basename auto-detect)
      to select it. There will only ever be ONE second-brain repo. Decide at that
      time whether to also register it in `repos.yml`.
