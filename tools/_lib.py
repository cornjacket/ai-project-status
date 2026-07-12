"""Shared helpers for project-status tools."""
import json
import os
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REPOS_YML = REPO_ROOT / "repos.yml"
STATE_JSON = REPO_ROOT / "state.json"
TRACKED_DIR = REPO_ROOT / "tracked"
SUMMARY_MD = REPO_ROOT / "summary.md"

# When the daily run executes inside a Claude remote routine, the platform
# pre-clones every declared `source` repo at /home/user/<name> via an
# authenticated local proxy. Direct https://github.com clones from inside
# that sandbox are intercepted by an Anthropic TLS-inspection proxy and
# return 401 even for public repos, so we MUST reuse the pre-cloned trees.
PREBUILT_SOURCE_ROOT = Path("/home/user")

# Well-known SHA-1 of git's empty tree, used as a baseline diff target on first run.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def load_repos():
    """Return list of normalized repo dicts with defaults applied."""
    with open(REPOS_YML) as f:
        data = yaml.safe_load(f) or {}
    out = []
    for r in data.get("repos") or []:
        out.append({
            "name": r["name"],
            "remote": r["remote"],
            "branch": r.get("branch", "main"),
            "enabled": r.get("enabled", True),
            "report_inactivity": r.get("report_inactivity", True),
        })
    return out


def enabled_repos():
    return [r for r in load_repos() if r["enabled"]]


def load_state():
    if not STATE_JSON.exists():
        return {}
    with open(STATE_JSON) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_JSON, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def repo_dir(name):
    return TRACKED_DIR / name


def prebuilt_source_path(name):
    """Path to the platform's pre-cloned checkout for `name`, or None."""
    if not os.environ.get("CLAUDE_CODE_REMOTE"):
        return None
    p = PREBUILT_SOURCE_ROOT / name
    return p if (p / ".git").is_dir() else None


def git(args, cwd=None, check=True):
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd) if cwd else None,
        check=check,
        capture_output=True,
        text=True,
    )


def head_commit(name):
    return git(["rev-parse", "HEAD"], cwd=repo_dir(name)).stdout.strip()


# ASCII control chars used as git-log delimiters. Bodies are multi-line, so a
# bare "%s%n%b" is unparseable across commits — these never occur in real text.
_RECORD_SEP = "\x1e"  # between commits
_UNIT_SEP = "\x1f"    # between fields within a commit


def _parse_message(raw):
    """Split a raw commit message into (title, context, impact, body).

    title = first non-blank line. context/impact = the `- [Context]:` and
    `- [Impact]:` values from the remaining lines; either may span multiple
    lines (continuation = non-marker, non-blank lines folded in until the next
    marker or a blank line). Parsing the raw message ourselves (rather than
    leaning on git's %s/%b) is deliberate: git treats the whole first paragraph
    as the subject, so a schema commit WITHOUT a blank line after the title
    would otherwise swallow [Context]/[Impact] into %s and leave %b empty.
    """
    lines = raw.splitlines()
    title = ""
    rest_start = 0
    for i, ln in enumerate(lines):
        if ln.strip():
            title = ln.strip()
            rest_start = i + 1
            break
    context_lines, impact_lines = [], []
    current = None
    for raw_line in lines[rest_start:]:
        line = raw_line.strip()
        low = line.lower()
        if low.startswith("- [context]:"):
            current = context_lines
            current.append(line.split(":", 1)[1].strip())
        elif low.startswith("- [impact]:"):
            current = impact_lines
            current.append(line.split(":", 1)[1].strip())
        elif not line:
            current = None
        elif current is not None:
            current.append(line)
    return (
        title,
        " ".join(p for p in context_lines if p).strip(),
        " ".join(p for p in impact_lines if p).strip(),
        raw.strip("\n"),
    )


