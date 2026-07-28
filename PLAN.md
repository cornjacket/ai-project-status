# PLAN — project-status

Outstanding tasks, in intended order. Detail lives in each linked doc under
[`tasks/`](tasks/); shipped history is in the git log, not here.

## Next up

1. **[Draft next-day daily-plans from task state](tasks/2026-07-27-draft-daily-plans-from-task-state.md)** (PLANNED)
   — local-only, human-invoked `tools/replan.py`: one `claude -p` per checked-out
   repo (rooted in the repo) drafts `daily-plan.md` for review. Draft-only, never
   pushes.
2. **[Missing-daily-plan reminder notifications](tasks/2026-06-29-daily-plan-reminder.md)** (PLANNED)
   — evening nudge (email/Slack/Discord) when a tracked repo has no fresh plan;
   the complement to task 1's *generate* side.
3. **[Review daily-plan abstraction level](tasks/2026-07-01-review-daily-plan-abstraction-level.md)** (OPEN)
   — recurring review of whether the plans sit at the right altitude.
