#!/usr/bin/env python3
"""Advance state.json to current HEADs and commit summary.md + state.json."""
from datetime import date

from _lib import REPO_ROOT, advance_state, git


def main():
    today = date.today().isoformat()
    advance_state(today=today)

    status = git(["status", "--porcelain", "summary.md", "state.json"], cwd=REPO_ROOT).stdout
    if not status.strip():
        print("[commit-state] nothing to commit")
        return
    git(["add", "summary.md", "state.json"], cwd=REPO_ROOT)
    git(["commit", "-m", f"status: {today} update"], cwd=REPO_ROOT)
    print(f"[commit-state] committed {today} update")


if __name__ == "__main__":
    main()
