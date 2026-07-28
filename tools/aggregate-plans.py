#!/usr/bin/env python3
"""Aggregate per-repo daily-plan.md into daily-plan-summary.md.

Each enabled tracked repo is expected to keep a `daily-plan.md` at its root
whose first line declares the plan's intended date:

    # Daily plan — YYYY-MM-DD

This tool reads each plan, applies a weekend-tolerant staleness check (a plan
is fresh iff its date is on or after `most_recent_weekday(today)`), and writes
one aggregated `daily-plan-summary.md` at the repo root, overwriting any
prior version. Repos with `enabled: false` are skipped entirely.

The aggregated summary is the daily deliverable, so each run also snapshots it
into `daily-plan-archive/YYYY-MM-DD.md` (keyed by the summary's own date). The
canonical `daily-plan-summary.md` is overwrite-only; the dated archive keeps a
browsable history of every day's plan for later review. Per-repo `daily-plan.md`
files remain overwrite-only — their history lives in each repo's git log.
"""
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from _lib import (
    DEFAULT_PRIORITY,
    REPO_ROOT,
    TRACKED_DIR,
    enabled_repos,
    git,
    target_drift,
)

DAILY_PLAN_SUMMARY = REPO_ROOT / "daily-plan-summary.md"
DAILY_PLAN_ARCHIVE_DIR = REPO_ROOT / "daily-plan-archive"
PLAN_HEADER_RE = re.compile(
    r"^#\s+Daily plan\s+[—\-]\s+(\d{4}-\d{2}-\d{2})\s*$",
    re.MULTILINE,
)
# The plan template's third body field. Its first bullet is the day's headline.
FOCUS_HEADING_RE = re.compile(r"^\*\*Focus\s*/\s*plan:?\*\*", re.MULTILINE | re.I)
BULLET_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
# Longest focus cell before truncation — the table is meant to be scanned, and a
# wrapping row defeats that.
MAX_FOCUS_CHARS = 64


def remote_to_url(remote: str | None) -> str | None:
    """Convert a git remote into a browsable https URL, or None if it doesn't
    look like one. Handles the forms we actually keep in repos.yml:

        https://github.com/owner/repo.git   -> https://github.com/owner/repo
        git@github.com:owner/repo.git       -> https://github.com/owner/repo
        ssh://git@github.com/owner/repo.git  -> https://github.com/owner/repo

    The link is derived here (single source of truth = repos.yml) rather than
    self-reported by each tracked repo, so it can't drift when a repo is
    renamed — repos.yml is already updated on rename.
    """
    if not remote:
        return None
    r = remote.strip()
    if r.startswith("git@"):
        # git@host:owner/repo(.git)
        host_path = r[len("git@"):]
        if ":" not in host_path:
            return None
        host, path = host_path.split(":", 1)
        r = f"https://{host}/{path}"
    elif r.startswith("ssh://"):
        r = "https://" + r[len("ssh://"):]
        # drop any embedded creds like git@ in ssh://git@host/...
        scheme, rest = r.split("://", 1)
        if "@" in rest.split("/", 1)[0]:
            rest = rest.split("@", 1)[1]
            r = f"{scheme}://{rest}"
    elif not r.startswith(("http://", "https://")):
        return None
    if r.endswith(".git"):
        r = r[: -len(".git")]
    return r


def most_recent_weekday(today: date) -> date:
    """Return today if it's Mon-Fri, else the previous Friday."""
    if today.weekday() < 5:
        return today
    return today - timedelta(days=today.weekday() - 4)


def parse_plan(text: str):
    """Return (plan_date, body_without_header). Returns (None, stripped_text)
    if the header is missing or malformed."""
    m = PLAN_HEADER_RE.search(text)
    if not m:
        return None, text.strip()
    try:
        plan_date = date.fromisoformat(m.group(1))
    except ValueError:
        return None, text.strip()
    body = (text[: m.start()] + text[m.end():]).strip()
    return plan_date, body


