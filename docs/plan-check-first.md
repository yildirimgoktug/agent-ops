# Why the shard plan is checked before any shard runs

## The trade

A single `manage.py test` discovers everything. When the suite becomes
too slow for one CI job, you split it into shards, and each shard runs
only what the plan names. That buys wall time and costs one guarantee:
a test directory missing from the plan is never run, and CI is green.

On the original project (all figures from its docs and commit messages):

- The full backend suite was 6077 tests taking 21268 s (about 5.9 hours)
  serially. The single CI job was killed at 50m22s by its 50-minute
  timeout, so the required check could never go green.
- It was split into 7 shards, each using Django's `--parallel`, behind a
  plan job. Later re-tuned to 13 shards when the hosted runner dropped
  from 4 to 2 vCPU. On that run all 13 shards were green and the slowest
  took 15m29s, against a 24-minute soft budget.

## Why "first"

The plan job runs the checker and produces the matrix. Shards depend on
it. If the plan is wrong, nothing runs and the aggregate check fails with
a message that names the missing unit. Checking after the shards (or
never) means a green run that silently skipped tests.

## The checker had a blind spot too

The first version asked "is this directory an app?" by looking for
`apps.py`. The Django project package has no `apps.py`. It owned 12
security tests (allowed hosts, the production settings validator), was
in no shard, and the checker could not see it. CI ran 6065 tests in 422
modules; local discovery found 6077 in 424. Exactly two modules short.

The fix changed the question to "does this directory own a test file?".
A second pass found the same blind spot one level up: a test module
sitting directly in the backend root belonged to no directory. Both
shapes are now units.

The lesson that carries over: **measure parity**. Count tests and modules
in a sharded run and in a local full discovery, and compare. A guard you
have not negative-tested is an assumption. The original checker was
negative-tested by deliberately breaking the plan in each way it should
catch; `tools/ci_shard_check/tests/` does the same.

## Related rules from the same project

- **Split by rule, not by list.** A large app is dealt round-robin into
  buckets, so a new test file joins a bucket without anyone editing the
  plan.
- **One source.** The workflow reads its matrix from the checker's
  `--matrix` output, not from its own copy of the JSON.
- **Soft budget.** Each shard prints its wall time and fails at 24
  minutes with "split it in ci_shards.json", well before the 40-minute
  hard timeout.
- **Stable aggregate name.** One aggregate job keeps the required-check
  name, so adding or renaming shards never leaves branch protection
  waiting on a check that no longer exists.
- **Run on task branches.** The workflow triggers on `feat/**` pushes,
  so a branch is verified before it merges, not after.
