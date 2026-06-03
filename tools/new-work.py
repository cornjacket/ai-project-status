#!/usr/bin/env python3
"""Emit a per-repo report of new work since last_commit, including inactivity metadata.

Output is the human-readable form of `gather_report()`. The orchestrator (run.py)
consumes the structured data directly via `from _lib import gather_report`.
"""
import argparse
from datetime import date

from _lib import format_telemetry, gather_report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", "--window", dest="since", metavar="WHEN",
                    help="ad-hoc commit-window override (e.g. '24 hours ago'); "
                         "default uses the durable last_commit..HEAD range")
    args = ap.parse_args()
    today = date.today().isoformat()
    report = gather_report(today=today, since=args.since)
    print(f"# Update report — {today}\n")
    if not report:
        print("_(no enabled repos in repos.yml)_")
        return
    for e in report:
        print(f"## {e['name']}")
        if e["status"] == "NOT_SYNCED":
            print("NOT_SYNCED — run sync.py first\n")
            continue
        if e["status"] == "INACTIVE_SUPPRESSED":
            print("INACTIVE_SUPPRESSED — omit from summary.md\n")
            continue
        if e["status"] == "INACTIVE":
            if e["last_activity_date"]:
                print(f"INACTIVE — no activity for {e['days_inactive']} days "
                      f"(last activity {e['last_activity_date']})\n")
            else:
                print("INACTIVE — no activity recorded yet\n")
            continue
        # ACTIVE
        print(f"ACTIVE — {e['last_commit'][:8]}..{e['head'][:8]}\n")
        print("### commit telemetry")
        print(format_telemetry(e["commit_telemetry"]))
        print("### file stat")
        print(e["file_stat"] or "(none)")
        print("### commits")
        print(e["commit_list"] or "(none)")
        print()


if __name__ == "__main__":
    main()
