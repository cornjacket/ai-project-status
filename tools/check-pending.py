#!/usr/bin/env python3
"""Report uncommitted and unpushed work across every repo in the workspace.

Run from anywhere; it always reports on the workspace root (the directory that
holds project-status and its sibling checkouts). Answers the question the daily
loop ends on — *did I actually commit and push everything?* — which no single
repo's editor view can answer, because the sibling repos are separate git repos
and simply aren't in scope there.

Two kinds of pending work, both reported, because only tracking the first is how
work goes missing:

  * **uncommitted** — staged, unstaged, or untracked changes in the working tree.
  * **unpushed** — commits on the current branch that the upstream doesn't have.
    A repo you committed but never pushed looks clean to `git status`.

Roster: `repos.yml` (plus project-status itself) by default, so this reports on
the tracked portfolio. `--all` instead sweeps every git repo under the workspace
root — including ones project-status doesn't track — honoring the same
`.project-status-ignore` opt-out the bootstrap hook uses.

LOCAL-ONLY: it reads working checkouts that don't exist in the routine sandbox,
so it is deliberately not part of tools/run.py.

Usage:
    python3 project-status/tools/check-pending.py [--all] [--dirty-only] [--path DIR]

Exits 1 when anything is pending, 0 when everything is committed and pushed, so
it works as a gate as well as a dashboard.
"""
import argparse
import sys
from pathlib import Path

from _lib import REPO_ROOT, UMBRELLA_DIR, enabled_repos, git, local_checkout

IGNORE_FILE = ".project-status-ignore"
# Nested worktree layouts put the checkout one level below the container
# (`create-ai-builder/main`), so a depth-1 scan would miss exactly the repo whose
# path is already the easiest to forget.
SCAN_DEPTH = 2
# Changed files listed per repo before the rest are summarized. Long enough for a
# real review, short enough that one noisy repo can't bury the others.
MAX_FILES = 12


def is_git_repo(path: Path) -> bool:
    """True for an ordinary clone *or* a linked worktree (where .git is a file)."""
    return (path / ".git").exists()


def discover_repos(workspace: Path) -> list[tuple[str, Path]]:
    """(label, checkout) for every git repo under `workspace`, depth-limited.

    A container directory (bare + worktrees) contributes its checkouts rather
    than itself, and any repo carrying `.project-status-ignore` is skipped — the
    same opt-out `hooks/check-repo-bootstrap.py` honors, so a repo you've already
    decided to leave alone stays quiet here too."""
    found = []
    for child in sorted(p for p in workspace.iterdir() if p.is_dir()):
        if child.name.startswith("."):
            continue
        if is_git_repo(child):
            if not (child / IGNORE_FILE).exists():
                found.append((child.name, child))
            continue
        for sub in sorted(p for p in child.iterdir() if p.is_dir()):
            if is_git_repo(sub) and not (sub / IGNORE_FILE).exists():
                found.append((f"{child.name}/{sub.name}", sub))
    return found


def worktrees_of(checkout: Path) -> list[Path]:
    """Every working tree attached to `checkout`'s repo, newest layout and all.

    Asks git (`git worktree list`) rather than guessing from directory shape.
    Guessing only finds worktrees that happen to sit next to their siblings; git
    knows about all of them, including ones parked in a separate directory
    (`tasks-test-wt/`) or outside the workspace entirely. Bare entries are
    dropped — a bare repo has no working tree, so it can hold no uncommitted
    work. Falls back to the checkout itself if git can't answer."""
    out = git(["worktree", "list", "--porcelain"], cwd=checkout, check=False)
    if out.returncode != 0:
        return [checkout]
    trees, current, bare = [], None, False
    for line in out.stdout.splitlines():
        if line.startswith("worktree "):
            current, bare = Path(line[len("worktree "):]), False
        elif line.strip() == "bare":
            bare = True
        elif not line.strip():
            if current and not bare:
                trees.append(current)
            current = None
    if current and not bare:
        trees.append(current)
    return trees or [checkout]


def label_for(path: Path, workspace: Path) -> str:
    """Workspace-relative label, falling back to the absolute path.

    A worktree can legitimately live outside the workspace; naming it by its full
    path is better than pretending it's a sibling."""
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return str(path)


def expand(entries: list[tuple[str, Path | None]], workspace: Path):
    """Replace each checkout with every worktree of its repo, deduped by path.

    A repo with three worktrees is three working trees that can each hold
    uncommitted work — reporting only the primary one is how the other two get
    forgotten."""
    seen, out = set(), []
    for name, checkout in entries:
        if checkout is None:
            out.append((name, None))
            continue
        for tree in worktrees_of(checkout):
            key = str(tree.resolve()) if tree.exists() else str(tree)
            if key in seen or not tree.exists():
                continue
            seen.add(key)
            out.append((label_for(tree, workspace), tree))
    return out


def tracked_repos(workspace: Path) -> list[tuple[str, Path | None]]:
    """(label, checkout) for the repos.yml roster, plus project-status itself.

    The tracker is included deliberately: it sits in the same workspace, it is
    where the day's plan-summary and state land, and leaving it out would make
    "everything is pushed" a claim the tool can't back."""
    out = [
        (r["name"], local_checkout(workspace, r["name"], r.get("branch", "main")))
        for r in enabled_repos()
    ]
    out += [(REPO_ROOT.name, REPO_ROOT if REPO_ROOT.exists() else None)]
    return expand(out, workspace)


