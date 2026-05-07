#!/usr/bin/env bash
# setup-new-repo.sh — bootstrap a target repo for tracking by ai-project-status.
#
# Clones the target into a temporary directory, ensures it has:
#   - log.md            (initial template if missing)
#   - CLAUDE.md         (with the work-log rule injected between markers)
# then commits + pushes the changes back to the remote and cleans up.
#
# Idempotent: re-running on an already-bootstrapped repo is a no-op. Pass
# --update to refresh the rule block in place (replaces content between the
# ai-project-status markers).
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
TEMPLATE_LOG="$SCRIPT_DIR/templates/log.md"
TEMPLATE_RULE="$SCRIPT_DIR/templates/claude-rule.md"
TEMPLATE_PLAN="$SCRIPT_DIR/templates/daily-plan.md"
TEMPLATE_HOOK="$SCRIPT_DIR/templates/check-daily-plan.py"
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

for t in "$TEMPLATE_LOG" "$TEMPLATE_RULE" "$TEMPLATE_PLAN" "$TEMPLATE_HOOK"; do
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

# 1. log.md
if [[ ! -f "$target/log.md" ]]; then
  cp "$TEMPLATE_LOG" "$target/log.md"
  echo "[setup] created log.md"
else
  echo "[setup] log.md already present; left as-is"
fi

# 2. CLAUDE.md — inject (or update) the rule block between markers
claude="$target/CLAUDE.md"
rule_block="$(cat "$TEMPLATE_RULE")"

if [[ ! -f "$claude" ]]; then
  printf '# CLAUDE.md\n\nProject-specific operating directives for Claude Code.\n\n%s\n' "$rule_block" >"$claude"
  echo "[setup] created CLAUDE.md with work-log rule"
elif grep -qF "$BEGIN_MARKER" "$claude"; then
  if (( update_mode )); then
    # Replace the existing block (anything between begin and end markers, inclusive).
    awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" -v repl="$rule_block" '
      BEGIN { in_block = 0; printed = 0 }
      $0 == begin { in_block = 1; if (!printed) { print repl; printed = 1 }; next }
      $0 == end   { in_block = 0; next }
      !in_block   { print }
    ' "$claude" >"$claude.tmp" && mv "$claude.tmp" "$claude"
    echo "[setup] refreshed work-log rule in CLAUDE.md (--update)"
  else
    echo "[setup] CLAUDE.md already contains the work-log rule; pass --update to refresh"
  fi
else
  printf '\n%s\n' "$rule_block" >>"$claude"
  echo "[setup] appended work-log rule to existing CLAUDE.md"
fi

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
git add log.md CLAUDE.md daily-plan.md
git add -f .claude/hooks/check-daily-plan.py .claude/settings.json
git commit --quiet -m "Bootstrap ai-project-status tracking (log.md, daily-plan.md, work-log rule, SessionStart hook)"
git push --quiet origin "$branch"
echo "[setup] committed and pushed to origin/$branch"

cat <<EOF

[setup] done. Next step — register this repo with ai-project-status:

  Add to repos.yml:
    - name: $name
      remote: $remote$([[ "$branch" != "main" ]] && echo "
      branch: $branch")

EOF
