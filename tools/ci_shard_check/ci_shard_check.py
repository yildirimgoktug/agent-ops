"""Check a CI shard plan against the test tree before any shard runs.

Splitting a test suite across CI shards buys wall time but adds a failure
mode a single `manage.py test` never had: a test directory that is missing
from the plan is silently never run, and CI still reports green.

So the plan is not trusted. This script derives the real set of test
units from the tree and fails unless the plan covers each of them exactly
once, or lists it as an explicit, printed exemption.

Unit of coverage
----------------
A *unit* is either

* a top-level directory under the root that owns a test module anywhere
  beneath it, or
* a test module sitting directly in the root.

It deliberately does NOT ask "is this an app?" (for example "does it have
an apps.py?"). A Django project package usually has no apps.py and can
still own tests; a check that enumerates apps cannot see them. Both kinds
of unit are valid `manage.py test` labels.

Plan format (JSON)
------------------
{
  "shards": [
    {"name": "small-apps", "apps": "catalog shipping"},
    {"name": "orders-1", "apps": "orders", "split": {"parts": 2, "index": 0}},
    {"name": "orders-2", "apps": "orders", "split": {"parts": 2, "index": 1}}
  ],
  "exempt": [
    {"unit": "test_helpers", "reason": "fixtures only, collects 0 tests"}
  ]
}

"apps" is a space-separated string or a list. A shard group that declares
"split" is dealt round-robin over the group's sorted test modules, so a
new test file joins a bucket the moment it exists and nobody edits the
plan. The check proves that the buckets tile the group exactly once.

Usage
-----
    python ci_shard_check.py --root backend --plan backend/ci_shards.json
    python ci_shard_check.py --root backend --matrix   # JSON for a CI matrix

Exit status: 0 when the plan holds, 1 when it does not, 2 on a malformed
plan. Standard library only.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

DEFAULT_PATTERN = "test*.py"
DEFAULT_SKIP_DIRS = {
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
}


class PlanError(ValueError):
    """The plan file itself is malformed (as opposed to not matching the tree)."""


def _is_test_file(path: Path, pattern: str) -> bool:
    return path.is_file() and fnmatch.fnmatch(path.name, pattern) and path.suffix == ".py"


def _walk_tests(base: Path, pattern: str, skip_dirs: set[str]):
    for path in base.rglob("*.py"):
        if any(part in skip_dirs for part in path.relative_to(base).parts):
            continue
        if _is_test_file(path, pattern):
            yield path


def units_with_tests(root: Path, pattern: str = DEFAULT_PATTERN,
                     skip_dirs: set[str] | None = None) -> set[str]:
    """Every top-level directory owning a test module, plus root-level test modules."""
    skip = DEFAULT_SKIP_DIRS if skip_dirs is None else skip_dirs
    found: set[str] = set()
    for entry in sorted(root.iterdir()):
        if entry.name in skip or entry.name.startswith("."):
            continue
        if entry.is_dir():
            if next(_walk_tests(entry, pattern, skip), None) is not None:
                found.add(entry.name)
        elif _is_test_file(entry, pattern):
            found.add(entry.stem)
    return found


def modules_of(root: Path, units: list[str], pattern: str = DEFAULT_PATTERN,
               skip_dirs: set[str] | None = None) -> list[str]:
    """Every test module in `units`, as sorted dotted labels.

    Sorted so that dealing into buckets is deterministic: the same tree
    always produces the same buckets on every runner.
    """
    skip = DEFAULT_SKIP_DIRS if skip_dirs is None else skip_dirs
    labels: list[str] = []
    for unit in units:
        base = root / unit
        if not base.is_dir():
            labels.append(unit)  # a root-level test module is its own label
            continue
        for path in _walk_tests(base, pattern, skip):
            rel = path.relative_to(root).with_suffix("")
            labels.append(".".join(rel.parts))
    return sorted(labels)


def _apps(shard: dict) -> list[str]:
    apps = shard["apps"]
    return apps.split() if isinstance(apps, str) else list(apps)


def resolve_labels(root: Path, shard: dict, pattern: str = DEFAULT_PATTERN,
                   skip_dirs: set[str] | None = None) -> list[str]:
    """The test labels this shard actually runs."""
    apps = _apps(shard)
    split = shard.get("split")
    if not split:
        return apps
    every = modules_of(root, apps, pattern, skip_dirs)
    return [m for i, m in enumerate(every) if i % split["parts"] == split["index"]]


def load_plan(path: Path) -> tuple[list[dict], dict[str, str]]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PlanError(f"plan file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PlanError(f"plan file is not valid JSON: {exc}") from exc
    if not isinstance(plan, dict):
        raise PlanError("plan must be a JSON object with a \"shards\" list")
    shards = plan.get("shards")
    if not isinstance(shards, list) or not shards:
        raise PlanError('plan needs a non-empty "shards" list')
    names = set()
    for i, shard in enumerate(shards):
        if not isinstance(shard, dict) or "name" not in shard or "apps" not in shard:
            raise PlanError(f'shard #{i} needs "name" and "apps"')
        if shard["name"] in names:
            raise PlanError(f'shard name {shard["name"]!r} is used twice')
        names.add(shard["name"])
        apps = shard["apps"]
        if not (isinstance(apps, str) or
                (isinstance(apps, list) and all(isinstance(a, str) for a in apps))):
            raise PlanError(
                f'shard {shard["name"]!r}: "apps" must be a string or a list of strings'
            )
        if not _apps(shard):
            raise PlanError(f'shard {shard["name"]!r} names no apps')
        split = shard.get("split")
        if split is not None:
            if not isinstance(split, dict):
                raise PlanError(f'shard {shard["name"]!r}: "split" must be an object')
            parts, index = split.get("parts"), split.get("index")
            if not (isinstance(parts, int) and isinstance(index, int) and parts >= 2):
                raise PlanError(
                    f'shard {shard["name"]!r}: "split" needs integer "parts" >= 2 and "index"'
                )
    exempt: dict[str, str] = {}
    entries = plan.get("exempt", [])
    if not isinstance(entries, list):
        raise PlanError('"exempt" must be a list of {"unit", "reason"} objects')
    for entry in entries:
        if not isinstance(entry, dict):
            raise PlanError('every "exempt" entry must be an object with "unit" and "reason"')
        if not entry.get("unit") or not str(entry.get("reason", "")).strip():
            raise PlanError('every "exempt" entry needs a "unit" and a written "reason"')
        exempt[entry["unit"]] = entry["reason"]
    return shards, exempt


def _check_splits(root: Path, shards: list[dict], problems: list[str],
                  pattern: str, skip_dirs: set[str] | None) -> None:
    """Every split group tiles its units exactly once: no gap, no overlap."""
    groups: dict[str, list[dict]] = {}
    for shard in shards:
        groups.setdefault(" ".join(sorted(_apps(shard))), []).append(shard)

    owner: dict[str, str] = {}
    for key in groups:
        for app in key.split():
            if app in owner and owner[app] != key:
                problems.append(
                    f"{app} appears in two different shard groups "
                    f"({owner[app]!r} and {key!r}) - it would run twice"
                )
            owner[app] = key

    for key, members in sorted(groups.items()):
        splits = [m for m in members if m.get("split")]
        if not splits:
            if len(members) > 1:
                problems.append(
                    f"{key} is in {len(members)} shards but declares no "
                    '"split" - add one, or put it in a single shard'
                )
            continue
        if len(splits) != len(members):
            problems.append(
                f"{key} is split in some shards and whole in others - "
                "every shard naming it must declare the same split"
            )
            continue
        parts_set = {m["split"]["parts"] for m in splits}
        if len(parts_set) != 1:
            problems.append(f"{key} declares conflicting split parts: {sorted(parts_set)}")
            continue
        (parts,) = parts_set
        indexes = sorted(m["split"]["index"] for m in splits)
        if indexes != list(range(parts)):
            problems.append(
                f"{key} is split into {parts} but its buckets are {indexes} - "
                f"they must be exactly {list(range(parts))}, each once"
            )
            continue
        apps = key.split()
        every = modules_of(root, apps, pattern, skip_dirs)
        seen: list[str] = []
        for m in splits:
            seen.extend(resolve_labels(root, m, pattern, skip_dirs))
        missing = sorted(set(every) - set(seen))
        if missing:
            problems.append(f"{key}: modules in NO bucket (never tested): {', '.join(missing)}")
        overlap = sorted({m for m in seen if seen.count(m) > 1})
        if overlap:
            problems.append(f"{key}: modules in MORE THAN ONE bucket: {', '.join(overlap)}")


def check(root: Path, shards: list[dict], exempt: dict[str, str],
          pattern: str = DEFAULT_PATTERN, skip_dirs: set[str] | None = None) -> list[str]:
    """Return a list of problems; an empty list means the plan holds."""
    by_app: dict[str, list[dict]] = {}
    for shard in shards:
        for app in _apps(shard):
            by_app.setdefault(app, []).append(shard)

    real = units_with_tests(root, pattern, skip_dirs)
    seen = set(by_app)
    problems: list[str] = []

    missing = sorted(real - seen - set(exempt))
    if missing:
        problems.append(
            "units that own tests but NO shard runs (they would silently "
            f"never be tested): {', '.join(missing)}"
        )
    unknown = sorted(seen - real)
    if unknown:
        problems.append(f"shard entries that own no test file: {', '.join(unknown)}")
    duplicated = sorted(
        app for app, entries in by_app.items()
        if len(entries) > 1 and not all(e.get("split") for e in entries)
    )
    if duplicated:
        problems.append(f"units listed in more than one shard: {', '.join(duplicated)}")
    both = sorted(seen & set(exempt))
    if both:
        problems.append(f"listed as exempt AND in a shard: {', '.join(both)}")
    stale = sorted(set(exempt) - real)
    if stale:
        problems.append(f"exempt entries that own no test file (delete them): {', '.join(stale)}")
    _check_splits(root, shards, problems, pattern, skip_dirs)
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail if the CI shard plan does not cover every test unit exactly once."
    )
    parser.add_argument("--root", default=".", help="directory that holds the test units (default: .)")
    parser.add_argument("--plan", help="plan JSON (default: <root>/ci_shards.json)")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN,
                        help=f"test module filename pattern (default: {DEFAULT_PATTERN})")
    parser.add_argument("--skip-dir", action="append", default=[],
                        help="extra directory name to ignore; may be repeated")
    parser.add_argument("--matrix", action="store_true",
                        help="print the resolved plan as JSON for a CI matrix")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: --root {args.root} is not a directory", file=sys.stderr)
        return 2
    plan_path = Path(args.plan) if args.plan else root / "ci_shards.json"
    skip = DEFAULT_SKIP_DIRS | set(args.skip_dir)

    try:
        shards, exempt = load_plan(plan_path)
    except PlanError as exc:
        print(f"malformed shard plan: {exc}", file=sys.stderr)
        return 2

    problems = check(root, shards, exempt, args.pattern, skip)
    if problems:
        print(f"{plan_path.name} does not match {root}:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(f"\nFix {plan_path.name}; it is the single source that the CI "
              "matrix and this check both read.", file=sys.stderr)
        return 1

    if args.matrix:
        print(json.dumps([
            {
                "name": s["name"],
                "apps": " ".join(_apps(s)),
                "labels": " ".join(resolve_labels(root, s, args.pattern, skip)),
            }
            for s in shards
        ]))
        return 0

    real = units_with_tests(root, args.pattern, skip)
    print(f"shard plan OK - {len(shards)} shards cover "
          f"{len(real) - len(exempt)} of {len(real)} units with tests:")
    for shard in shards:
        split = shard.get("split")
        detail = " ".join(_apps(shard))
        if split:
            n = len(resolve_labels(root, shard, args.pattern, skip))
            detail += f"  [bucket {split['index'] + 1}/{split['parts']}, {n} modules]"
        print(f"  {shard['name']:32} {detail}")
    # Always print the exemptions, even when there are none, so a reader
    # can see at a glance that nothing is being quietly skipped.
    if exempt:
        print("exempt (NOT run by CI):")
        for unit, reason in sorted(exempt.items()):
            print(f"  {unit:32} {reason}")
    else:
        print("exempt: none - every unit with tests is in a shard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
