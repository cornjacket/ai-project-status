#!/usr/bin/env bash
# Daily entry point for the Claude remote routine.
#
# The Claude GitHub App identity used by remote routines cannot push to
# the default branch (manifests as a misleading "non-fast-forward" error
# from the local git proxy). So we push the run's commit to a side
# branch named auto/status-YYYY-MM-DD and let
# .github/workflows/auto-merge-status.yml fast-forward it onto main.
# See README.md "Daily tracking" for the full architecture.

set -euo pipefail

cd "$(dirname "$0")/.."

DATE=$(date -u +%Y-%m-%d)
BRANCH="auto/status-$DATE"

pip install --quiet pyyaml 2>/dev/null || pip install --user --quiet pyyaml

git fetch origin
git checkout -b "$BRANCH"

python3 tools/run.py

if git diff --quiet "origin/main..HEAD"; then
  echo "[daily] no new work; nothing to push"
else
  git push -u origin "$BRANCH"
  echo "[daily] pushed $BRANCH; auto-merge-status workflow will land it on main"
fi
