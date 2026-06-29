# Task: Missing-daily-plan reminder notifications

- **Created:** 2026-06-29
- **Status:** PLANNED — not yet started. Proposed feature; design captured here for a later build pass.
- **Owner:** David Taylor
- **Scope decision:** TBD at build time. Default assumption: a new deterministic
  pipeline step (no `claude -p` call) that rides the existing daily run.

## Goal

At the end of each day, if a tracked repo has **not** produced a fresh
`daily-plan.md`, notify the user (email / Slack / Discord) so they go create one.
The check is **per-repo opt-in/opt-out**, and all due reminders for a given run
**aggregate into a single message** so the notification is never noisy.

This closes the loop on the forward-looking side: today the pipeline *reports* a
missing/stale plan in `daily-plan-summary.md` (passive, pull), but nothing
actively *prompts* the human to write one (push).

## Why this is cheap to build

The staleness classification **already exists** and is the same logic the
reminder needs — do NOT reimplement it:

- `tools/aggregate-plans.py:most_recent_weekday(today)` — weekend-tolerant
  "what's the freshness cutoff" calculation.
- `tools/aggregate-plans.py:parse_plan(text)` — extracts the
  `# Daily plan — YYYY-MM-DD` header date (and flags unparseable files).
- `tools/aggregate-plans.py:render_repo_section(...)` already branches into the
  exact three states a reminder cares about:
  1. `no plan committed` (file absent)
  2. `plan file present but unparseable` (bad/missing header)
  3. `STALE (last plan: …)` (`plan_date < most_recent_weekday(today)`)

A repo is "reminder-due" iff it lands in state 1, 2, or 3. State "plan for
`<today/recent weekday>`" is fresh → no reminder.

## Proposed design

### 1. Config — new per-repo flag in `repos.yml`

Add `remind_missing_plan` alongside the existing `enabled` / `report_inactivity`
flags (read in `tools/_lib.py:load_repos()` at lines 35–37):

```yaml
repos:
  - name: ai-builder
    remote: https://github.com/cornjacket/ai-builder.git
    remind_missing_plan: false   # opt this repo out
```

- **Default:** `true` (opt-out) — **DECIDED**. Mirrors `report_inactivity`'s
  default-on convention; a repo opts out by setting the flag to `false`.
- Thread the flag through `load_repos()` → `enabled_repos()` so downstream code
  sees it the same way it sees the other flags.

### 2. Detection — refactor `aggregate-plans.py` to expose structured status

Right now `render_repo_section()` returns a formatted markdown string, so its
verdict (fresh / stale / missing / unparseable) is not reusable. Refactor so the
classification is a structured value that **both** consumers share:

- Extract a helper, e.g. `classify_plan(name, plan_path, today) ->
  {name, state, plan_date}` where `state ∈ {fresh, stale, missing,
  unparseable}`.
- `render_repo_section()` becomes a thin formatter over `classify_plan()` — the
  existing `daily-plan-summary.md` output stays byte-for-byte identical (guard
  with the existing tests).
- The reminder collector calls `classify_plan()` for every enabled repo whose
  `remind_missing_plan` is true and keeps those whose `state != fresh`.

### 3. Aggregation — one consolidated message

Collect ALL due repos into a single notification payload, never one-per-repo:

```
📋 Daily-plan reminder — 2026-06-29
The following repos have no fresh daily-plan.md:
  • ai-builder        — no plan committed
  • gsd-walkthru      — STALE (last plan: 2026-06-24)
  • second-brain-devkit — plan file present but unparseable
Create/refresh each repo's daily-plan.md.
```

If zero repos are due, send **nothing** (no "all good" message — keep it quiet).

### 4. Delivery — external channel (email / Slack / Discord) — **DECIDED**

Use an external channel, **not** an ephemeral push notification — the user wants
a durable message. New module `tools/notify.py` with a small `send(message)`
surface so the specific channel is swappable. Candidate channels (pick one to
ship first; all sit behind the same `send()`):

- **Slack / Discord incoming webhook.** Single `WEBHOOK_URL` env var, `POST` a
  JSON payload. Lightest of the three; durable, searchable channel history.
- **Email (SMTP).** Heaviest setup (SMTP host + credentials); use if email is
  specifically wanted.

Read the channel target (webhook URL / SMTP creds) from an env var or the
routine's secret store — **never commit the secret**. *(Which of the three to
ship first is the one remaining sub-decision — see Open decisions.)*

### 5. Wiring — a SEPARATE, earlier-firing trigger — **DECIDED**

The reminder does **not** ride the existing summary run. The current `/schedule`
routine (`trig_01BLz2BYyE95n44TCDKaFcnA`) fires **on the plan's own day** and
looks *backward* (it reports what was done). The reminder must fire **before**
the plan is due — i.e. near the **end of the previous day** — so the user still
has time to create the plan. That is a different time of day and a different
intent, so it needs its **own trigger**.

Implications:

