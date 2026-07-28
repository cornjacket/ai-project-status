# Task: Order the per-repo plan sections like the "At a glance" table

- **Created:** 2026-07-27
- **Status:** DONE — 2026-07-27. `build_summary` now orders sections through
  `sort_rows`; three ordering tests added in `tests/test_aggregate_plans.py`;
  `daily-plan-summary.md` regenerated; ordering documented in `DESIGN.md`,
  `README.md`, and `CLAUDE.md`.
- **Owner:** _unassigned_

## Goal

`daily-plan-summary.md` currently has two different orderings in one document:

- The **At a glance** table sorts by *fresh plans first, then priority band, then
  `repos.yml` order* (`sort_rows` in `tools/aggregate-plans.py`).
- The **per-repo sections** below it are emitted in raw `repos.yml` order.

So the table tells you what matters today, and then the body makes you hunt for
those repos in an unrelated order. Make the sections follow the same order as
the table, so scanning the table and then reading down the page are the same
motion.

## Design

- `sort_rows` stays the single source of truth for ordering — the table and the
  sections must not be able to disagree, the same way `plan_state` is already
  the single source of truth for freshness.
- `build_summary` computes the overview rows **once**, sorts them, renders the
  table from them, and emits the sections in that same sorted order. That also
  removes the current double read of every `daily-plan.md` (once for the table,
  once for the section).
- `repos.yml` order remains the tie-breaker, so the ordering is still stable and
  the registry still has the final say between equally-ranked repos.
- **`summary.md` is untouched.** The retrospective rollup keeps `repos.yml`
  order — only the plan summary is intent-ranked.

## Out of scope

- Changing the sort key itself (freshness → band → registry order is accepted).
- Any change to `summary.md` ordering or to per-repo `daily-plan.md` files.
