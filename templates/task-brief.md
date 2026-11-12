# Task brief: {{TASK_ID}} - {{SHORT_TITLE}}

<!--
  One brief per agent. Fields are drawn from the original project's
  briefs and backlog rows (source, owner, files owned, acceptance, tests,
  gates, "deliberately not done"). Keep it to one screen if you can.
-->

**Branch:** `{{BRANCH_PREFIX}}/{{TASK_ID}}-{{SLUG}}` from `{{BASE_REF}}`
**Worktree:** `{{WORKTREE_PATH}}`
**Wave:** {{WAVE}} (runs in parallel with: {{OTHER_TASK_IDS or "none"}})
**Source:** {{why this task exists: doc + section, finding ID, owner's words}}

## Step 0 - prove the base

- `git fetch && git merge-base HEAD {{BASE_REF}}` equals `{{EXPECTED_SHA}}`.
- `grep -n "{{SOMETHING_THE_BASE_MUST_CONTAIN}}" {{FILE}}` finds it.
- Record baselines: lint count, test count for the touched apps.

If any of these fail, stop and report. Do not start on the wrong base.

## Goal

{{One or two sentences. The outcome a user can observe, not the code to write.}}

## Files in scope (you own these)

- `{{path/to/file_a}}`
- `{{path/to/dir_b/}}` (everything under it)
- New files allowed under: `{{path/}}`

## Files out of scope (do not edit)

- `{{path/owned/by/another/agent}}` - owned by {{OTHER_TASK_ID}}
- Migrations: {{"none allowed" | "one additive migration allowed in <app>"}}
- Anything not listed above. If you need it, stop and report why.

## Acceptance

Each item is observable and checkable by someone who did not write the code.

1. {{As <role>, doing <action> on <screen/endpoint> results in <observable result>.}}
2. {{...}}

## Invariants that must hold

- {{INV-ID}}: {{one line}} - locked by `{{test path::name}}`
- New invariant introduced by this task, if any: {{ID, statement, test}}

## How it will be verified

The reviewer will, from `origin`, not from your report:
- run `{{TEST_COMMAND for touched apps}}` and the full suite `{{FULL_SUITE_COMMAND}}`;
- run the shard plan check `{{PLAN_CHECK_COMMAND}}`;
- reach each acceptance item {{as each role / from the UI / with this request}};
- {{any task-specific probe: e.g. "try the action as a role that must be refused"}}.

## Deliberately NOT in this task

- {{Things a reader might expect but that are excluded, with the reason.}}

## Report back with

- branch and tip SHA; per acceptance item: done / not done + evidence;
- measured numbers (tests run, lint count, timings);
- "Where this brief was wrong" - any premise you checked and found false;
- open items, each with its evidence.
