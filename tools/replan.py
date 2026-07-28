#!/usr/bin/env python3
"""Draft next-day daily-plan.md files across the locally checked-out repos.

One `claude -p` per tracked repo, run with **cwd = that repo's own checkout**,
so the repo's `CLAUDE.md`, its skills, and its task system load naturally — the
context an umbrella session structurally lacks. Each run rewrites that repo's
`daily-plan.md` in place for the next business day and leaves it **uncommitted**.

Two invariants, both load-bearing:

  * **Draft-only.** The tool writes working-tree files and stops. It never stages,
    never commits, never pushes. Git *is* the review surface: every drafted plan
    shows up as a modified file (VS Code's Source Control view, `git diff`), and
    approving one means committing it yourself, from inside that repo.
  * **The plan is read from task state, not invented.** The human encodes intent
    by curating each repo's task system; the agent derives tomorrow's plan by
    inspecting that state plus the git log, and defaults to keeping the current
    plan (re-dated) whenever the next step isn't unambiguous. The agent is run
    read-only (see ALLOWED_TOOLS / DISALLOWED_TOOLS) so it *cannot* edit the
    tasks it reads — the tool owns every write.

LOCAL-ONLY. This writes to the human's working checkouts and shells out to the
`claude` CLI, so — like gen-umbrella-claude.py — it is deliberately NOT part of
tools/run.py or the cloud routine. It is human-invoked.

Usage:
    python3 tools/replan.py                    # draft for the next business day
    python3 tools/replan.py --only captains-log,create-project-system
    python3 tools/replan.py --date 2026-08-03 --force
    python3 tools/replan.py --report           # re-print the last run's table
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from _lib import (
    REPO_ROOT,
    UMBRELLA_DIR,
    enabled_repos,
    git,
    local_checkout,
)

PLAN_FILENAME = "daily-plan.md"
PROMPT_TEMPLATE = REPO_ROOT / "prompts" / "replan.md"
# Only so `--report` can re-print a run after the terminal scrolls. Gitignored:
# the plans themselves are the durable artifact, in the repos that own them.
LAST_RUN_JSON = REPO_ROOT / ".replan-last-run.json"

# Read-only by construction. The agent's whole job is to *read* human-encoded
# intent, so it gets the tools to read a repo and none that can change one — the
# "never edits tasks" rule is enforced here, not left to the prompt.
ALLOWED_TOOLS = [
    "Read",
    "Glob",
    "Grep",
    "Skill",
    "TodoWrite",
    "Bash(git log:*)",
    "Bash(git show:*)",
    "Bash(git status:*)",
    "Bash(git diff:*)",
    "Bash(ls:*)",
]
DISALLOWED_TOOLS = ["Write", "Edit", "NotebookEdit", "Task", "WebFetch", "WebSearch"]

# Drafting reads a whole task tree and a git log; a minute or two is normal, and
# the ceiling only exists so one wedged repo can't hold up the batch.
DEFAULT_TIMEOUT = 900

PLAN_MARKER = "---PLAN---"
STATUS_RE = re.compile(r"^\s*STATUS:\s*(\w+)", re.MULTILINE | re.I)
NOTE_RE = re.compile(r"^\s*NOTE:\s*(.*)$", re.MULTILINE | re.I)
PLAN_HEADER_RE = re.compile(r"^#\s+Daily plan\s+[—\-]\s+(\d{4}-\d{2}-\d{2})\s*$", re.M)
FENCE_RE = re.compile(r"^```[\w-]*\n(.*)\n```\s*$", re.S)

VERDICTS = {"advanced", "kept", "blocked"}


class DraftError(Exception):
    """A repo failed to draft. Isolated: the batch carries on without it."""


# --- target date ----------------------------------------------------------

def next_business_day(today: date) -> date:
    """The next Mon-Fri strictly after `today`.

    Friday, Saturday and Sunday all point at Monday, matching the aggregator's
    weekend tolerance: a Friday plan stays fresh through Sunday, so Monday's is
    the plan that's actually missing."""
    nxt = today + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt


# --- the plan file --------------------------------------------------------

def plan_path(checkout: Path) -> Path:
    return Path(checkout) / PLAN_FILENAME


