<!--
  Prompt template for tools/replan.py. Piped to `claude -p` once per repo, with
  cwd = that repo's local checkout, so the repo's own CLAUDE.md, skills, and
  task system load naturally.

  Placeholders: {{REPO_NAME}}, {{TARGET_DATE}}.
-->

You are drafting a **candidate** `daily-plan.md` for this repo. A human reviews it
before anything is written or committed — your output is a proposal, not a change.

- Repo: `{{REPO_NAME}}`
- Date to plan for: `{{TARGET_DATE}}`

## Your job: read the intent, don't invent it

A daily plan encodes the human's intent, and the human expresses that intent by
curating this repo's task system. You are a **reader** of that intent, never a
forecaster of it.

1. Read the current `daily-plan.md` at the repo root, if there is one.
2. Read this repo's task state — whatever form it takes here: the repo's
   `task-system` skill if it has one, otherwise `project/tasks/`, `tasks/`,
   `PLAN.md`, `TODO.md`, or whatever `CLAUDE.md` names. Note what is in progress,
   what is queued next, and what just closed.
3. Read recent history: `git log --oneline -20`, and the last few full messages
   for their `- [Context]:` / `- [Impact]:` lines.
4. Decide **keep vs. advance**:
   - **advance** — landed work plus task state make the next step unambiguous.
     Write the new focus.
   - **keep** — anything less than unambiguous. Reproduce the current plan with
     only the date rolled forward to {{TARGET_DATE}}. **This is the default.**
     Never manufacture a new direction so the plan looks productive.
   - **blocked** — you cannot derive a plan at all: the task state is stale or
     empty *and* there is no current plan to re-date. Say so plainly. That is a
     signal for the human to curate tasks — not something for you to paper over.

## Hard rules

- **Read-only.** Create, edit, and delete nothing — not the plan, not the tasks,
  not anything else. The draft is your output, not a file you write. Run no git
  command that mutates state (no `add`, `commit`, `push`, `checkout`).
- **Never curate tasks.** You report what the task state says; you never change
  what it says.
- **Never put a URL in the plan.** project-status links the repo itself, from its
  own registry.

## Plan structure

Follow `project-status-guide.md` in this repo. First line exactly
`# Daily plan — {{TARGET_DATE}}` and nothing else on it, then, in order:

1. `**What this repo is (for a newcomer):**` — one or two plain-language
   sentences. Keep this stable: carry the existing wording forward unless the
   repo's purpose genuinely shifted.
2. `**Last implemented:**` — one line naming the most recent thing shipped (read
   it off the git log).
3. `**Focus / plan:**` — a short, scannable bullet list of the day's intent. Not
   granular subtasks; the commit history records granularity after the fact.
4. A small ASCII diagram of the day's shape, in a fenced block.

## Output format

Emit exactly this and nothing else — no preamble, no commentary, no code fence
around the plan:

```
STATUS: advanced|kept|blocked
NOTE: one line on why, written for a human scanning a batch of repos
---PLAN---
# Daily plan — {{TARGET_DATE}}
(the full plan file body)
```

When STATUS is `blocked`, stop after the `NOTE:` line and emit no `---PLAN---`
section — say in the note exactly what the human needs to curate.
