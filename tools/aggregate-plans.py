#!/usr/bin/env python3
"""Aggregate per-repo daily-plan.md into daily-plan-summary.md.

Each enabled tracked repo is expected to keep a `daily-plan.md` at its root
whose first line declares the plan's intended date:

    # Daily plan — YYYY-MM-DD

This tool reads each plan, applies a weekend-tolerant staleness check (a plan
is fresh iff its date is on or after `most_recent_weekday(today)`), and writes
one aggregated `daily-plan-summary.md` at the repo root, overwriting any
prior version. Repos with `enabled: false` are skipped entirely.
"""
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from _lib import REPO_ROOT, TRACKED_DIR, enabled_repos

DAILY_PLAN_SUMMARY = REPO_ROOT / "daily-plan-summary.md"
PLAN_HEADER_RE = re.compile(
    r"^#\s+Daily plan\s+[—\-]\s+(\d{4}-\d{2}-\d{2})\s*$",
    re.MULTILINE,
)


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


def render_repo_section(name: str, plan_path: Path, today: date) -> str:
    if not plan_path.exists():
        return f"## {name} — no plan committed\n"

    text = plan_path.read_text()
    plan_date, body = parse_plan(text)

    if plan_date is None:
        return (
            f"## {name} — plan file present but unparseable\n\n"
            "> Could not extract `# Daily plan — YYYY-MM-DD` header. "
            "The repo's SessionStart hook will prompt for a fresh plan.\n"
        )

    expected = most_recent_weekday(today)
    if plan_date < expected:
        header = f"## {name} — STALE (last plan: {plan_date.isoformat()})"
    else:
        header = f"## {name} — plan for {plan_date.isoformat()}"

    if not body:
        return f"{header}\n\n> Plan file has no body content.\n"
    return f"{header}\n\n{body}\n"


def build_summary(today: date | None = None, repos=None) -> str:
    today = today or date.today()
    repos = repos if repos is not None else enabled_repos()
    sections = [
        render_repo_section(r["name"], TRACKED_DIR / r["name"] / "daily-plan.md", today)
        for r in repos
        if r.get("enabled", True)
    ]
    body = "\n".join(sections)
    return (
        f"# Daily plan summary — {today.isoformat()}\n\n"
        "<!-- Auto-aggregated by tools/aggregate-plans.py from each tracked "
        "repo's daily-plan.md. Overwritten on every run. -->\n\n"
        f"{body}"
    )


def main():
    today = date.today()
    summary = build_summary(today=today)
    DAILY_PLAN_SUMMARY.write_text(summary)
    print(f"[aggregate-plans] wrote {DAILY_PLAN_SUMMARY}", file=sys.stderr)


if __name__ == "__main__":
    main()
