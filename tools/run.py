#!/usr/bin/env python3
"""Daily orchestrator. Single entry point for the full update cycle.

Steps:
  1. sync.py    — refresh tracked clones
  2. gather_report() — classify each repo
  3. for each ACTIVE repo: claude -p with prompts/per-repo.md
  4. for each INACTIVE repo (report_inactivity=true): deterministic one-liner
  5. if >=2 ACTIVE: claude -p with prompts/polish.md to merge cross-repo themes
  6. prepend the day section to summary.md
  7. commit-state.py — advance state.json, commit summary.md + state.json

Live-LLM steps (3, 5) can be skipped with --dry-run for offline testing.
"""
import argparse
import subprocess
import sys
from datetime import date

from _lib import REPO_ROOT, SUMMARY_MD, gather_report

PROMPTS_DIR = REPO_ROOT / "prompts"
TOOLS_DIR = REPO_ROOT / "tools"
INSERT_MARKER = "<!-- new sections inserted below -->"


def claude_p(prompt: str) -> str:
    """Invoke `claude -p`, piping the prompt via stdin (safer for large inputs)."""
    r = subprocess.run(
        ["claude", "-p"],
        input=prompt,
        check=True,
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


def format_slice(e: dict) -> str:
    return (
        f"Range: {e['last_commit'][:8]}..{e['head'][:8]}\n\n"
        f"## log.md additions\n{e['log_diff'] or '(none)'}\n\n"
        f"## file stat\n{e['file_stat'] or '(none)'}\n\n"
        f"## commits\n{e['commit_list'] or '(none)'}\n"
    )


def render_per_repo(e: dict, dry_run: bool) -> str:
    if dry_run:
        return f"### {e['name']}\n- (dry-run placeholder for {e['last_commit'][:8]}..{e['head'][:8]})"
    template = (PROMPTS_DIR / "per-repo.md").read_text()
    prompt = (template
              .replace("{{REPO_NAME}}", e["name"])
              .replace("{{REPO_SLICE}}", format_slice(e)))
    return claude_p(prompt)


def render_inactive(e: dict) -> str:
    if e["last_activity_date"]:
        return (f"### {e['name']}\n"
                f"No activity for {e['days_inactive']} days "
                f"(last activity {e['last_activity_date']})")
    return f"### {e['name']}\nNo activity recorded yet"


def polish(today: str, drafts_text: str, dry_run: bool) -> str:
    if dry_run:
        return f"## {today}\n\n{drafts_text}"
    template = (PROMPTS_DIR / "polish.md").read_text()
    prompt = template.replace("{{TODAY}}", today).replace("{{DRAFTS}}", drafts_text)
    return claude_p(prompt)


def prepend_to_summary(section: str) -> None:
    text = SUMMARY_MD.read_text()
    block = section.rstrip() + "\n"
    if INSERT_MARKER in text:
        new = text.replace(INSERT_MARKER, INSERT_MARKER + "\n\n" + block, 1)
    else:
        # Fallback: insert before the first existing day section, else append.
        idx = text.find("\n## ")
        if idx == -1:
            new = text.rstrip() + "\n\n" + block
        else:
            new = text[:idx + 1] + block + "\n" + text[idx + 1:]
    SUMMARY_MD.write_text(new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="skip claude -p calls; emit deterministic placeholders")
    ap.add_argument("--skip-sync", action="store_true",
                    help="skip the sync.py step (useful when iterating locally)")
    ap.add_argument("--skip-commit", action="store_true",
                    help="skip the commit-state.py step")
    args = ap.parse_args()

    if not args.skip_sync:
        print("[run] sync...")
        subprocess.run([sys.executable, str(TOOLS_DIR / "sync.py")], check=True)

    today = date.today().isoformat()
    report = gather_report(today=today)

    drafts: list[str] = []
    active_count = 0
    for e in report:
        if e["status"] in ("INACTIVE_SUPPRESSED",):
            continue
        if e["status"] == "NOT_SYNCED":
            print(f"[run] WARNING: {e['name']} not synced; skipping", file=sys.stderr)
            continue
        if e["status"] == "INACTIVE":
            drafts.append(render_inactive(e))
            continue
        # ACTIVE
        print(f"[run] summarizing {e['name']}...")
        drafts.append(render_per_repo(e, args.dry_run))
        active_count += 1

    if not drafts:
        print("[run] nothing to write; exiting")
        return

    drafts_text = "\n\n".join(drafts)
    if active_count >= 2:
        print("[run] polishing cross-repo section...")
        section = polish(today, drafts_text, args.dry_run)
    else:
        section = f"## {today}\n\n{drafts_text}"

    prepend_to_summary(section)
    print(f"[run] prepended {today} section to summary.md")

    if not args.skip_commit:
        print("[run] commit-state...")
        subprocess.run([sys.executable, str(TOOLS_DIR / "commit-state.py")], check=True)


if __name__ == "__main__":
    main()