def plan_header_date(checkout: Path) -> date | None:
    """The date the repo's current plan is for, or None.

    This is the batch's idempotency key: a plan already dated for the target has
    been drafted (or hand-written), so a re-run leaves it alone. Deriving it from
    the file itself — rather than from a sidecar ledger — means the tool can never
    disagree with what's actually on disk."""
    p = plan_path(checkout)
    if not p.exists():
        return None
    m = PLAN_HEADER_RE.search(p.read_text())
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def plan_is_dirty(checkout: Path) -> bool:
    """True when the repo's daily-plan.md has uncommitted changes (or is untracked).

    Guard against clobbering: an uncommitted plan is work git cannot give back,
    so it is never overwritten without --force."""
    out = git(["status", "--porcelain", "--", PLAN_FILENAME],
              cwd=checkout, check=False).stdout.strip()
    return bool(out)


def write_plan(checkout: Path, text: str) -> Path:
    """Overwrite the repo's daily-plan.md atomically.

    Via a temp file in the same directory so an interrupted run can never leave a
    half-written plan behind — the file either is the old plan or is the new one."""
    dest = plan_path(checkout)
    tmp = dest.with_name(f".{PLAN_FILENAME}.replan-tmp")
    tmp.write_text(text if text.endswith("\n") else text + "\n")
    tmp.replace(dest)
    return dest


# --- run ledger (for --report only) ---------------------------------------

def load_last_run() -> dict:
    if not LAST_RUN_JSON.exists():
        return {}
    try:
        return json.loads(LAST_RUN_JSON.read_text())
    except json.JSONDecodeError:
        return {}


def save_last_run(target: date, results: list[dict]) -> None:
    """Persist the batch's per-repo outcome after *every* repo, not once at the
    end: the 2026-07-27 hand-run died mid-batch on an auth error, and the report
    has to survive that."""
    LAST_RUN_JSON.write_text(json.dumps(
        {"date": target.isoformat(), "results": results}, indent=2,
    ) + "\n")


# --- the agent call -------------------------------------------------------

def render_prompt(name: str, target: date, template: str | None = None) -> str:
    template = template if template is not None else PROMPT_TEMPLATE.read_text()
    return (template
            .replace("{{REPO_NAME}}", name)
            .replace("{{TARGET_DATE}}", target.isoformat()))


def claude_cmd(model: str | None = None) -> list[str]:
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--allowedTools", ",".join(ALLOWED_TOOLS),
        "--disallowedTools", ",".join(DISALLOWED_TOOLS),
    ]
    if model:
        cmd += ["--model", model]
    return cmd