def branch_of(checkout: Path) -> str:
    name = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=checkout, check=False).stdout.strip()
    return name or "(no commits)"


def unpushed(checkout: Path) -> tuple[int, str | None]:
    """(commits ahead of upstream, problem) — problem is None when it's knowable.

    No upstream is *reported*, not treated as zero: a branch that was never
    pushed is the most unpushed state there is, and silently calling it clean is
    the failure this tool exists to prevent."""
    up = git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
             cwd=checkout, check=False)
    if up.returncode != 0 or not up.stdout.strip():
        return 0, "no upstream"
    out = git(["rev-list", "--count", "@{upstream}..HEAD"], cwd=checkout, check=False)
    try:
        return int(out.stdout.strip()), None
    except ValueError:
        return 0, "upstream unreadable"


def porcelain(checkout: Path) -> list[tuple[str, str]]:
    """[(XY, path)] from `git status --porcelain`, untracked files included."""
    out = git(["status", "--porcelain"], cwd=checkout, check=False).stdout
    entries = []
    for line in out.splitlines():
        if len(line) > 3:
            entries.append((line[:2], line[3:]))
    return entries


def inspect(label: str, checkout: Path | None) -> dict:
    if checkout is None:
        return {"label": label, "state": "absent"}
    changes = porcelain(checkout)
    ahead, problem = unpushed(checkout)
    return {
        "label": label,
        "state": "ok",
        "path": checkout,
        "branch": branch_of(checkout),
        "changes": changes,
        "staged": sum(1 for xy, _ in changes if xy[0] not in " ?"),
        "untracked": sum(1 for xy, _ in changes if xy == "??"),
        "ahead": ahead,
        "upstream_problem": problem,
    }


def is_pending(r: dict) -> bool:
    if r["state"] != "ok":
        return False
    return bool(r["changes"]) or r["ahead"] > 0 or r["upstream_problem"] is not None


def summarize(r: dict) -> str:
    """The one-line verdict: what is pending in this repo, if anything."""
    if r["state"] == "absent":
        return "not checked out locally"
    bits = []
    if r["changes"]:
        n = len(r["changes"])
        detail = []
        if r["staged"]:
            detail.append(f"{r['staged']} staged")
        if r["untracked"]:
            detail.append(f"{r['untracked']} untracked")
        bits.append(f"{n} changed" + (f" ({', '.join(detail)})" if detail else ""))
    if r["ahead"]:
        bits.append(f"{r['ahead']} unpushed commit{'s' if r['ahead'] != 1 else ''}")
    if r["upstream_problem"]:
        bits.append(r["upstream_problem"])
    return ", ".join(bits) if bits else "clean"


def render(results: list[dict], workspace: Path, source: str, dirty_only: bool) -> str:
    shown = [r for r in results if not dirty_only or is_pending(r) or r["state"] != "ok"]
    lines = [f"Pending work under {workspace} ({source})", ""]
    if not shown:
        lines.append("  everything committed and pushed")
        return "\n".join(lines) + "\n"

    width = max(len(r["label"]) for r in shown)
    for r in shown:
        mark = "!" if is_pending(r) else ("-" if r["state"] != "ok" else " ")
        branch = f"  [{r['branch']}]" if r["state"] == "ok" else ""
        lines.append(f"{mark} {r['label']:<{width}}{branch}  {summarize(r)}")
        for xy, path in r.get("changes", [])[:MAX_FILES]:
            lines.append(f"      {xy} {path}")
        extra = len(r.get("changes", [])) - MAX_FILES
        if extra > 0:
            lines.append(f"      … and {extra} more")

    pending = [r for r in results if is_pending(r)]
    absent = [r for r in results if r["state"] == "absent"]
    checked = len(results) - len(absent)
    # State the happy path outright. "0 of 6 have pending work" is the same fact
    # phrased as a near-miss, and it's the line you read every day.
    lines += ["", f"{len(pending)} of {checked} repo(s) have pending work."
              if pending else "everything committed and pushed"]
    if absent:
        lines.append(f"{len(absent)} not checked out locally: "
                     + ", ".join(r["label"] for r in absent))
    return "\n".join(lines) + "\n"


def collect(workspace: Path, scan_all: bool) -> tuple[list[dict], str]:
    if scan_all:
        # Expanded too: a repo found here may have worktrees parked elsewhere.
        repos = expand(discover_repos(workspace), workspace)
        source = "every git repo found here, worktrees included"
    else:
        repos = tracked_repos(workspace)
        source = "tracked repos from repos.yml, worktrees included"
    return [inspect(label, path) for label, path in repos], source


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all", action="store_true", dest="scan_all",
                    help="sweep every git repo under the workspace root, not just "
                         "the repos.yml roster")
    ap.add_argument("--dirty-only", action="store_true",
                    help="list only repos with pending work")
    ap.add_argument("--path", type=Path, default=UMBRELLA_DIR,
                    help=f"workspace root (default: {UMBRELLA_DIR})")
    args = ap.parse_args(argv)

    workspace = args.path.expanduser().resolve()
    if not workspace.is_dir():
        print(f"[check-pending] no such directory: {workspace}", file=sys.stderr)
        return 2

    results, source = collect(workspace, args.scan_all)
    sys.stdout.write(render(results, workspace, source, args.dirty_only))
    return 1 if any(is_pending(r) for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