- **New standalone entrypoint**, e.g. `tools/remind.py`, that does the minimal
  cycle on its own: sync/clone the tracked repos → `classify_plan()` for each
  opted-in repo → aggregate the non-fresh ones → `notify.send()`. It must NOT
  write `summary.md` / `daily-plan-summary.md` / `state.json` (no overlap with
  the summary routine's committed state).
- **New `/schedule` routine** pointing at `tools/remind.py`, scheduled in the
  evening (end of day, before the next day's plan is due). Its `sources` must
  list the same tracked repos as the summary routine so the sandbox egress proxy
  can clone them (same constraint called out in `CLAUDE.md` step 3 of "Add a new
  tracked repo").
- No-op cleanly when zero repos are due (send nothing) and degrade gracefully if
  the channel secret is absent.
- **Freshness cutoff sub-decision:** because the reminder runs the evening
  *before* day D, "fresh" should mean *the plan for the upcoming day exists*, not
  "today's plan exists." Recommended cutoff: the **next** business day relative
  to the run (forward-looking), reusing the weekday-skipping logic so a Friday
  evening run nudges for Monday's plan, not Saturday's. Confirm at build time —
  this is the one place the reminder's date math legitimately differs from the
  summary's backward-looking `most_recent_weekday(today)`.

Update `CLAUDE.md` to document both the new entrypoint and the new routine
(alongside the existing "Run an update cycle" / routine docs).

> **Portability constraint (user preference).** Do NOT hard-couple the reminder
> to Claude's hosted `/schedule` cloud-routine infrastructure. The user prefers a
> **generic, non-vendor-locked** scheduling + delivery path. The Claude routine
> may be *one supported way* to fire `tools/remind.py`, but the design must keep
> the trigger swappable — `tools/remind.py` should be a plain script runnable
> from any scheduler (cron, systemd timer, GitHub Actions `schedule:`, a CI
> nightly job, etc.), and `notify.send()` should target a portable channel
> (SMTP/email or an incoming webhook) rather than a Claude-only push capability.
> This is also why §4 chose an external channel over the routine push. When in
> doubt, favor the cron-runnable, vendor-neutral option even if the hosted
> routine would be marginally less setup.

### 6. Tests (deterministic layer)

- `classify_plan()` unit tests covering all four states + the weekend-tolerant
  cutoff (extend `tests/` alongside the existing aggregate-plans coverage).
- Reminder-collector test: mixed fixture repos (fresh / stale / missing /
  opted-out) → assert only non-fresh, opted-in repos appear, and that the
  message is a single aggregated payload.
- Assert `daily-plan-summary.md` output is unchanged by the refactor.

## Decisions

**Settled:**

- **Delivery is an external channel (email / Slack / Discord), not push.** ✅
- **`remind_missing_plan` defaults to `true` (opt-out).** ✅
- **The reminder runs on its own NEW trigger, scheduled the evening before the
  plan's day** — separate from the existing summary routine. ✅
- **No vendor lock-in.** The scheduler and delivery channel must be generic /
  portable, not bound to Claude's hosted infra. The Claude `/schedule` routine is
  at most *one* way to fire it; `tools/remind.py` must run from any cron-like
  scheduler. (See the portability constraint in §5.) ✅

**Remaining (resolve at build time):**

1. **Which external channel ships first** — Slack/Discord webhook (lightest) vs.
   email (SMTP). All sit behind the same `notify.send()` seam, so this only
   affects what secret/infra to set up first.
2. **Freshness cutoff direction** — confirm the reminder checks for the
   *upcoming* day's plan (forward-looking), per §5, rather than reusing the
   summary's backward-looking `most_recent_weekday(today)`.
3. **Exact fire time** for the evening trigger (e.g. 18:00 local) and its weekday
   handling (skip weekend nags via the same weekday logic).

## To-do checklist

- [ ] Add `remind_missing_plan` flag to `repos.yml` schema + `_lib.py:load_repos()`
      (and `enabled_repos()` passthrough).
- [ ] Refactor `aggregate-plans.py`: extract `classify_plan()`; re-express
      `render_repo_section()` on top of it (output unchanged).
- [ ] Build the reminder collector (consume `classify_plan()`, filter to
      opted-in non-fresh repos, aggregate into one message).
- [ ] Add `tools/notify.py` with a swappable `send()` and the chosen channel.
- [ ] Add standalone `tools/remind.py` entrypoint (sync → classify → aggregate →
      `notify.send()`; writes NO committed state).
- [ ] Create a new evening `/schedule` routine pointing at `tools/remind.py`,
      with `sources` mirroring the summary routine's tracked repos; document both
      in `CLAUDE.md`.
- [ ] Confirm the forward-looking freshness cutoff (upcoming day's plan).
- [ ] Tests: `classify_plan()` states, collector filtering/aggregation,
      `daily-plan-summary.md` unchanged.
- [ ] Resolve the remaining build-time decisions (channel pick, fire time).
