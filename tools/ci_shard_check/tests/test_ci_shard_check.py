"""Tests for ci_shard_check. Every case builds its own tree under tmp_path."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIR))

import ci_shard_check as csc  # noqa: E402

EXAMPLE = TOOL_DIR / "example"


def make_tree(root: Path, files: list[str]) -> Path:
    for rel in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# test module\n", encoding="utf-8")
    return root


def write_plan(root: Path, shards: list[dict], exempt: list[dict] | None = None) -> Path:
    plan = {"shards": shards}
    if exempt is not None:
        plan["exempt"] = exempt
    path = root / "ci_shards.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    return path


def run(root: Path, *extra: str) -> int:
    return csc.main(["--root", str(root), *extra])


BASIC = ["alpha/tests/test_a.py", "beta/tests/test_b.py"]


# --- the example project -------------------------------------------------

def test_example_project_passes(capsys):
    assert run(EXAMPLE) == 0
    out = capsys.readouterr().out
    assert "shard plan OK" in out
    assert "test_helpers" in out  # the exemption is printed


def test_example_matrix_tiles_the_split_app(capsys):
    assert run(EXAMPLE, "--matrix") == 0
    matrix = json.loads(capsys.readouterr().out)
    buckets = [m["labels"].split() for m in matrix if m["apps"] == "orders"]
    union = sorted(label for bucket in buckets for label in bucket)
    assert union == csc.modules_of(EXAMPLE, ["orders"])
    assert len(union) == len(set(union))


# --- unit discovery ------------------------------------------------------

def test_package_without_apps_py_is_a_unit(tmp_path):
    make_tree(tmp_path, ["project/tests/test_settings.py", "alpha/apps.py", "alpha/tests/test_a.py"])
    assert csc.units_with_tests(tmp_path) == {"project", "alpha"}


def test_skipped_dirs_are_ignored(tmp_path):
    make_tree(tmp_path, BASIC + ["node_modules/x/test_x.py", "alpha/__pycache__/test_c.py"])
    assert csc.units_with_tests(tmp_path) == {"alpha", "beta"}
    assert csc.modules_of(tmp_path, ["alpha"]) == ["alpha.tests.test_a"]


def test_custom_pattern(tmp_path):
    make_tree(tmp_path, ["alpha/a_test.py", "beta/test_b.py"])
    assert csc.units_with_tests(tmp_path, pattern="*_test.py") == {"alpha"}


# --- coverage failures ---------------------------------------------------

def test_plan_covering_everything_passes(tmp_path):
    make_tree(tmp_path, BASIC)
    write_plan(tmp_path, [{"name": "all", "apps": "alpha beta"}])
    assert run(tmp_path) == 0


def test_apps_may_be_a_list(tmp_path):
    make_tree(tmp_path, BASIC)
    write_plan(tmp_path, [{"name": "all", "apps": ["alpha", "beta"]}])
    assert run(tmp_path) == 0


def test_unit_missing_from_plan_fails_and_is_named(tmp_path, capsys):
    make_tree(tmp_path, BASIC)
    write_plan(tmp_path, [{"name": "one", "apps": "alpha"}])
    assert run(tmp_path) == 1
    assert "beta" in capsys.readouterr().err


def test_root_level_test_module_missing_fails(tmp_path, capsys):
    make_tree(tmp_path, BASIC + ["test_smoke.py"])
    write_plan(tmp_path, [{"name": "all", "apps": "alpha beta"}])
    assert run(tmp_path) == 1
    assert "test_smoke" in capsys.readouterr().err


def test_root_level_test_module_exempt_passes_and_is_printed(tmp_path, capsys):
    make_tree(tmp_path, BASIC + ["test_utils.py"])
    write_plan(tmp_path, [{"name": "all", "apps": "alpha beta"}],
               [{"unit": "test_utils", "reason": "fixtures only"}])
    assert run(tmp_path) == 0
    assert "test_utils" in capsys.readouterr().out


def test_exempt_and_sharded_fails(tmp_path):
    make_tree(tmp_path, BASIC)
    write_plan(tmp_path, [{"name": "all", "apps": "alpha beta"}],
               [{"unit": "beta", "reason": "x"}])
    assert run(tmp_path) == 1


def test_stale_exemption_fails(tmp_path):
    make_tree(tmp_path, BASIC)
    write_plan(tmp_path, [{"name": "all", "apps": "alpha beta"}],
               [{"unit": "gone", "reason": "was removed"}])
    assert run(tmp_path) == 1


def test_unit_in_two_shards_without_split_fails(tmp_path):
    make_tree(tmp_path, BASIC)
    write_plan(tmp_path, [{"name": "a", "apps": "alpha beta"}, {"name": "b", "apps": "beta"}])
    assert run(tmp_path) == 1


def test_shard_naming_unit_without_tests_fails(tmp_path):
    make_tree(tmp_path, BASIC)
    (tmp_path / "gamma").mkdir()
    write_plan(tmp_path, [{"name": "all", "apps": "alpha beta gamma"}])
    assert run(tmp_path) == 1


# --- split rules ---------------------------------------------------------

SPLIT_TREE = [f"big/tests/test_{n}.py" for n in "abcde"] + ["small/tests/test_s.py"]


def split_shards(parts: int, indexes: list[int]) -> list[dict]:
    shards = [{"name": f"big-{n}", "apps": "big", "split": {"parts": parts, "index": i}}
              for n, i in enumerate(indexes)]
    return shards + [{"name": "small", "apps": "small"}]


def test_split_that_tiles_passes(tmp_path):
    make_tree(tmp_path, SPLIT_TREE)
    write_plan(tmp_path, split_shards(2, [0, 1]))
    assert run(tmp_path) == 0


def test_split_is_round_robin_over_sorted_modules(tmp_path):
    make_tree(tmp_path, SPLIT_TREE)
    shard = {"name": "big-0", "apps": "big", "split": {"parts": 2, "index": 0}}
    assert csc.resolve_labels(tmp_path, shard) == [
        "big.tests.test_a", "big.tests.test_c", "big.tests.test_e"]


def test_split_missing_bucket_fails(tmp_path, capsys):
    make_tree(tmp_path, SPLIT_TREE)
    write_plan(tmp_path, split_shards(3, [0, 1]))
    assert run(tmp_path) == 1
    assert "buckets" in capsys.readouterr().err


def test_split_duplicate_bucket_fails(tmp_path):
    make_tree(tmp_path, SPLIT_TREE)
    write_plan(tmp_path, split_shards(2, [0, 0]))
    assert run(tmp_path) == 1


def test_split_conflicting_parts_fails(tmp_path):
    make_tree(tmp_path, SPLIT_TREE)
    shards = [
        {"name": "big-0", "apps": "big", "split": {"parts": 2, "index": 0}},
        {"name": "big-1", "apps": "big", "split": {"parts": 3, "index": 1}},
        {"name": "small", "apps": "small"},
    ]
    write_plan(tmp_path, shards)
    assert run(tmp_path) == 1


def test_split_in_one_shard_whole_in_another_fails(tmp_path):
    make_tree(tmp_path, SPLIT_TREE)
    shards = [
        {"name": "big-0", "apps": "big", "split": {"parts": 2, "index": 0}},
        {"name": "big-whole", "apps": "big"},
        {"name": "small", "apps": "small"},
    ]
    write_plan(tmp_path, shards)
    assert run(tmp_path) == 1


def test_unit_in_two_split_groups_fails(tmp_path):
    make_tree(tmp_path, SPLIT_TREE)
    shards = [
        {"name": "g1-0", "apps": "big small", "split": {"parts": 2, "index": 0}},
        {"name": "g1-1", "apps": "big small", "split": {"parts": 2, "index": 1}},
        {"name": "g2-0", "apps": "big", "split": {"parts": 2, "index": 0}},
        {"name": "g2-1", "apps": "big", "split": {"parts": 2, "index": 1}},
    ]
    write_plan(tmp_path, shards)
    assert run(tmp_path) == 1


def test_new_test_file_joins_a_bucket_without_editing_the_plan(tmp_path, capsys):
    make_tree(tmp_path, SPLIT_TREE)
    write_plan(tmp_path, split_shards(2, [0, 1]))
    assert run(tmp_path) == 0
    make_tree(tmp_path, ["big/tests/test_new.py"])
    capsys.readouterr()
    assert run(tmp_path, "--matrix") == 0
    labels = " ".join(m["labels"] for m in json.loads(capsys.readouterr().out))
    assert "big.tests.test_new" in labels


# --- malformed plans -----------------------------------------------------

@pytest.mark.parametrize("plan", [
    "not json",
    json.dumps({"shards": []}),
    json.dumps({"shards": [{"name": "x"}]}),
    json.dumps({"shards": [{"name": "x", "apps": "a"}, {"name": "x", "apps": "b"}]}),
    json.dumps({"shards": [{"name": "x", "apps": "a", "split": {"parts": 1, "index": 0}}]}),
    json.dumps({"shards": [{"name": "x", "apps": "a"}], "exempt": [{"unit": "b"}]}),
    json.dumps([{"name": "x", "apps": "a"}]),  # top level is a list
    json.dumps({"shards": [{"name": "x", "apps": 5}]}),  # apps is a number
    json.dumps({"shards": [{"name": "x", "apps": "a"}], "exempt": ["b"]}),  # strings, not objects
    json.dumps({"shards": [{"name": "x", "apps": "a", "split": 2}]}),  # split is a number
])
def test_malformed_plan_exits_2(tmp_path, plan):
    make_tree(tmp_path, ["a/test_a.py"])
    (tmp_path / "ci_shards.json").write_text(plan, encoding="utf-8")
    assert run(tmp_path) == 2


def test_malformed_plan_is_one_line_message_not_traceback(tmp_path, capsys):
    make_tree(tmp_path, ["a/test_a.py"])
    (tmp_path / "ci_shards.json").write_text('["x"]', encoding="utf-8")
    assert run(tmp_path) == 2
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 1 and err[0].startswith("malformed shard plan")


def test_nonexistent_root_exits_2_with_one_line(tmp_path, capsys):
    assert run(tmp_path / "no-such-dir") == 2
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 1 and "not a directory" in err[0]


def test_missing_plan_exits_2(tmp_path):
    make_tree(tmp_path, BASIC)
    assert run(tmp_path) == 2


def test_example_copy_detects_a_dropped_unit(tmp_path):
    """Negative control on the real example: drop one unit from its plan."""
    copy = tmp_path / "example"
    shutil.copytree(EXAMPLE, copy)
    plan = json.loads((copy / "ci_shards.json").read_text(encoding="utf-8"))
    plan["shards"][0]["apps"] = "catalog shipping"  # mysite dropped
    (copy / "ci_shards.json").write_text(json.dumps(plan), encoding="utf-8")
    assert run(copy) == 1
