#!/usr/bin/env python3
"""Generate the umbrella CLAUDE.md for the workspace root.

The "umbrella" directory is the parent of every tracked repo checkout
(`~/src/github.com/cornjacket/`). A Claude session started there sits *above*
all repos and should behave as a read-only cross-repo dashboard, but that
directory is not a git repo, so its CLAUDE.md cannot be version controlled
there. It is therefore a **build artifact**: this generator lives in
project-status (version controlled) and writes the artifact out.

LOCAL-ONLY. The umbrella path does not exist in the remote scheduled run, so
this tool is deliberately NOT wired into tools/run.py or the aggregate cycle.
Re-run it by hand whenever repos.yml gains or loses a repo.

Managed-block split (same pattern as setup-new-repo.sh): everything outside the
`<!-- project-status:begin -->` / `<!-- project-status:end -->` markers is
human-owned and never touched on regeneration; the block holds the generated
repo roster. If the file is missing entirely it is created from the template
below.

Usage:
    python3 tools/gen-umbrella-claude.py [--path DIR] [--dry-run]
"""
import argparse
import re
import sys
from pathlib import Path

from _lib import REPO_ROOT, TRACKED_DIR, enabled_repos

# The workspace root is project-status's parent: ~/src/github.com/cornjacket/
DEFAULT_UMBRELLA_DIR = REPO_ROOT.parent

BEGIN_MARKER = "<!-- project-status:begin -->"
END_MARKER = "<!-- project-status:end -->"

# The one-line purpose comes from each repo's daily-plan.md — the same
# "What this repo is (for a newcomer)" field the plan template mandates.
PURPOSE_RE = re.compile(
    r"^\*\*What this repo is \(for a newcomer\):\*\*\s*(.*)$",
    re.MULTILINE,
)
# Longest purpose we inline. This block is always-on context for every umbrella
# session, so it stays names + one-liners; depth lives in daily-plan-summary.md.
MAX_PURPOSE_CHARS = 160
# Below this, one sentence hasn't said anything ("`foo` is a generator.") — pull
# in the next one rather than shipping a roster line that carries no signal.
MIN_PURPOSE_CHARS = 60


def _truncate(text: str) -> str:
    cut = text[:MAX_PURPOSE_CHARS].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:—-") + "…"


def _summarize(text: str) -> str:
    """Leading sentence(s) of `text`, capped at MAX_PURPOSE_CHARS."""
    out = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        candidate = f"{out} {sentence}".strip()
        if len(candidate) > MAX_PURPOSE_CHARS:
            # Enough already, or nothing yet and even one sentence overflows.
            return out if len(out) >= MIN_PURPOSE_CHARS else _truncate(candidate)
        out = candidate
        if len(out) >= MIN_PURPOSE_CHARS:
            break
    return out


def extract_purpose(text: str) -> str | None:
    """Pull the one-line repo purpose out of a daily-plan.md body.

    Folds continuation lines (the field routinely wraps) up to the next blank
    line or structural marker. Returns None when the field is absent or still
    holds the template's placeholder."""
    m = PURPOSE_RE.search(text)
    if not m:
        return None
    parts = [m.group(1).strip()]
    # `$` matches before the newline, so drop exactly that one terminator —
    # lstrip would also eat a genuine blank line and keep folding past it.
    rest = text[m.end():]
    if rest.startswith("\n"):
        rest = rest[1:]
    for raw in rest.splitlines():
        line = raw.strip()
        if not line or line.startswith(("**", "#", "- ", "* ", "```", ">", "|")):
            break
        parts.append(line)
    blob = " ".join(p for p in parts if p).strip()
    if not blob or "replace this" in blob.lower():
        return None
    return _summarize(blob)


def plan_sources(name: str, umbrella: Path):
    """Candidate daily-plan.md paths for `name`, best first.

    The local sibling checkout wins over project-status's `tracked/` cache: it
    is the working copy the umbrella session actually sees (and may hold an
    uncommitted plan), and it is the path the roster points at. `tracked/` is
    the fallback for repos not checked out locally."""
    return [umbrella / name / "daily-plan.md", TRACKED_DIR / name / "daily-plan.md"]


def repo_purpose(name: str, umbrella: Path) -> str | None:
    for path in plan_sources(name, umbrella):
        if path.exists():
            purpose = extract_purpose(path.read_text())
            if purpose:
                return purpose
    return None


