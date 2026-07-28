#!/usr/bin/env python3
"""SessionStart hook: nudge when a repo isn't bootstrapped for project-status.

Unlike the per-repo `check-daily-plan.py` hook, this one is installed
**user-level** (in ~/.claude/settings.json) and fires everywhere. It has to be:
a repo that was never bootstrapped has no hook of its own to run, which is
exactly the case worth catching — a fresh clone or a brand-new project you
start working in before registering it with project-status.

Stdout is injected as a system reminder before the first prompt; silence
(exit 0, no output) means everything is fine, so bootstrapped repos are
unaffected.

Deliberately narrow, because a hook that cries wolf gets ignored:
  - only inside a git repo;
  - only under the workspace root (override with PROJECT_STATUS_WORKSPACE);
  - never in project-status itself — it's the tracker, not a target;
  - never in a repo containing `.project-status-ignore`, the opt-out for repos
    that are deliberately untracked (scratch, forks, personal config).
"""
import os
import subprocess
import sys
from pathlib import Path

BEGIN_MARKER = "<!-- ai-project-status:begin -->"
IGNORE_FILE = ".project-status-ignore"
TRACKER_NAME = "project-status"
DEFAULT_WORKSPACE = Path.home() / "src" / "github.com" / "cornjacket"


def workspace_root() -> Path:
    override = os.environ.get("PROJECT_STATUS_WORKSPACE")
    return Path(override).expanduser() if override else DEFAULT_WORKSPACE


def repo_root() -> Path | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    path = out.stdout.strip()
    return Path(path) if path else None


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def main() -> int:
    root = repo_root()
    if root is None:
        return 0
    if not is_under(root, workspace_root()):
        return 0
    if root.name == TRACKER_NAME or (root / "repos.yml").exists():
        return 0
    if (root / IGNORE_FILE).exists():
        return 0

    claude = root / "CLAUDE.md"
    if claude.exists() and BEGIN_MARKER in claude.read_text():
        return 0

    tracker = workspace_root() / TRACKER_NAME
    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    ).stdout.strip() or "<remote-url>"

    print(
        f"`{root.name}` is not bootstrapped for project-status: its CLAUDE.md "
        "carries no commit-telemetry rules, so its work will not appear in the "
        "cross-repo rollup. Mention this to the user once, and if they want it "
        "tracked, run from "
        f"{tracker}:\n\n"
        f"    ./setup-new-repo.sh {remote}\n\n"
        f"then add it to repos.yml. If this repo should stay untracked, "
        f"`touch {IGNORE_FILE}` in it to silence this permanently. Do not let "
        "this block the user's actual request."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
