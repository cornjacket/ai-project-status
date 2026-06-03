#!/usr/bin/env bash
# migrate-target-telemetry.sh — migrate a tracked repo OFF log.md and ONTO
# git-native commit telemetry.
#
# Operates IN PLACE on a local checkout (it does not clone, commit, or push —
# review the diff and commit yourself). For each target it:
#   1. removes log.md (git rm if tracked, rm if untracked, skip if absent)
#   2. swaps the ai-project-status CLAUDE.md block (between the begin/end
#      markers) for the new "Knowledge Extraction & Git Automation" rules,
#      creating CLAUDE.md if it is missing
#   3. flags any remaining unmanaged `log.md` mentions for manual review
#
# Idempotent: re-running on an already-migrated checkout is a no-op.
#
# The daily-plan.md mechanism is intentionally left COMPLETELY untouched.
#
# Usage:
#   ./migrate-target-telemetry.sh <target-dir>
#   ./migrate-target-telemetry.sh --second-brain <target-dir>
#
# --second-brain (or a target whose basename is `second-brain`) selects the
# docs() schema. That schema is DEFERRED and not yet shipped, so the script
# stops with a clear message until templates/claude-rule-second-brain.md exists.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_RULE="$SCRIPT_DIR/templates/claude-rule.md"
TEMPLATE_RULE_SB="$SCRIPT_DIR/templates/claude-rule-second-brain.md"
BEGIN_MARKER="<!-- ai-project-status:begin -->"
END_MARKER="<!-- ai-project-status:end -->"

usage() {
  sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-1}"
}

second_brain=0
case "${1:-}" in
  -h|--help) usage 0 ;;
  --second-brain) second_brain=1; shift ;;
esac

target="${1:-}"
[[ -z "$target" ]] && usage 1
[[ -d "$target" ]] || { echo "[migrate] not a directory: $target" >&2; exit 1; }

# 1. Must be a git repo.
git -C "$target" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "[migrate] not a git repository: $target" >&2
  exit 1
}

# Auto-detect second-brain by basename.
name="$(basename "$(cd "$target" && pwd)")"
if [[ "$name" == "second-brain" ]]; then
  second_brain=1
fi

rule_template="$TEMPLATE_RULE"
if (( second_brain )); then
  if [[ ! -f "$TEMPLATE_RULE_SB" ]]; then
    echo "[migrate] second-brain schema is deferred — $TEMPLATE_RULE_SB does not exist yet." >&2
    echo "[migrate] aborting without changes. Build the docs() template first." >&2
    exit 2
  fi
  rule_template="$TEMPLATE_RULE_SB"
fi

[[ -f "$rule_template" ]] || { echo "[migrate] missing template: $rule_template" >&2; exit 1; }

# 2. Remove log.md.
if git -C "$target" ls-files --error-unmatch log.md >/dev/null 2>&1; then
  git -C "$target" rm -f --quiet log.md
  echo "[migrate] removed tracked log.md"
elif [[ -f "$target/log.md" ]]; then
  rm -f "$target/log.md"
  echo "[migrate] removed untracked log.md"
else
  echo "[migrate] no log.md present; skipping"
fi

# 3. CLAUDE.md — inject/replace the managed block.
claude="$target/CLAUDE.md"
rule_block="$(cat "$rule_template")"

if [[ ! -f "$claude" ]]; then
  printf '# CLAUDE.md\n\nProject-specific operating directives for Claude Code.\n\n%s\n' "$rule_block" >"$claude"
  echo "[migrate] created CLAUDE.md with git-automation rules"
elif grep -qF "$BEGIN_MARKER" "$claude"; then
  # Replace whatever is between the markers (the old work-log block) in place.
  awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" -v repl="$rule_block" '
    BEGIN { in_block = 0; printed = 0 }
    $0 == begin { in_block = 1; if (!printed) { print repl; printed = 1 }; next }
    $0 == end   { in_block = 0; next }
    !in_block   { print }
  ' "$claude" >"$claude.tmp" && mv "$claude.tmp" "$claude"
  echo "[migrate] replaced managed block in CLAUDE.md with git-automation rules"
else
  printf '\n%s\n' "$rule_block" >>"$claude"
  echo "[migrate] appended git-automation rules to existing CLAUDE.md"
fi

# 4. Surface any unmanaged log.md references for manual review. The managed
#    block is handled above (and legitimately mentions log.md), so scan ONLY
#    the lines OUTSIDE the markers. Prose the user hand-wrote there is NOT
#    auto-deleted (too easy to mangle real content) — we flag it instead.
unmanaged="$(awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" '
  $0 == begin { in_block = 1; next }
  $0 == end   { in_block = 0; next }
  !in_block && /log\.md/ { print }
' "$claude")"
if [[ -n "$unmanaged" ]]; then
  echo "[migrate] WARNING: CLAUDE.md mentions log.md outside the managed block — review:" >&2
  printf '%s\n' "$unmanaged" >&2
fi

echo "[migrate] done for $name. Review the diff, then commit."