def render_block(repos, umbrella: Path) -> str:
    """The generated roster, markers included."""
    lines = [
        BEGIN_MARKER,
        "<!-- Generated from project-status/repos.yml by "
        "tools/gen-umbrella-claude.py. Do not hand-edit: re-run the generator "
        "when a repo is added or removed. -->",
        "",
    ]
    for r in repos:
        name = r["name"]
        purpose = repo_purpose(name, umbrella) or "_(no daily-plan.md yet)_"
        present = "" if (umbrella / name).is_dir() else " — **not checked out locally**"
        lines.append(f"- **{name}** (`./{name}`{present}) — {purpose}")
    if not repos:
        lines.append("- _(no enabled repos in repos.yml)_")
    lines += ["", END_MARKER]
    return "\n".join(lines)


def new_file(block: str) -> str:
    """Full CLAUDE.md for a workspace that doesn't have one yet.

    Everything outside the block is human-owned from here on — regeneration
    never rewrites it. Kept to a kernel of role, guardrail, and pointers:
    it is always-on context for every umbrella session."""
    return f"""# CLAUDE.md — cornjacket workspace (umbrella)

<!-- This directory is not a git repo. This file is a build artifact generated
     by project-status/tools/gen-umbrella-claude.py. Text outside the
     project-status markers is human-owned and safe to edit; the block between
     them is regenerated. -->

## What this session is

You are rooted at the workspace directory that sits *above* every repo below.
This session is a **read-only cross-repo dashboard and orchestrator**, not a
workbench.

- Reading anything under this directory is fine — that is the point.
- Do code edits, commits, and pushes **inside the owning repo**, from a session
  rooted there. Not from here.
- Writing here is limited to this directory's own planning artifacts (task
  capture, notes). Capture is planning, not code mutation.
- When a request turns into real work on a repo, name the repo and hand off.

## Repos tracked by project-status

{block}

## Where to look first

Read these when you need them; do not inline them here — the aggregator keeps
them fresh.

- `project-status/daily-plan-summary.md` — every tracked repo's current
  `daily-plan.md`, aggregated, with stale plans flagged.
- `project-status/summary.md` — interpretive daily rollup of commit activity
  across all tracked repos, newest first.
- `project-status/repos.yml` — the tracked-repo registry (source of the roster
  above).

## Cross-repo conventions

- Tracked repos commit with: `<domain>(<scope>): <high-level summary>`, plus
  `- [Context]:` (why) and `- [Impact]:` (what it changes) lines. That schema is
  what the rollup reads — it is telemetry, not decoration.
- Each tracked repo keeps a root `daily-plan.md`: single-day scope, first line
  `# Daily plan — YYYY-MM-DD`, overwritten rather than appended.
- Consult the personal second-brain (the `second-brain` skill) before designing
  a system or choosing conventions and naming.
"""


def splice(existing: str, block: str) -> str:
    """Replace the managed block in `existing`, preserving everything else.

    Appends the block (with a heading) when the markers are absent, so a
    hand-written umbrella CLAUDE.md can be adopted without losing content."""
    if BEGIN_MARKER not in existing:
        return existing.rstrip("\n") + f"\n\n## Repos tracked by project-status\n\n{block}\n"
    out, in_block, emitted = [], False, False
    for line in existing.splitlines():
        if line.strip() == BEGIN_MARKER:
            in_block = True
            if not emitted:
                out.append(block)
                emitted = True
            continue
        if line.strip() == END_MARKER:
            in_block = False
            continue
        if not in_block:
            out.append(line)
    return "\n".join(out) + "\n"


def build(umbrella: Path, repos=None) -> str:
    repos = repos if repos is not None else enabled_repos()
    block = render_block(repos, umbrella)
    target = umbrella / "CLAUDE.md"
    if target.exists():
        return splice(target.read_text(), block)
    return new_file(block)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_UMBRELLA_DIR,
        help=f"umbrella directory (default: {DEFAULT_UMBRELLA_DIR})",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print the result to stdout instead of writing it",
    )
    args = ap.parse_args(argv)

    umbrella = args.path.expanduser().resolve()
    if umbrella == REPO_ROOT:
        # project-status has its own version-controlled CLAUDE.md; clobbering it
        # with the umbrella artifact would be silent and destructive.
        print(
            "[gen-umbrella-claude] refusing to write to project-status itself "
            f"({umbrella})",
            file=sys.stderr,
        )
        return 1
    if not umbrella.is_dir():
        print(f"[gen-umbrella-claude] no such directory: {umbrella}", file=sys.stderr)
        return 1

    content = build(umbrella)
    target = umbrella / "CLAUDE.md"
    if args.dry_run:
        sys.stdout.write(content)
        print(f"[gen-umbrella-claude] dry run — would write {target}", file=sys.stderr)
        return 0
    action = "updated roster in" if target.exists() else "created"
    target.write_text(content)
    print(f"[gen-umbrella-claude] {action} {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
