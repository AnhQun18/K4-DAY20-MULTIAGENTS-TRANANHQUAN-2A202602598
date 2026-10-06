---
name: repo-conventions
description: Use when editing a Python package or fixing bugs in a repo that has tests, a changelog, or documented conventions. Ensures reusable repo-wide rules are satisfied, not just the visible tests.
---
Apply organization-wide conventions whenever you modify package code.

1. Type hints: every public function (name not starting with `_`) must annotate all parameters and the return value.
2. Regression tests: add `tests/test_regressions.py` with one test function per bug fixed (at least 3); the file must pass.
3. Changelog: record each fix in `CHANGELOG.md` under the heading `## Unreleased` as a bullet `- fix(<function name>): <short description>` (at least 3 bullets).
4. Run the full test suite after edits and confirm it passes before finishing.
5. Do not modify existing tests to make them pass; fix the source instead.
