#!/usr/bin/env bash
# agents-down.sh - remove agent worktrees, but only ones that lose nothing.
#
# Default is a dry run: it reports, for each worktree, whether it is clean
# and whether its commits are reachable from a remote. Nothing is removed.
#
#   --yes    remove worktrees that are clean AND fully pushed
#   --force  also remove dirty or unpushed worktrees (their work is LOST)
#
# Branches are never deleted. Suggested, not from the original project
# (which cleaned up by hand after archiving; see docs/why-worktrees.md).
#
# Usage:
#   scripts/agents-down.sh --dir ../wt alpha beta
#   scripts/agents-down.sh --dir ../wt --yes alpha beta
set -euo pipefail

DIR="../agent-worktrees"
YES=0
FORCE=0
NAMES=()

while [ $# -gt 0 ]; do
  case "$1" in
    --dir) DIR="${2:-}"; shift 2 ;;
    --yes) YES=1; shift ;;
    --force) FORCE=1; YES=1; shift ;;
    -h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) NAMES+=("$1"); shift ;;
  esac
done

[ "${#NAMES[@]}" -gt 0 ] || { echo "error: give at least one agent name" >&2; exit 2; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "error: run inside a git repository" >&2; exit 2; }

for name in "${NAMES[@]}"; do
  path="$DIR/$name"
  if [ ! -d "$path" ]; then
    echo "$name: no worktree at $path"
    continue
  fi
  dirty=$(git -C "$path" status --porcelain | wc -l | tr -d ' ')
  unpushed=$(git -C "$path" rev-list HEAD --not --remotes | wc -l | tr -d ' ')
  state="clean, pushed"
  [ "$dirty" -eq 0 ] || state="$dirty uncommitted change(s)"
  [ "$unpushed" -eq 0 ] || state="$state; $unpushed commit(s) on no remote"

  if [ "$dirty" -eq 0 ] && [ "$unpushed" -eq 0 ]; then
    if [ "$YES" -eq 1 ]; then
      git worktree remove "$path" && echo "$name: removed ($state)"
    else
      echo "$name: $state - would remove (pass --yes)"
    fi
  else
    if [ "$FORCE" -eq 1 ]; then
      git worktree remove --force "$path" && echo "$name: FORCE-removed ($state)"
    else
      echo "$name: KEPT - $state. Push or archive it first, or pass --force to discard."
    fi
  fi
done

[ "$YES" -eq 1 ] && git worktree prune
exit 0
