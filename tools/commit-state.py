#!/usr/bin/env python3
"""Advance state.json to current HEADs and commit summary.md + state.json."""
from datetime import date

from _lib import REPO_ROOT, enabled_repos, git, head_commit, load_state, repo_dir, save_state


def main():
    state = load_state()
    today = date.today().isoformat()
    for r in enabled_repos():
        name = r["name"]
        if not repo_dir(name).exists():
            continue
        head = head_commit(name)
        prev = state.get(name, {})
        had_activity = prev.get("last_commit") != head
        state[name] = {
            "last_commit": head,
            "last_synced": today,
            "last_activity_date": today if had_activity else prev.get("last_activity_date"),
        }
    save_state(state)

    status = git(["status", "--porcelain", "summary.md", "state.json"], cwd=REPO_ROOT).stdout
    if not status.strip():
        print("[commit-state] nothing to commit")
        return
    git(["add", "summary.md", "state.json"], cwd=REPO_ROOT)
    git(["commit", "-m", f"status: {today} update"], cwd=REPO_ROOT)
    print(f"[commit-state] committed {today} update")


if __name__ == "__main__":
    main()
