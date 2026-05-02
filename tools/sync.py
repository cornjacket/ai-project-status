#!/usr/bin/env python3
"""Clone or fast-forward-pull every enabled repo into tracked/."""
from _lib import enabled_repos, git, prebuilt_source_path, repo_dir, TRACKED_DIR


def main():
    TRACKED_DIR.mkdir(exist_ok=True)
    repos = enabled_repos()
    if not repos:
        print("[sync] no enabled repos in repos.yml")
        return
    for r in repos:
        d = repo_dir(r["name"])
        prebuilt = prebuilt_source_path(r["name"])
        if prebuilt:
            if d.is_symlink() or d.exists():
                print(f"[sync] {r['name']} already wired to pre-cloned source")
            else:
                print(f"[sync] linking {r['name']} -> {prebuilt}")
                d.symlink_to(prebuilt)
            continue
        if not d.exists():
            print(f"[sync] cloning {r['name']} from {r['remote']} (branch {r['branch']})")
            git(["clone", "-b", r["branch"], r["remote"], str(d)])
        else:
            print(f"[sync] pulling {r['name']}")
            git(["pull", "--ff-only"], cwd=d)


if __name__ == "__main__":
    main()
