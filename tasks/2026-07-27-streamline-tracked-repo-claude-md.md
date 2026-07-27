# Task: Streamline the tracked-repo CLAUDE.md block + a more robust per-repo summary

- **Created:** 2026-07-27
- **Status:** OPEN — unassigned. Not yet started.
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
