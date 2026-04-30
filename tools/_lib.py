"""Shared helpers for ai-project-status tools."""
import json
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REPOS_YML = REPO_ROOT / "repos.yml"
STATE_JSON = REPO_ROOT / "state.json"
TRACKED_DIR = REPO_ROOT / "tracked"
SUMMARY_MD = REPO_ROOT / "summary.md"

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


def days_between(iso_a, iso_b):
    from datetime import date
    return (date.fromisoformat(iso_b) - date.fromisoformat(iso_a)).days


def gather_report(today=None):
    """Return one dict per enabled repo, in repos.yml order.

    Each entry has:
      name, status, last_commit, head, last_activity_date, days_inactive,
      log_diff, file_stat, commit_list, report_inactivity

    status ∈ {'ACTIVE', 'INACTIVE', 'INACTIVE_SUPPRESSED', 'NOT_SYNCED'}
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
            "log_diff": None,
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
        if head == last:
            entry["status"] = "INACTIVE" if r["report_inactivity"] else "INACTIVE_SUPPRESSED"
        else:
            entry["status"] = "ACTIVE"
            entry["log_diff"] = git(["diff", f"{last}..HEAD", "--", "log.md"], cwd=d).stdout
            entry["file_stat"] = git(["diff", "--stat", f"{last}..HEAD"], cwd=d).stdout
            entry["commit_list"] = git(["log", "--oneline", f"{last}..HEAD"], cwd=d).stdout
        out.append(entry)
    return out