def extract_focus(body: str) -> str | None:
    """First bullet of the plan's `**Focus / plan:**` section.

    Falls back to the first bullet anywhere in the body, since older plans
    predate the fixed structure. Returns None when the plan has no bullets."""
    m = FOCUS_HEADING_RE.search(body)
    region = body[m.end():] if m else body
    for line in region.splitlines():
        b = BULLET_RE.match(line)
        if b:
            return b.group(1)
    return None


def plan_state(plan_path: Path, today: date):
    """(state, plan_date, body) where state is fresh|stale|missing|unparseable.

    Single source of truth for freshness, shared by the overview table and the
    per-repo sections so the two can't disagree."""
    if not plan_path.exists():
        return "missing", None, ""
    plan_date, body = parse_plan(plan_path.read_text())
    if plan_date is None:
        return "unparseable", None, body
    state = "stale" if plan_date < most_recent_weekday(today) else "fresh"
    return state, plan_date, body


def days_since_commit(name: str, today: date) -> int | None:
    """Days since the newest commit in the tracked checkout, or None.

    Read from git rather than state.json on purpose: aggregation runs *before*
    commit-state.py advances the state, so state.json's last_activity_date is
    always a run behind and would report today's work as a day idle."""
    d = TRACKED_DIR / name
    if not (d / ".git").exists() and not d.is_symlink() and not d.exists():
        return None
    out = git(["log", "-1", "--format=%cs"], cwd=d, check=False).stdout.strip()
    try:
        return (today - date.fromisoformat(out)).days
    except ValueError:
        return None