def git_telemetry(repo_dir, rev_range):
    """High-level commit telemetry for `rev_range`, newest first.

    Returns list[{hash, title, context, impact, body}]. Replaces the old
    `git diff -- log.md` narrative source: change detection was already
    git-native; this reads structured commit messages instead of log.md.

    Tracked repos follow (enforced via their CLAUDE.md):
        <domain>(<scope>): <high-level functional summary>
        - [Context]: why this was done / what was learned
        - [Impact]: how it alters the project or system behavior

    `%B` (raw message) is used as a single field so the title/marker split is
    robust whether or not the author left a blank line after the title.
    """
    fmt = f"{_RECORD_SEP}%h{_UNIT_SEP}%B"
    out = git(["log", f"--pretty=format:{fmt}", rev_range], cwd=repo_dir).stdout
    commits = []
    for record in out.split(_RECORD_SEP):
        if not record.strip():
            continue
        parts = record.split(_UNIT_SEP, 1)
        h = parts[0].strip()
        raw = parts[1] if len(parts) > 1 else ""
        title, context, impact, body = _parse_message(raw)
        commits.append({
            "hash": h,
            "title": title,
            "context": context,
            "impact": impact,
            "body": body,
        })
    return commits


def days_between(iso_a, iso_b):
    from datetime import date
    return (date.fromisoformat(iso_b) - date.fromisoformat(iso_a)).days


def advance_state(today=None):
    """Bump last_commit/last_synced for every enabled+synced repo; bump
    last_activity_date only when the head moved. Persists and returns the
    new state."""
    from datetime import date as _date
    today = today or _date.today().isoformat()
    state = load_state()
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
    return state


def format_telemetry(commits):
    """Render git_telemetry() output as a human/LLM-readable block.

    Returns "(none)" for an empty/None list so callers can drop their own
    fallbacks. Mirrors the old "### log.md additions" slot.
    """
    if not commits:
        return "(none)"
    blocks = []
    for c in commits:
        lines = [f"- {c['hash']} {c['title']}"]
        if c["context"]:
            lines.append(f"    [Context]: {c['context']}")
        if c["impact"]:
            lines.append(f"    [Impact]: {c['impact']}")
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def gather_report(today=None, since=None):
    """Return one dict per enabled repo, in repos.yml order.

    Each entry has:
      name, status, last_commit, head, last_activity_date, days_inactive,
      commit_telemetry, file_stat, commit_list, report_inactivity

    status ∈ {'ACTIVE', 'INACTIVE', 'INACTIVE_SUPPRESSED', 'NOT_SYNCED'}

    Commit window: by default the durable range `last_commit..HEAD` from
    state.json (Locked decision #1 — preserves catch-up recovery and
    determinism). `since` is an opt-in ad-hoc override (e.g. "24 hours ago"):
    the content window becomes `<last commit before cutoff>..HEAD` and a repo
    is ACTIVE when that window is non-empty, independent of state.json.
    """
    from datetime import date as _date
    today = today or _date.today().isoformat()
    state = load_state()
    out = []
    for r in enabled_repos():
        name = r["name"]
        s = state.get(name, {})
        last = s.get("last_commit") or EMPTY_TREE
        last_act = s.get("last_activity_date")
        d = repo_dir(name)
        entry = {
            "name": name,
            "status": None,
            "last_commit": last,
            "head": None,
            "last_activity_date": last_act,
            "days_inactive": days_between(last_act, today) if last_act else None,
            "commit_telemetry": None,
            "file_stat": None,
            "commit_list": None,
            "report_inactivity": r["report_inactivity"],
        }
        if not d.exists():
            entry["status"] = "NOT_SYNCED"
            out.append(entry)
            continue
        head = head_commit(name)
        entry["head"] = head
        if since:
            base = git(["rev-list", "-1", f"--before={since}", "HEAD"],
                       cwd=d, check=False).stdout.strip() or EMPTY_TREE
            rev_range = f"{base}..HEAD"
            is_active = bool(git(["rev-list", rev_range], cwd=d).stdout.strip())
        else:
            rev_range = f"{last}..HEAD"
            is_active = head != last
        if not is_active:
            entry["status"] = "INACTIVE" if r["report_inactivity"] else "INACTIVE_SUPPRESSED"
        else:
            entry["status"] = "ACTIVE"
            entry["commit_telemetry"] = git_telemetry(d, rev_range)
            entry["file_stat"] = git(["diff", "--stat", rev_range], cwd=d).stdout
            entry["commit_list"] = git(["log", "--oneline", rev_range], cwd=d).stdout
        out.append(entry)
    return out
