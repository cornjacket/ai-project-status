#!/usr/bin/env python3
"""Show new log.md entries and --stat for one repo since its recorded last_commit."""
import sys

from _lib import EMPTY_TREE, git, load_state, repo_dir


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: diff.py <repo-name>")
    name = sys.argv[1]
    state = load_state()
    last = state.get(name, {}).get("last_commit") or EMPTY_TREE
    d = repo_dir(name)
    if not d.exists():
        sys.exit(f"tracked/{name} does not exist — run sync.py first")

    print(f"=== {name}: {last[:8]}..HEAD ===\n")
    print("--- log.md additions ---")
    print(git(["diff", f"{last}..HEAD", "--", "log.md"], cwd=d).stdout or "(no log.md changes)")
    print("--- file stat ---")
    print(git(["diff", "--stat", f"{last}..HEAD"], cwd=d).stdout or "(no file changes)")


if __name__ == "__main__":
    main()
