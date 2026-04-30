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
BEGIN_MARKER="<!-- ai-project-status:begin -->"
END_MARKER="<!-- ai-project-status:end -->"

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

[[ -f "$TEMPLATE_LOG" && -f "$TEMPLATE_RULE" ]] || {
  echo "[setup] missing template under $SCRIPT_DIR/templates/" >&2
  exit 1
}

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

# 3. Commit + push if anything changed
cd "$target"
if [[ -z "$(git status --porcelain)" ]]; then
  echo "[setup] no changes — repo already bootstrapped"
  exit 0
fi

git add log.md CLAUDE.md
git commit --quiet -m "Bootstrap log.md and work-log rule for ai-project-status tracking"
git push --quiet origin "$branch"
echo "[setup] committed and pushed to origin/$branch"

cat <<EOF

[setup] done. Next step — register this repo with ai-project-status:

  Add to repos.yml:
    - name: $name
      remote: $remote$([[ "$branch" != "main" ]] && echo "
      branch: $branch")

EOF
