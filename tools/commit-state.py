#!/usr/bin/env python3
"""Advance state.json to current HEADs and commit summary.md, state.json,
daily-plan-summary.md, and the daily-plan-archive/ snapshots as a single
atomic update."""
from datetime import date

from _lib import REPO_ROOT, advance_state, git

TRACKED_FILES = [
    "summary.md",
    "state.json",
    "daily-plan-summary.md",
    "daily-plan-archive",
]


def main():
    today = date.today().isoformat()
    advance_state(today=today)

    existing = [f for f in TRACKED_FILES if (REPO_ROOT / f).exists()]
    status = git(["status", "--porcelain"] + existing, cwd=REPO_ROOT).stdout
    if not status.strip():
        print("[commit-state] nothing to commit")
        return
    git(["add"] + existing, cwd=REPO_ROOT)
    git(["commit", "-m", f"status: {today} update"], cwd=REPO_ROOT)
    print(f"[commit-state] committed {today} update")


if __name__ == "__main__":
    main()
