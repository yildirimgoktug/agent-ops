# Where each part comes from

The original project is a private web platform (Django backend, React
frontend) built between May and November 2026 by one developer directing
several Claude Code agent sessions. Its source stays private. This page
says which parts of this playbook are taken from what that project
recorded, and which are suggestions added here.

| Part | Status | Basis in the original project |
|---|---|---|
| Waves of parallel agents with disjoint file ownership | adapted | a planning doc's "three waves", each sprint with an "Owns" column, and its branch mechanics section |
| Detached worktree per agent, `pull --rebase`, never force-push | adapted | same planning doc |
| One branch per task, pushed, verified from `origin` before merge | adapted | sprint checklist "Branch policy" and the rule recorded after a later sprint |
| Agent never opens PRs or merges; owner merges | adapted | sprint checklist entries recording agent workflow rules |
| Independent verification by a separate session, then owner gate | adapted | sprint checklist and the frontend addendum's verification protocol |
| Bounded fix loop (two iterations), no agent-vs-agent loops | adapted | the frontend addendum's verification protocol |
| Step 0 sync + guard, adversarial self-review | adapted | sprint checklist "Conventions" |
| Full suite at the close of every task | adapted | sprint checklist "Close rule"; the suite-repair doc |
| Invariant table with "enforced at" + "test that locks it" | adapted | the RBAC reference doc, section "Hard invariants" |
| Living checklist with NOW / NEXT / SHIPPED, updated in the same branch | adapted | the sprint checklist's own maintenance rules |
| Docs index with "update trigger" per doc; code wins over docs | adapted | the docs index |
| `ci_shard_check` and the plan-first workflow | adapted (rewritten) | `ci_shard_check.py`, `ci_shards.json`, `test.yml` |
| `templates/CLAUDE.md.template` | reconstructed | the original CLAUDE.md was not committed; rules are rebuilt from where docs, code comments and commit messages quote it |
| `scripts/agents-up.*` | suggested | mechanics adapted from the planning doc; no launch script existed in the repo |
| `scripts/agents-down.*` | suggested | cleanup was done by hand after archiving |
| Worked invariant example (notes service) | suggested | generic, not from the product |
| Lessons on worktree hygiene beyond what is listed as adapted | suggested | |

## Earlier approach that was retired

Before the wave-and-verify loop, the project used three Claude Code
sub-agents defined in the repository: a project manager that owned a
backlog folder and dispatched work, and a backend and a frontend
engineer. The docs index lists that "PM-dispatch workflow" as superseded
and archives it. Two ideas from it survive here: every backlog row named
its acceptance and its test file, and only one role edited the tracker.
