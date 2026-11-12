# Writing a brief an agent cannot misread

An agent does what the brief says, fills gaps with plausible guesses, and
reports success in the same confident tone either way. The brief is your
main control. These points come from what went wrong on the original
project, unless marked as suggested.

## State outcomes a user can observe

On the original project, two items in one task were reported as delivered
and could not be reached by a user: a reporting endpoint with no screen,
and a page with no link to it. In another round, eight items reported as
shipped were visibly broken on the test site. Write acceptance as
*"As <role>, from <navigation entry>, I see / can do <result>"*, and
the reviewer reaches each item by clicking, not by typing a URL.

## Name the files it owns, and the ones it does not

Parallel agents only stay out of each other's way if ownership is
explicit. List owned files and directories, list neighbours that are
off limits and who owns them, and say whether migrations are allowed.

## Make it prove its starting point

Start with a "Step 0": fetch, check the merge base, grep for something
the base must contain, record baselines. On the original project, one
task's Step 0 found that the previous task's branch had never reached
`origin`.

## Expect the brief to be wrong sometimes, and ask to be told

Several briefs on the original project stated premises that were false:
that a component had no state machine (it had one of 643 lines), that a
value was swallowed (it never was), that a list page existed (it did
not). Ask the agent to check each premise against the code and report
"where the brief was wrong" instead of building on it. The project's
standing rule: where docs and code disagree, the code is the truth, and
the drift is reported, not silently followed.

## Say what is NOT in scope

A "Deliberately NOT in this task" section stops scope creep and stops a
reviewer from flagging a planned omission as a defect.

## Require the full suite, not only the touched tests

For about four weeks the original project only ran tests for touched
modules. When the full suite was finally run, 51 tests (43 failures,
8 errors) had gone red in modules no task had touched. The rule became:
the full suite runs at the close of every task, and a red is a task item,
not a note.

## Bound the retries

At most two fix iterations per failing item, then report it as open with
evidence. No unattended agent-versus-agent loops.

## Ask for numbers, measured

"Tests pass" is a claim. "Ran 1289 tests in 97 modules, OK" is evidence.
Ask for the command and its output for every number in the report.

## Suggested, not from the original project

- Keep a brief to one screen. If it is longer, it is probably two tasks.
- Give the agent the verification checklist up front; it will check its
  own work against the same list the reviewer uses.
