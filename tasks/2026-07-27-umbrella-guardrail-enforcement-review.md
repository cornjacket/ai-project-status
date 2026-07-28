# Task: Review how to stop umbrella-session work on tracked repos (all mechanisms)

- **Created:** 2026-07-27
- **Status:** OPEN — unassigned. Review/design task; evaluate options, then split
  out whichever are adopted as their own build tasks.
- **Owner:** _unassigned_

## The issue

The umbrella (workspace-root) session is supposed to be a **read-only cross-repo
dashboard/orchestrator** — edits, commits, and pushes belong in the owning repo
from a session rooted there. That rule exists **only as prose** in the generated
umbrella `CLAUDE.md` (emitted by `tools/gen-umbrella-claude.py:new_file()`), and
**nothing enforces it**. It is advisory, and the model can silently cross it.

**Evidence it fails in practice:** on 2026-07-27 an umbrella session did
substantial `project-status` work from the umbrella — authored task design docs,
created `PLAN.md`, edited task Status lines, and ran multiple `git commit` +
`git push` cycles — despite the `CLAUDE.md` text saying not to. The prose was in
context and was crossed anyway. Two contributing weaknesses:

1. **A loophole in the carve-out.** The guardrail allows *"writing … this
   directory's own planning artifacts (task capture, notes)."* Task capture *is*
   legitimately allowed — but the line between "capture a task" and "author design
   docs + PLAN.md + status edits + commit + push" is fuzzy and unenforced, and the
   session slid across it.
2. **The guardrail is unmaintained.** It lives *outside* the
   `<!-- project-status:begin/end -->` markers, so `splice()` never touches it on
   regeneration — if weakened or deleted, the generator won't restore it, and a
   fresh generation on another machine re-emits whatever is hard-coded in
   `new_file()`.

## Goal

Review the **full option space** for making the read-only umbrella boundary
actually hold, decide which mechanism(s) to adopt (soft, hard, or tiered), and
spin the adopted ones out as their own build tasks. This is a review task, not a
build — no mechanism is pre-decided.

## Mechanisms to evaluate

Soft (instruct better) → hard (make impossible). Not mutually exclusive.

1. **Sharpen the prose guardrail** — in `gen-umbrella-claude.py:new_file()` (the
   source of truth, not the hand-edited artifact). Keep task capture allowed but
   draw the line explicitly: capture = *a note/task file*; the following still
   require a repo-rooted session — authoring multi-file design work, creating/
   editing `PLAN.md`, `git commit`, `git push`. Cheap; sharpens the specific
   ambiguity; still soft — same category of control that just failed.
2. **PreToolUse enforcement hook** — when cwd is the workspace root, **deny**
   `Bash(git commit …)` / `Bash(git push …)` (and optionally `Edit`/`Write` into a
   tracked repo beyond a task file), while allowing reads and task capture. Hard
   gate — turns advice into a mechanism. Decide registration (user-level vs. an
   umbrella-placed `.claude/settings.json`) and how it identifies "a tracked repo"
   (repos.yml roster).
3. **Permission/settings deny-rules** — a `.claude/settings.json` in the umbrella
   dir (or user-level) with `deny` entries for the relevant Bash patterns
   (`git commit`/`git push` from the umbrella). Lighter than a custom hook if
   pattern-matching suffices; verify the umbrella (a non-repo dir) picks up local
   settings.
4. **Give "capture" a clearer home / shape** — define exactly where and in what
   form task capture lands so the allowed path is unambiguous and there's no drift
   into full design work. Pairs with option 1.
5. **Harden the guardrail against regeneration drift** — move the guardrail into a
   managed (regenerated) region so it can't silently weaken, or add a
   `check-targets.py`-style drift check that flags an umbrella `CLAUDE.md` whose
   guardrail text has diverged from the template.
6. **SessionStart re-assertion hook for the umbrella** — actively inject the
   read-only role each umbrella session (push) instead of relying on the passive
   `CLAUDE.md` (pull). Compare with the existing `check-repo-bootstrap.py` pattern.

## Decision axis

The governing question is **soft vs. hard**, matched to stakes. The failure mode
here is low blast radius (doc commits to the wrong "seat," easily corrected,
nothing destructive), which argues a sharpened prose rule (1, +4/5) may be
proportionate and a hard gate (2/3) could be over-engineering. Counterweight — a
second-brain principle: *"anything that can become a gate should become a gate;"*
an advisory rule the model can silently cross is a prime gate candidate. Resolve
by picking the tier deliberately rather than by default. Note the boundary is
specifically about *code mutation* (edits/commits/pushes on tracked repos) —
**task capture from the umbrella stays allowed**; any mechanism must preserve it.

## Out of scope

- Building any chosen mechanism (each adopted option becomes its own task).
- Changes to the remote aggregate cycle.

## Notes

- Meta: this task exists *because* the boundary failed, and by that same boundary
  the fix work (editing `gen-umbrella-claude.py`, adding hooks/settings) must be
  done from a session rooted in `project-status`, not the umbrella. (Capturing
  this task from the umbrella is itself the allowed exception.)
- Related: `2026-07-27-generate-umbrella-claude-md.md` (owns `new_file()` and the
  managed-block split), `hooks/check-repo-bootstrap.py` (existing SessionStart
  nudge pattern), `check-targets.py` (existing drift-check pattern to mirror for
  option 5).

## To-do checklist

- [ ] Evaluate mechanisms 1–6; record the soft-vs-hard decision and rationale.
- [ ] For each adopted mechanism, create a build task and (optionally) slot it
      into `PLAN.md`.
- [ ] If prose-only is chosen: sharpen `new_file()` guardrail + regenerate; verify
      a fresh generation emits the tightened text.
- [ ] If a gate is chosen: prototype the PreToolUse hook / settings deny-rules and
      confirm it blocks commit/push from the umbrella while allowing reads and task
      capture.
