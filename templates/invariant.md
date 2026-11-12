# Invariants: rules bound to tests

An invariant is a rule that must never break, written down together with
where it is enforced and the test that fails if it does break. A rule
without a test is a wish. A test without a written rule gets "fixed" by
the next agent that finds it inconvenient.

On the original project the security floor was a table of 12 hard
invariants. Each row had four columns: ID, the rule in one sentence,
"enforced at" (file and function), and "test that locks it". Any change
that contradicted one was treated as a P0 regression.

## Template (one row per invariant)

| ID | Invariant | Enforced at | Test that locks it |
|---|---|---|---|
| INV-{{n}} | **{{One sentence, stated as what must never happen or must always happen.}}** | `{{path/to/module.py}}` `{{function}}` | `{{path/to/test_file.py}}::{{TestClass}}::{{test_name}}` |

Rules for the table:
- One sentence per invariant. If it needs "and", it is two invariants.
- "Enforced at" names a real place in code. If enforcement lives in two
  places (view and service), list both and keep both.
- "Test that locks it" names a test that **fails** when the rule is broken.
  Prove it once: break the rule locally, watch the test go red, restore.
- When the rule changes, change the row, the code and the test in one commit.
- Agents may add rows. Agents may not delete or weaken a row or its test
  without written sign-off from the owner.

## Worked example (generic)

A multi-tenant notes service. Users belong to one workspace.

| ID | Invariant | Enforced at | Test that locks it |
|---|---|---|---|
| INV-1 | **A user never reads a note from another workspace, by list, by ID or by search.** | `notes/scoping.py` `notes_visible_to(user)`; every note view builds its queryset from it | `notes/tests/test_inv1_workspace_isolation.py` |

The test covers every door, not only the obvious one, and asserts the
refusal as well as the success:

```python
# notes/tests/test_inv1_workspace_isolation.py
from django.test import TestCase
from rest_framework.test import APIClient

from notes.models import Note, Workspace
from users.models import User


class WorkspaceIsolationTests(TestCase):
    """INV-1: a user never reads a note from another workspace."""

    def setUp(self):
        self.ws_a = Workspace.objects.create(name="A")
        self.ws_b = Workspace.objects.create(name="B")
        self.alice = User.objects.create_user("alice", workspace=self.ws_a)
        self.note_b = Note.objects.create(workspace=self.ws_b, title="b-secret")
        self.client = APIClient()
        self.client.force_authenticate(self.alice)

    def test_list_excludes_other_workspace(self):
        ids = [n["id"] for n in self.client.get("/api/notes/").json()["results"]]
        self.assertNotIn(self.note_b.id, ids)

    def test_detail_by_id_is_404_not_403(self):
        # 404, so the response does not confirm the note exists.
        r = self.client.get(f"/api/notes/{self.note_b.id}/")
        self.assertEqual(r.status_code, 404)

    def test_search_does_not_leak_titles(self):
        r = self.client.get("/api/notes/", {"q": "b-secret"})
        self.assertEqual(r.json()["count"], 0)

    def test_id_smuggled_in_a_write_is_refused(self):
        # Attaching another workspace's note by ID is a classic side door.
        r = self.client.post("/api/links/", {"note": self.note_b.id})
        self.assertIn(r.status_code, (400, 404))
```

## Checking the table in review

- Every row's test path exists and the test runs in some CI shard
  (the shard plan check guarantees the second half).
- `git diff` on the branch shows no edit to a locking test unless the
  brief allowed it.
- New endpoints that read scoped data have a row, or cite an existing one.
