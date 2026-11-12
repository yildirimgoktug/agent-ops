# ci_shard_check

A standalone, standard-library-only check for sharded test suites. It
fails CI **before any shard starts** if the shard plan does not cover
every test unit exactly once.

Adapted from the checker used on the original project; rewritten to be
project-neutral and configurable.

## The problem it solves

One `manage.py test` runs everything it discovers. Once you split the
suite into shards, each shard only runs what the plan names. A directory
that is missing from the plan is never tested, and CI is still green.

On the original project this happened even with a checker in place: the
first version asked "is this directory an app (does it have `apps.py`)?".
The Django project package has no `apps.py`, owned 12 security tests,
and was in no shard. CI ran 6065 tests in 422 modules while local
discovery found 6077 in 424. The check now asks "does this directory own
a test file?" instead.

## What counts as a unit

- a top-level directory under `--root` that owns a file matching
  `--pattern` (default `test*.py`) anywhere beneath it, or
- a matching test module that sits directly in `--root`.

`__pycache__`, `.git`, `node_modules`, virtualenvs and dot-directories
are ignored. Add more with `--skip-dir NAME`.

## What it checks

| Fails when | Why |
|---|---|
| a unit owns tests but is in no shard and not exempt | it would never run |
| a shard names something that owns no tests | typo or stale entry |
| a unit is in two shards without a `split` | it would run twice |
| a unit is both exempt and sharded | contradictory plan |
| an exemption names a unit that owns no tests | stale exemption |
| a split group's buckets are not exactly `0..parts-1` | a bucket is missing or doubled |
| the resolved buckets do not cover the group's modules exactly once | gap or overlap |

Every exemption needs a written reason, and every run prints the
exemptions (or "none"). An exemption anyone can see beats a rule no one
can.

## Splitting by rule, not by list

A large unit is split by declaring buckets:

```json
{"name": "orders-1", "apps": "orders", "split": {"parts": 2, "index": 0}},
{"name": "orders-2", "apps": "orders", "split": {"parts": 2, "index": 1}}
```

The group's test modules are sorted and dealt round-robin. A new test
file joins a bucket the moment it exists; nobody edits the plan.
Round-robin rather than contiguous halves spreads slow modules, which
tend to cluster by name prefix. Several small units can share one split
group (`"apps": "a b c"`).

## Usage

The checker needs a plan file. By default it reads `<root>/ci_shards.json`;
pass `--plan` to use another path. `example/ci_shards.json` is a working
plan to copy and adapt.

```bash
python tools/ci_shard_check/ci_shard_check.py --root backend
python tools/ci_shard_check/ci_shard_check.py --root backend --plan ci/shards.json
python tools/ci_shard_check/ci_shard_check.py --root backend --matrix   # JSON for CI
```

Exit codes: `0` plan holds, `1` plan does not match the tree, `2` plan
file malformed.

`--matrix` prints `[{"name", "apps", "labels"}]`. Feed `labels` to
`manage.py test`. The workflow reads the matrix from the checker, so
the labels are computed in one place.

See `example/` for a five-unit layout (including a project package
without `apps.py` and an exempt root-level helper) and
`example-workflow.yml` for the GitHub Actions wiring.

## Tests

```bash
python -m pytest tools/ci_shard_check/tests -q
```

## Limits

- It checks **files**, not tests. A module that defines no test cases
  passes the check. Compare test counts between a sharded run and a
  local full discovery from time to time.
- It does not balance shard times. Measure wall time per shard and move
  units or add buckets by hand.
- Not tested against non-Django runners. For pytest, use the `labels`
  as paths after replacing `.` with `/` and adding `.py`, or adapt
  `modules_of()`.
