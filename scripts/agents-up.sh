#!/usr/bin/env bash
# agents-up.sh - create one git worktree per agent, all from the same base.
#
# Mechanics adapted from the original project's parallel-wave notes: each
# parallel agent works in its own DETACHED worktree cut from one shared
# branch, owns a disjoint set of files, and pushes back with
# pull --rebase, never --force. The script itself is suggested.
#
# Usage:
#   scripts/agents-up.sh --base origin/feat/wave-1 --dir ../wt alpha beta gamma
#   scripts/agents-up.sh --base origin/feat/wave-1 --dry-run alpha beta
#
# Creates ../wt/alpha, ../wt/beta, ... Never deletes, resets or pushes anything.
set -euo pipefail

BASE=""
DIR="../agent-worktrees"
DRY_RUN=0
NAMES=()

usage() {
  sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="${2:-}"; shift 2 ;;
    --dir) DIR="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage 0 ;;
    -*) echo "unknown option: $1" >&2; usage 2 ;;
    *) NAMES+=("$1"); shift ;;
  esac
done

[ -n "$BASE" ] || { echo "error: --base is required (e.g. origin/feat/wave-1)" >&2; exit 2; }
[ "${#NAMES[@]}" -gt 0 ] || { echo "error: give at least one agent name" >&2; exit 2; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "error: run inside a git repository" >&2; exit 2; }
git rev-parse --verify --quiet "$BASE^{commit}" >/dev/null || { echo "error: base '$BASE' does not resolve; fetch first?" >&2; exit 2; }

# The shared branch the agents push to, if the base is a remote branch.
PUSH_BRANCH="${BASE#origin/}"

for name in "${NAMES[@]}"; do
  case "$name" in *[!A-Za-z0-9._-]*) echo "error: bad agent name '$name'" >&2; exit 2 ;; esac
  path="$DIR/$name"
  if [ -e "$path" ]; then
    echo "skip: $path already exists" >&2
    continue
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "would run: git worktree add --detach \"$path\" \"$BASE\""
  else
    git worktree add --detach "$path" "$BASE"
  fi
done

cat <<EOF

Next, per agent:
  1. Open a separate agent session in its worktree (one per directory under $DIR).
  2. Give it its task brief; the brief lists the files it owns.
  3. When done, inside the worktree:
       git add <explicit paths>      # never 'git add -A'
       git commit
       git pull --rebase origin $PUSH_BRANCH
       git push origin HEAD:$PUSH_BRANCH   # if rejected: pull --rebase again; never --force
  4. Remove finished worktrees with scripts/agents-down.sh.
EOF
