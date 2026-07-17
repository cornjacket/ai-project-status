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

from _lib import REPO_ROOT, TRACKED_DIR, enabled_repos

DAILY_PLAN_SUMMARY = REPO_ROOT / "daily-plan-summary.md"
DAILY_PLAN_ARCHIVE_DIR = REPO_ROOT / "daily-plan-archive"
PLAN_HEADER_RE = re.compile(
    r"^#\s+Daily plan\s+[—\-]\s+(\d{4}-\d{2}-\d{2})\s*$",
    re.MULTILINE,
)


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


def render_repo_section(
    name: str, plan_path: Path, today: date, remote: str | None = None
) -> str:
    # Link the repo name to its browsable URL (derived from repos.yml's remote)
    # so the aggregated summary is one click away from each repo. Falls back to
    # a plain name when the remote is absent or unrecognized.
    url = remote_to_url(remote)
    label = f"[{name}]({url})" if url else name

    if not plan_path.exists():
        return f"## {label} — no plan committed\n"

    text = plan_path.read_text()
    plan_date, body = parse_plan(text)

    if plan_date is None:
        return (
            f"## {label} — plan file present but unparseable\n\n"
            "> Could not extract `# Daily plan — YYYY-MM-DD` header. "
            "The repo's SessionStart hook will prompt for a fresh plan.\n"
        )

    expected = most_recent_weekday(today)
    if plan_date < expected:
        header = f"## {label} — STALE (last plan: {plan_date.isoformat()})"
    else:
        header = f"## {label} — plan for {plan_date.isoformat()}"

    if not body:
        return f"{header}\n\n> Plan file has no body content.\n"
    return f"{header}\n\n{body}\n"


def build_summary(today: date | None = None, repos=None) -> str:
    today = today or date.today()
    repos = repos if repos is not None else enabled_repos()
    sections = [
        render_repo_section(
            r["name"],
            TRACKED_DIR / r["name"] / "daily-plan.md",
            today,
            r.get("remote"),
        )
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
