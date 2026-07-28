# Task: Streamline the tracked-repo CLAUDE.md block + a more robust per-repo summary

- **Created:** 2026-07-27
- **Status:** DONE — 2026-07-27. Part 1 (kernel/guide split) propagated to all
  six tracked repos; Part 2 (portfolio-at-a-glance table) shipped, plus a
  two-layer guard against repos falling out of the system.
- **Owner:** _unassigned_

## Goal

Two related improvements to how `project-status` provisions and summarizes each
tracked repo:

1. **Streamline the injected `CLAUDE.md` block** (`templates/claude-rule.md`) so
   it carries less always-on weight while staying deterministic and
   cross-assistant (Claude *and* Gemini).
2. **Produce a more robust and concise per-repo summary** so the portfolio is
   quick to review — the standing pain point is that with many repos it is hard
   to review quickly.

## Part 1 — streamline the CLAUDE.md block

The daily-plan rules block is large and duplicated verbatim into every tracked
repo, costing always-on tokens everywhere. Redesign so the **hook carries the
verbose procedure on-demand** and `CLAUDE.md` keeps only the tight invariant.

- Keep in `CLAUDE.md`: the few hard rules (header format, single-day scope,
  forward-write rule) — an always-loaded backstop.
- Move to the SessionStart hook (`templates/check-daily-plan.py`): the full body
  structure, injected **only when the plan is stale/missing** (i.e. exactly when
  it is needed). Single source of truth, near-zero always-on cost.

**Decision gate — is Gemini still in the workflow?**

- **Yes** → the `CLAUDE.md` block must stay as Gemini's channel (Gemini does not
  run Claude Code hooks), so the hook is only the freshness nudge; streamlining is
  limited to trimming prose.
- **No** → the hook path is fully viable; gut the `CLAUDE.md` block down to the
  invariant and let the fattened hook carry the procedure.

Propagate any change with `./setup-new-repo.sh --update <repo-remote>` across all
tracked repos.

## Part 2 — more robust, concise per-repo summary

Make each repo's cross-portfolio summary genuinely scannable.

- Tighten the `daily-plan.md` "What this repo is (for a newcomer)" +
  "Last implemented" fields so a cold reader grasps each repo in one glance.
- Consider a compact **portfolio-at-a-glance** view in `daily-plan-summary.md`
  (or a sibling): a one-line-per-repo table — repo · purpose · next step ·
  importance/status — above the current full per-repo sections.
- Relates to the existing review task
  [`2026-07-01-review-daily-plan-abstraction-level.md`](2026-07-01-review-daily-plan-abstraction-level.md)
  (plans drifting too low-level); this task acts on it rather than only reviewing.

## Out of scope

- The umbrella `CLAUDE.md` generator (tracked separately in
  [`2026-07-27-generate-umbrella-claude-md.md`](2026-07-27-generate-umbrella-claude-md.md)).

## Notes

- The lever for plan altitude/readability is upstream in `templates/` +
  `setup-new-repo.sh --update`, not in the aggregator, which copies plans through
  verbatim.

## Part 1 as built (2026-07-27)

**Decision gate answered: Gemini is still in the workflow.** So the split is
CLAUDE.md → a *repo-root file*, not CLAUDE.md → the hook: a plain Markdown file
is cross-assistant, while a Claude Code hook is not. The hook stays a thin
freshness nudge.

- `templates/claude-rule.md` cut from 62 lines / ~6,650 chars to 41 / ~2,260 —
  the kernel only. Each surviving rule passed the test *"if this loaded on
  demand, would it be too late?"*: the commit schema and the
  title-for-a-stranger rule (applied at commit time, nothing would trigger a
  lookup first), task-granularity + commit-before-session-close (fires at end of
  session), the plan header format and single-day/overwrite rule (Gemini's only
  channel — the hook covers this for Claude), the forward-write rule (fires on an
  ambiguous signoff, when *no* hook fires and nothing prompts a lookup — miss it
  and today's plan is destroyed), the ✅ announce line (kept by explicit
  decision), and the pointer to the guide.