def _cell(text: str, limit: int = MAX_FOCUS_CHARS) -> str:
    """Table-safe single-line cell: pipes escaped, length capped."""
    one_line = " ".join(text.split())
    if len(one_line) > limit:
        one_line = one_line[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-") + "…"
    return one_line.replace("|", "\\|")


def overview_row(repo: dict, today: date) -> dict:
    name = repo["name"]
    url = remote_to_url(repo.get("remote"))
    state, plan_date, body = plan_state(
        TRACKED_DIR / name / "daily-plan.md", today
    )
    focus = extract_focus(body) if body else None
    return {
        "name": name,
        "url": url,
        "priority": int(repo.get("priority", DEFAULT_PRIORITY)),
        "state": state,
        "plan_date": plan_date,
        "focus": focus,
        "idle": days_since_commit(name, today),
    }


def sort_rows(rows):
    """Fresh plans first, then by priority band, then repos.yml order.

    Freshness leads because the table answers "what is live today" before "what
    matters most" — a stale P1 has nothing to say about today. Python's sort is
    stable, so equal keys keep their repos.yml position."""
    return sorted(
        enumerate(rows),
        key=lambda pair: (
            0 if pair[1]["state"] == "fresh" else 1,
            pair[1]["priority"],
            pair[0],
        ),
    )


def render_overview(repos, today: date, rows=None) -> str:
    """One-line-per-repo table above the full sections.

    `rows` lets the caller pass in rows it already computed (build_summary needs
    them to order the sections identically) instead of re-reading every plan."""
    rows = rows if rows is not None else [overview_row(r, today) for r in repos]
    if not rows:
        return ""
    lines = [
        "## At a glance",
        "",
        "<!-- Fresh plans first, then by priority band (P1 = highest, set in "
        "repos.yml). Idle = days since the newest commit. -->",
        "",
        "| Repo | Pri | Plan | Focus | Idle |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _, r in sort_rows(rows):
        label = f"[{r['name']}]({r['url']})" if r["url"] else r["name"]
        plan_cell = {
            "fresh": r["plan_date"].isoformat() if r["plan_date"] else "—",
            "stale": f"**STALE** {r['plan_date'].isoformat()}" if r["plan_date"] else "**STALE**",
            "missing": "**none**",
            "unparseable": "**bad header**",
        }[r["state"]]
        focus = _cell(r["focus"]) if r["focus"] else "—"
        if r["idle"] is None:
            idle = "—"
        elif r["idle"] == 0:
            idle = "today"
        else:
            idle = f"{r['idle']}d"
        lines.append(
            f"| {label} | P{r['priority']} | {plan_cell} | {focus} | {idle} |"
        )
    return "\n".join(lines) + "\n"


def drift_notice(name: str, remote: str | None) -> str:
    """Callout naming any project-status drift in this repo, or "".

    Surfaced here — in the repo's own section of the daily summary — rather than
    only in a checker you have to remember to run: the summary is read every
    day, so drift gets seen the day it appears."""
    problems = target_drift(name)
    if not problems:
        return ""
    cmd = f"./setup-new-repo.sh --update {remote or '<remote>'}"
    return (
        f"> ⚠️ **project-status drift:** {'; '.join(problems)}. "
        f"Re-run from project-status: `{cmd}`\n\n"
    )


def render_repo_section(
    name: str, plan_path: Path, today: date, remote: str | None = None
) -> str:
    # Link the repo name to its browsable URL (derived from repos.yml's remote)
    # so the aggregated summary is one click away from each repo. Falls back to
    # a plain name when the remote is absent or unrecognized.
    url = remote_to_url(remote)
    label = f"[{name}]({url})" if url else name
    drift = drift_notice(name, remote)

    state, plan_date, body = plan_state(plan_path, today)

    if state == "missing":
        return f"## {label} — no plan committed\n\n{drift}".rstrip("\n") + "\n"

    if state == "unparseable":
        return (
            f"## {label} — plan file present but unparseable\n\n"
            f"{drift}"
            "> Could not extract `# Daily plan — YYYY-MM-DD` header. "
            "The repo's SessionStart hook will prompt for a fresh plan.\n"
        )

    if state == "stale":
        header = f"## {label} — STALE (last plan: {plan_date.isoformat()})"
    else:
        header = f"## {label} — plan for {plan_date.isoformat()}"

    if not body:
        return f"{header}\n\n{drift}> Plan file has no body content.\n"
    return f"{header}\n\n{drift}{body}\n"


def build_summary(today: date | None = None, repos=None) -> str:
    today = today or date.today()
    repos = repos if repos is not None else enabled_repos()
    active = [r for r in repos if r.get("enabled", True)]
    # One pass over the plans feeds both the table and the section order, so the
    # two can never disagree: scanning the table and reading down the page are
    # the same motion.
    rows = [overview_row(r, today) for r in active]
    overview = render_overview(active, today, rows=rows)
    sections = [
        render_repo_section(
            active[i]["name"],
            TRACKED_DIR / active[i]["name"] / "daily-plan.md",
            today,
            active[i].get("remote"),
        )
        for i, _ in sort_rows(rows)
    ]
    body = "\n".join(sections)
    return (
        f"# Daily plan summary — {today.isoformat()}\n\n"
        "<!-- Auto-aggregated by tools/aggregate-plans.py from each tracked "
        "repo's daily-plan.md. Overwritten on every run. -->\n\n"
        f"{overview}\n"
        f"{body}"
    )


def archive_summary(today: date, summary: str) -> Path:
    """Snapshot the aggregated summary into daily-plan-archive/<today>.md.

    Keyed by the summary's own date, so re-running on the same day overwrites
    that day's snapshot (idempotent) rather than accumulating duplicates."""
    DAILY_PLAN_ARCHIVE_DIR.mkdir(exist_ok=True)
    dest = DAILY_PLAN_ARCHIVE_DIR / f"{today.isoformat()}.md"
    dest.write_text(summary)
    return dest


def main():
    today = date.today()
    summary = build_summary(today=today)
    DAILY_PLAN_SUMMARY.write_text(summary)
    print(f"[aggregate-plans] wrote {DAILY_PLAN_SUMMARY}", file=sys.stderr)
    dest = archive_summary(today, summary)
    print(f"[aggregate-plans] archived {dest}", file=sys.stderr)


if __name__ == "__main__":
    main()