def run_claude(prompt: str, cwd: Path, timeout: int, model: str | None) -> str:
    """Run one `claude -p` in `cwd` and return its result text.

    Raises DraftError on every failure mode — non-zero exit, timeout, missing
    CLI, or an error result — so the caller can record it against this one repo
    and move on to the next."""
    try:
        proc = subprocess.run(
            claude_cmd(model),
            input=prompt,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise DraftError("`claude` CLI not found on PATH")
    except subprocess.TimeoutExpired:
        raise DraftError(f"timed out after {timeout}s")

    if proc.returncode != 0:
        raise DraftError(_tail(proc.stderr) or f"claude exited {proc.returncode}")

    out = proc.stdout.strip()
    if not out:
        raise DraftError("claude produced no output")
    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        return out  # tolerate a plain-text result if --output-format is ignored
    if isinstance(payload, dict):
        if payload.get("is_error"):
            raise DraftError(_tail(str(payload.get("result") or payload.get("subtype"))))
        return str(payload.get("result", "")).strip()
    return out


def _tail(text: str | None, limit: int = 200) -> str:
    """Last meaningful line of a subprocess's noise, trimmed for a status line."""
    if not text:
        return ""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return ""
    last = lines[-1]
    return last if len(last) <= limit else last[: limit - 1] + "…"


# --- response parsing -----------------------------------------------------

def parse_response(text: str) -> tuple[str, str, str]:
    """(verdict, note, plan_text) from the agent's STATUS/NOTE/---PLAN--- reply.

    Deliberately forgiving about the envelope and strict about the content: a
    missing marker or a stray code fence is a formatting slip worth recovering
    from, but a reply with no plan header at all is not a plan and must never be
    written over a real one."""
    m = STATUS_RE.search(text)
    verdict = m.group(1).lower() if m else ""
    if verdict not in VERDICTS:
        raise DraftError(f"unrecognized STATUS in reply: {verdict or '(none)'}")

    n = NOTE_RE.search(text)
    note = n.group(1).strip() if n else ""

    if PLAN_MARKER in text:
        plan = text.split(PLAN_MARKER, 1)[1].strip()
    else:
        # No marker: fall back to the plan header itself, which is unambiguous.
        h = PLAN_HEADER_RE.search(text)
        plan = text[h.start():].strip() if h else ""

    fence = FENCE_RE.match(plan)
    if fence:
        plan = fence.group(1).strip()

    if verdict == "blocked":
        return verdict, note or "agent could not derive a plan", ""
    if not plan:
        raise DraftError("reply carried no plan body")
    return verdict, note, plan


def normalize_header(plan: str, target: date) -> tuple[str, bool]:
    """Force the plan's header date to `target`; (plan, was_rewritten).

    The tool owns the target date — it is the one fact here the agent cannot know
    better — so a drifted header is corrected rather than rejected. A plan with no
    header at all is a different animal: that's malformed, and it raises rather
    than overwriting a good plan with a bad one."""
    m = PLAN_HEADER_RE.search(plan)
    if not m:
        raise DraftError("draft has no `# Daily plan — YYYY-MM-DD` header")
    if m.group(1) == target.isoformat():
        return plan, False
    fixed = f"# Daily plan — {target.isoformat()}"
    return plan[: m.start()] + fixed + plan[m.end():], True


# --- per-repo drive -------------------------------------------------------

def draft_repo(name: str, checkout: Path, target: date, args, template: str) -> dict:
    """Draft one repo, writing its plan in place. Never raises: the outcome is
    the return value, so one repo's failure can't take down the batch."""
    result = {"name": name, "checkout": str(checkout)}
    try:
        reply = run_claude(
            render_prompt(name, target, template),
            cwd=checkout,
            timeout=args.timeout,
            model=args.model,
        )
        verdict, note, plan = parse_response(reply)
        if verdict == "blocked":
            return {**result, "status": "blocked", "note": note}
        plan, rewritten = normalize_header(plan, target)
        write_plan(checkout, plan)
        if rewritten:
            note = (note + " " if note else "") + "(header date corrected)"
        return {**result, "status": verdict, "note": note,
                "path": str(plan_path(checkout))}
    except DraftError as e:
        return {**result, "status": "failed", "note": str(e)}


def resolve_targets(repos, umbrella: Path, only: set[str] | None):
    """[(repo_dict, checkout_or_None)] in repos.yml order.

    Repos with no local checkout are *reported*, not silently dropped — a repo
    that is never checked out (customer-req-responder) is exactly the one whose
    plan goes stale unnoticed."""
    out = []
    for r in repos:
        if only and r["name"] not in only:
            continue
        out.append((r, local_checkout(umbrella, r["name"], r.get("branch", "main"))))
    return out


def skip_reason(checkout: Path, target: date, force: bool) -> str | None:
    """Why this repo should be left alone, or None to draft it.

    Order matters: "already planned for the target" is the resumability case and
    the more informative message, so it wins over the dirty-file guard — a re-run
    after a mid-batch failure would otherwise report every finished repo as
    'uncommitted changes', which is true but useless."""
    if plan_header_date(checkout) == target and not force:
        return f"plan already dated {target.isoformat()} (--force to redraft)"
    if plan_is_dirty(checkout) and not force:
        return f"{PLAN_FILENAME} has uncommitted changes (--force to overwrite)"
    return None


def run_batch(target: date, args, repos=None, umbrella: Path | None = None) -> list[dict]:
    """Sequential per-repo loop with isolated failures.

    Sequential on purpose: the fan-out's real failure mode is a shared one (an
    expired login takes out every concurrent call at once), so parallelism buys
    wall-clock and costs legible output and re-run clarity. Resumability comes
    from the plan files themselves — a re-run skips repos already dated for the
    target."""
    umbrella = umbrella or UMBRELLA_DIR
    repos = repos if repos is not None else enabled_repos()
    only = set(args.only.split(",")) if args.only else None
    targets = resolve_targets(repos, umbrella, only)
    if only:
        missing = only - {r["name"] for r, _ in targets}
        for name in sorted(missing):
            print(f"[replan] WARNING: no such enabled repo: {name}", file=sys.stderr)

    template = PROMPT_TEMPLATE.read_text()
    results: list[dict] = []

    for repo, checkout in targets:
        name = repo["name"]
        if checkout is None:
            results.append({"name": name, "status": "skipped",
                            "note": "not checked out locally"})
        elif (reason := skip_reason(checkout, target, args.force)):
            results.append({"name": name, "checkout": str(checkout),
                            "status": "skipped", "note": reason})
            print(f"[replan] {name}: {reason}", file=sys.stderr)
        elif args.dry_run:
            results.append({"name": name, "checkout": str(checkout),
                            "status": "dry-run",
                            "note": f"would rewrite {plan_path(checkout)}"})
        else:
            print(f"[replan] drafting {name} (cwd={checkout})...", file=sys.stderr)
            results.append(draft_repo(name, checkout, target, args, template))
        # Persist as we go, so a mid-batch death still leaves a readable report.
        if not args.dry_run:
            save_last_run(target, results)
    return results


# --- reporting ------------------------------------------------------------

LABELS = {
    "advanced": "drafted — advanced",
    "kept": "drafted — kept, re-dated",
    "blocked": "BLOCKED",
    "failed": "FAILED",
    "skipped": "skipped",
    "dry-run": "dry run",
}


def render_report(results: list[dict], target: date) -> str:
    """One status line per repo, in repos.yml order."""
    if not results:
        return f"[replan] nothing to report for {target.isoformat()}\n"
    width = max(len(r["name"]) for r in results)
    lines = [f"Daily plans for {target.isoformat()}", ""]
    for r in results:
        note = f" — {r['note']}" if r.get("note") else ""
        lines.append(f"  {r['name']:<{width}}  {LABELS.get(r['status'], r['status'])}{note}")
    return "\n".join(lines) + "\n"


def next_steps(results: list[dict]) -> str:
    """The handoff. Every drafted plan is an uncommitted change in the repo that
    owns it, so the review surface is the one already open in the editor."""
    written = [r for r in results if r["status"] in ("advanced", "kept")]
    if not written:
        return ""
    lines = [
        "",
        "Review the daily-plans, commit, and push.",
        "",
        f"{len(written)} plan(s) rewritten in place and left uncommitted — they show "
        "up as modified files in VS Code's Source Control view (one entry per repo):",
        "",
    ]
    lines += [f"  {r['path']}" for r in written]
    lines += [
        "",
        "Nothing was staged, committed, or pushed. Commit each plan from inside "
        "the repo that owns it.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", help="plan date to draft for (default: next business day)")
    ap.add_argument("--only", help="comma-separated repo names to limit the batch to")
    ap.add_argument("--force", action="store_true",
                    help="redraft repos already dated for the target, and "
                         "overwrite an uncommitted daily-plan.md")
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve the roster and print what would run; no claude "
                         "calls, no writes")
    ap.add_argument("--report", action="store_true",
                    help="re-print the last run's status table and exit")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help=f"per-repo timeout in seconds (default: {DEFAULT_TIMEOUT})")
    ap.add_argument("--model", help="model override passed through to `claude -p`")
    args = ap.parse_args(argv)

    if args.report:
        last = load_last_run()
        if not last:
            print("[replan] no recorded run to report", file=sys.stderr)
            return 0
        stored = date.fromisoformat(last["date"])
        sys.stdout.write(render_report(last.get("results", []), stored))
        sys.stdout.write(next_steps(last.get("results", [])))
        return 0

    try:
        target = date.fromisoformat(args.date) if args.date else next_business_day(date.today())
    except ValueError:
        print(f"[replan] not a date: {args.date}", file=sys.stderr)
        return 2

    results = run_batch(target, args)
    sys.stdout.write(render_report(results, target))
    sys.stdout.write(next_steps(results))
    return 1 if any(r["status"] == "failed" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
