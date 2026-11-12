# Pre-merge verification checklist

Run by someone other than the agent that wrote the branch: a separate
session, a second model, or a person. On the original project this was a
separate assistant session that read each pushed branch from `origin`,
followed by the owner's go-ahead. The rule there: nothing merges before
it has been verified from `origin`, with no exception.

**Branch:** `{{branch}}`  **Tip:** `{{sha}}`  **Brief:** {{TASK_ID}}
**Verifier:** {{who}}  **Date:** {{date}}

## 1. Read from origin, not from the report

- [ ] `git fetch origin && git checkout --detach origin/{{branch}}` in a
      clean worktree. The report is a claim; the branch is the evidence.
- [ ] The tip SHA matches the report.
- [ ] The branch starts from the base the brief named
      (`git merge-base origin/{{branch}} origin/{{main}}`).

## 2. Scope

- [ ] `git diff --stat origin/{{main}}...origin/{{branch}}` touches only
      files the brief put in scope. Every extra file is explained.
- [ ] Migrations: none, or exactly the ones the brief allowed, additive.
- [ ] No secrets, local paths, generated artefacts or private files staged.

## 3. Gates, re-run by you

- [ ] Fast checks (type check, lint at or below baseline, migrations check).
- [ ] Tests for the touched units pass.
- [ ] Full suite passes. If it was not run, the branch is not done.
- [ ] Shard plan check passes (every test unit in exactly one shard).
- [ ] CI is green for this exact SHA.

## 4. Invariants

- [ ] Every invariant the brief listed still has its locking test, and
      the test was not weakened, skipped or deleted (`git diff` the test files).
- [ ] New behaviour that touches permissions, tenancy or money has a
      negative test (the refused case), not only the happy path.

## 5. Acceptance, reached the way a user would

- [ ] Each acceptance item reproduced by you, as the role it names.
      An endpoint that returns 401 proves a route exists, not a feature.
- [ ] Each feature is reachable by clicking from the navigation, not only
      by typing its URL.
- [ ] Any UI text quoted in docs matches the running screen.

## 6. The report itself

- [ ] Every "done" claim has evidence. Spot-check at least two.
- [ ] Numbers are measured (command output), not estimated.
- [ ] "Not done" and "where the brief was wrong" are present when they apply.
- [ ] The living checklist (NOW / NEXT / SHIPPED) was updated in this branch.

## Verdict

- [ ] **Merge** - all boxes ticked.
- [ ] **Return** - list each failed box with what you saw.

Bounded loop: a branch returns to its agent at most twice for the same
item. After that, the item is recorded as open and decided by a person.
