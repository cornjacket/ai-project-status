#!/usr/bin/env bash
# setup-new-repo.sh — bootstrap a target repo for tracking by project-status.
#
# Clones the target into a temporary directory, ensures it has:
#   - CLAUDE.md               (kernel rules injected between markers)
#   - project-status-guide.md (the on-demand reference half; overwritten)
# then commits + pushes the changes back to the remote and cleans up.
#
# Idempotent: re-running on an already-bootstrapped repo is a no-op. The guide
# and the hook are upstream-managed and always refreshed; pass --update to also
# replace the CLAUDE.md rule block in place (content between the markers).
#
# Usage:
#   ./setup-new-repo.sh <remote-url> [branch]
#   ./setup-new-repo.sh --update <remote-url> [branch]
#
# Examples:
#   ./setup-new-repo.sh git@github.com:cornjacket/ai-foo.git
#   ./setup-new-repo.sh git@github.com:cornjacket/ai-foo.git develop
#   ./setup-new-repo.sh --update git@github.com:cornjacket/ai-foo.git

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_RULE="$SCRIPT_DIR/templates/claude-rule.md"
TEMPLATE_PLAN="$SCRIPT_DIR/templates/daily-plan.md"
TEMPLATE_HOOK="$SCRIPT_DIR/templates/check-daily-plan.py"
TEMPLATE_GUIDE="$SCRIPT_DIR/templates/project-status-guide.md"
BEGIN_MARKER="<!-- ai-project-status:begin -->"
END_MARKER="<!-- ai-project-status:end -->"
HOOK_CMD="python3 .claude/hooks/check-daily-plan.py"

usage() {
  sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-1}"
}

update_mode=0
case "${1:-}" in
  -h|--help) usage 0 ;;
  --update) update_mode=1; shift ;;
esac

remote="${1:-}"
branch="${2:-main}"
[[ -z "$remote" ]] && usage 1

for t in "$TEMPLATE_RULE" "$TEMPLATE_PLAN" "$TEMPLATE_HOOK" "$TEMPLATE_GUIDE"; do
  [[ -f "$t" ]] || {
    echo "[setup] missing template: $t" >&2
    exit 1
  }
done

name="$(basename "$remote" .git)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
target="$tmp/$name"

echo "[setup] cloning $remote (branch $branch) into $target"
git clone --quiet -b "$branch" "$remote" "$target"

# 1. CLAUDE.md — inject (or update) the rule block between markers
claude="$target/CLAUDE.md"
rule_block="$(cat "$TEMPLATE_RULE")"

if [[ ! -f "$claude" ]]; then
  printf '# CLAUDE.md\n\nProject-specific operating directives for Claude Code.\n\n%s\n' "$rule_block" >"$claude"
  echo "[setup] created CLAUDE.md with git-automation rule"
elif grep -qF "$BEGIN_MARKER" "$claude"; then
  if (( update_mode )); then
    # Replace the existing block (anything between begin and end markers, inclusive).
    # Python, not awk: BSD awk (macOS default) rejects the multi-line template
    # passed via -v ("newline in string") and silently leaves the block stale.
    python3 - "$claude" "$TEMPLATE_RULE" "$BEGIN_MARKER" "$END_MARKER" <<'PY'
import sys, pathlib
claude_path, tmpl_path, begin, end = sys.argv[1:5]
repl = pathlib.Path(tmpl_path).read_text().rstrip("\n")
out, in_block, printed = [], False, False
for line in pathlib.Path(claude_path).read_text().splitlines():
    if line == begin:
        in_block = True
        if not printed:
            out.append(repl)
            printed = True
        continue
    if line == end:
        in_block = False
        continue
    if not in_block:
        out.append(line)
pathlib.Path(claude_path).write_text("\n".join(out) + "\n")
PY
    echo "[setup] refreshed git-automation rule in CLAUDE.md (--update)"
  else
    echo "[setup] CLAUDE.md already contains the git-automation rule; pass --update to refresh"
  fi
else
  printf '\n%s\n' "$rule_block" >>"$claude"
  echo "[setup] appended git-automation rule to existing CLAUDE.md"
fi

# 2. project-status-guide.md (always overwritten — upstream-managed reference
#    half of the CLAUDE.md block; the kernel in CLAUDE.md points at it)
cp "$TEMPLATE_GUIDE" "$target/project-status-guide.md"
echo "[setup] installed project-status-guide.md"

# 3. daily-plan.md (created if missing; never overwritten)
if [[ ! -f "$target/daily-plan.md" ]]; then
  cp "$TEMPLATE_PLAN" "$target/daily-plan.md"
  echo "[setup] created daily-plan.md"
else
  echo "[setup] daily-plan.md already present; left as-is"
fi

# 4. .claude/hooks/check-daily-plan.py (always overwritten — upstream-managed)
mkdir -p "$target/.claude/hooks"
cp "$TEMPLATE_HOOK" "$target/.claude/hooks/check-daily-plan.py"
chmod +x "$target/.claude/hooks/check-daily-plan.py"
echo "[setup] installed .claude/hooks/check-daily-plan.py"

# 5. .claude/settings.json — merge our SessionStart hook idempotently,
#    leaving any other settings the user has untouched.
python3 - "$target/.claude/settings.json" "$HOOK_CMD" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
cmd = sys.argv[2]
data = json.loads(path.read_text()) if path.exists() else {}
hooks = data.setdefault("hooks", {})
session_start = hooks.setdefault("SessionStart", [])
already = any(
    any(h.get("command") == cmd for h in entry.get("hooks", []) or [])
    for entry in session_start
)
if not already:
    session_start.append({"hooks": [{"type": "command", "command": cmd}]})
    print(f"[setup] added SessionStart hook to {path}")
else:
    print(f"[setup] SessionStart hook already present in {path}")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n")
PY

# 6. Commit + push if anything changed
cd "$target"
if [[ -z "$(git status --porcelain)" ]]; then
  echo "[setup] no changes — repo already bootstrapped"
  exit 0
fi

# `git add -f` so a `.claude/` line in .gitignore doesn't silently skip the hook.
git add CLAUDE.md daily-plan.md project-status-guide.md
git add -f .claude/hooks/check-daily-plan.py .claude/settings.json
git commit --quiet -m "Bootstrap project-status tracking (daily-plan.md, kernel rule block + project-status-guide.md, SessionStart hook)"
git push --quiet origin "$branch"
echo "[setup] committed and pushed to origin/$branch"

cat <<EOF

[setup] done. Next step — register this repo with project-status:

  Add to repos.yml:
    - name: $name
      remote: $remote$([[ "$branch" != "main" ]] && echo "
      branch: $branch")

EOF
