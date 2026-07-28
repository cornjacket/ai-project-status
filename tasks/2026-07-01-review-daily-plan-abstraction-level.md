# Task: Review daily-plan summaries for abstraction level & readability

- **Created:** 2026-07-01
- **Status:** OPEN — **queued (PLAN #3 of 3).** Unassigned recurring review task; not yet started.
- **Owner:** _unassigned_

## Goal

Periodically review the archived daily-plan summaries and confirm they are:

1. **At an appropriate abstraction level** — a 100-ft view of the day's intent,
   not a granular task list. (The standing concern is that plans drift *too
   low-level*; commit history already records granularity after the fact.)
2. **Readable by an outsider** — someone unfamiliar with the repos should be able
   to skim a day's summary and understand what each project is working toward in
   seconds, without needing prior context.

## Where to look

The material lives in [`daily-plan-archive/`](../daily-plan-archive/) — one
`YYYY-MM-DD.md` snapshot of `daily-plan-summary.md` per run. Read a spread of
dates (not just the latest) to judge whether quality holds over time. Each dated
file is the aggregated cross-repo plan as it was generated that day.

## What to produce

A short judgement per reviewed period:

- Which repos' plans are well-pitched vs. too granular / too vague.
- Any plans that assume insider context (jargon, unexplained references) an
  outsider couldn't follow.
- Whether the aggregated framing (`daily-plan-summary.md` layout) helps or hurts
  a cold reader.

## If plans need adjusting

Plan *altitude* is governed by the rule injected into each tracked repo, not by
this repo's plumbing:

- `templates/claude-rule.md` → "Daily plan (daily-plan.md)" → **rule 3**
  ("Body is a 100-ft view, written as a bullet list…") is the lever. Tighten the
  guidance there, then propagate to tracked repos with
  `./setup-new-repo.sh --update <repo-remote>`.
- The aggregator (`tools/aggregate-plans.py`) copies plans through verbatim, so
  it is not where readability is fixed — the fix is upstream in how each repo
  writes its plan.

## Notes

- This is a **review / quality-control** task, not a build task — no code change
  is required unless the review concludes the plan-writing rule needs revising.
- Consider re-running it on a cadence (e.g. weekly) once a few days of archive
  have accumulated, so drift is caught early.
