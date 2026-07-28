#!/usr/bin/env python3
"""Report tracked repos whose injected project-status files have drifted.

Compares each synced repo's `CLAUDE.md` rule block and `project-status-guide.md`
against `templates/`. Drift happens quietly: `setup-new-repo.sh` always
refreshes the guide and the hook but only rewrites the CLAUDE.md block when
given `--update`, so a repo can carry a current guide beside a months-old
kernel with nothing to say so.

The same check is surfaced per repo in `daily-plan-summary.md` (that's the copy
you read every day); this tool is the one-shot, whole-portfolio view, and exits
non-zero when anything is out of sync so it can gate a CI job.

Run `tools/sync.py` first — this reads the `tracked/` checkouts, not the
remotes.

Usage:
    python3 tools/check-targets.py [--quiet]
"""
import argparse
import sys

from _lib import enabled_repos, repo_dir, target_drift


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="print only repos that have drifted",
    )
    args = ap.parse_args(argv)

    drifted = 0
    for r in enabled_repos():
        name = r["name"]
        if not repo_dir(name).exists():
            if not args.quiet:
                print(f"?  {name}: not synced (run tools/sync.py)")
            continue
        problems = target_drift(name)
        if problems:
            drifted += 1
            print(f"!  {name}: {'; '.join(problems)}")
            print(f"     ./setup-new-repo.sh --update {r['remote']}")
        elif not args.quiet:
            print(f"ok {name}")

    if drifted:
        print(
            f"\n{drifted} repo(s) out of sync with templates/.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
