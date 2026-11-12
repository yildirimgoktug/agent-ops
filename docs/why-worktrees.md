# Why one worktree per agent

Two agents in one working directory share one index, one checkout and one
set of build artefacts. One agent's `git checkout`, half-written file or
failing build becomes the other's problem. A git worktree gives each
agent its own directory and checkout while sharing one object store, so
it is cheap to create and every commit is visible to the others at once.

## How the original project used them

- Work was planned in **waves**. Tasks inside a wave touched no shared
  file and ran as parallel agent sessions. Waves ran one after another
  when a later wave built on an earlier wave's files.
- Each brief had an "owns" column: the exact files and directories that
  agent could change.
- One shared branch was created and pushed once, before any agent
  started. Each agent worked in its own **detached** worktree cut from
  that branch, then pushed with `git pull --rebase` followed by
  `git push origin HEAD:<branch>`. Because files were disjoint, the
  rebase was clean. A rejected push meant pull-rebase and retry, never
  force-push.
- Later, the policy narrowed: one branch per task, pushed to `origin` so
  it could be verified from there, deleted after merge. At rest the remote
  held only `main` and tags.

`scripts/agents-up.sh` / `.ps1` reproduce the first pattern's worktrees
(detached, cut from one base), but their hint has each agent push its own
branch (`feat/<name>`) rather than the shared one.

## What went wrong, and what to do instead

Worktrees are cheap to create and easy to forget. On the original project,
by the time of a cleanup sprint the main development machine held about
100 worktrees and 143 local branches. Of those branches, 113 were not merged and held
400 commits that `main` did not have; 198 of those commits existed on that
one machine only. Some worktrees could not be removed without elevated
rights, because container builds had written root-owned files into them.
The cleanup had to archive everything into a git bundle and verify the
bundle before deleting anything.

Suggested, not from the original project:
- Remove a worktree when its task merges. `scripts/agents-down.sh`
  refuses to remove a worktree that is dirty or has commits on no remote.
- Do not let containers write into worktrees as root; mount build output
  elsewhere or run the container as your user.
- Keep worktrees outside the main checkout (for example `../wt/<name>`),
  so tools that scan the repository do not walk into them.
- Before any bulk cleanup, run `git rev-list --count origin/main..<branch>`
  for every branch. Zero means fully contained; anything else is work
  that only exists there.