- `templates/project-status-guide.md` — new, installed at each tracked repo's
  **root** (not `.claude/`: that directory is force-added past `.gitignore` in
  some repos, and it's Claude-branded when the whole point is cross-assistant
  readability). Carries the rationale, worked good/bad examples, the four-part
  plan body structure, the no-URL-in-header reasoning, and the hook description.
  Upstream-managed — always overwritten, like the hook.
- Fixed a live drift found while splitting: the SessionStart hook told the
  assistant to write "one short paragraph of intent" while the rule block
  mandated a four-part body. The hook now points at the guide's *Body structure*
  section instead of restating it.
- `tests/test_templates.py` — size ceiling on the kernel (2,800 chars), marker
  integrity, the guide pointer survives, the moved procedure actually landed in
  the guide, and the hook doesn't restate the body structure. Size is mechanical
  and gated in CI; whether a rule *belongs* in the kernel stays a review call.
- Verified end-to-end against a throwaway local bare remote: the old block is
  replaced in place, hand-written content above and below it survives, the guide
  is added, and an existing `daily-plan.md` is left alone.

Propagated 2026-07-27 via `./setup-new-repo.sh --update <remote>` across all six
tracked repos (one commit + push each): `second-brain-test`,
`second-brain-devkit`, `customer-req-responder`, `create-ai-builder`,
`captains-log`, `create-project-system`.

## Part 2 as built (2026-07-27)

`daily-plan-summary.md` opens with an **At a glance** table: one row per repo —
repo (linked), priority band, plan freshness, the first bullet of today's focus,
and days since the last commit.

- **Sort: fresh plans first, then by band.** Freshness leads because the table
  answers "what is live today" before "what matters most" — a stale P1 has
  nothing to say about today. Ties keep `repos.yml` order (stable sort).
- **Priority lives in `repos.yml`** (`priority: 1|2|3`, default 3), not in each
  repo's `daily-plan.md`. It is a cross-portfolio judgment that only means
  anything relative to the other repos, and no single repo can see them; a
  self-reported field would give six repos each claiming P1 with no arbiter.
  Bands, not a strict rank — ties are expected. Assigned from observed commit
  activity, recency weighted over raw volume.
- **Idle comes from git, not `state.json`.** Aggregation runs *before*
  `commit-state.py` advances the state, so `last_activity_date` is always a run
  behind and would report today's work as a day idle.
- Cells escape `|` and truncate, or one long focus bullet breaks the table.

## Keeping repos from falling out of the system (2026-07-27)

Cloning a *tracked* repo was never the gap — the block, guide, and hook are
committed into the repo and arrive with the clone. Two real gaps, two layers:

1. **Never bootstrapped** — a new project, or one worked in before being
   registered. Caught by `hooks/check-repo-bootstrap.py`, a **user-level**
   `SessionStart` hook in `~/.claude/settings.json`. It has to be user-level:
   a repo that was never bootstrapped has no hook of its own to fire. Narrow by
   design (git repos under the workspace root only, never the tracker itself,
   `.project-status-ignore` opts out) — a hook that cries wolf gets ignored.
2. **Version skew** — the failure a clone-time hook cannot see, and the one that
   already existed: `setup-new-repo.sh` always refreshes the guide and hook but
   only rewrites the `CLAUDE.md` block with `--update`, so a repo can carry a
   current guide beside a months-old kernel. `_lib.target_drift()` compares both
   against `templates/`; `tools/check-targets.py` is the whole-portfolio view
   (non-zero exit on drift), and the same finding is repeated as a callout in
   that repo's section of `daily-plan-summary.md` — the copy actually read every
   day, so drift gets seen the day it appears rather than when someone
   remembers to run a checker.
