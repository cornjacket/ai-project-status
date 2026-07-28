# PLAN — project-status

Outstanding tasks, in intended order. Detail lives in each linked doc under
[`tasks/`](tasks/); shipped history is in the git log, not here.

## Next up

1. **[Missing-daily-plan reminder notifications](tasks/2026-06-29-daily-plan-reminder.md)** (PLANNED)
   — evening nudge (email/Slack/Discord) when a tracked repo has no fresh plan;
   the *nudge* half of the loop whose *generate* half shipped as `tools/replan.py`.
   `replan.py --report` already prints the per-repo state a notifier would send.
2. **[Review daily-plan abstraction level](tasks/2026-07-01-review-daily-plan-abstraction-level.md)** (OPEN)
   — recurring review of whether the plans sit at the right altitude.
3. **[Stop umbrella-session work on tracked repos — review all mechanisms](tasks/2026-07-27-umbrella-guardrail-enforcement-review.md)** (OPEN)
   — the umbrella read-only guardrail is prose-only and unenforced (crossed in
   practice on 2026-07-27); review the soft→hard mechanism space (sharpen prose,
   PreToolUse gate, settings deny-rules, drift-hardening) and adopt a tier.
