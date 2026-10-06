---
name: python-package-fix
description: Use when fixing bugs in a Python package so its test suite passes and public functions match their docstrings. Covers type hints, regression tests, and changelog conventions.
---
- Read the failing tests and each function's docstring before editing; the docstring is the spec.
- Fix source files only; do not modify existing tests to make them pass.
- Add type annotations to every public function (name not starting with `_`): all parameters and the return value.
- Add `tests/test_regressions.py` with one test function per bug fixed (at least 3); ensure the file passes.
- Record each fix in `CHANGELOG.md` under the heading `## Unreleased` as a bullet `- fix(<function name>): <short description>` (at least 3 bullets).
- After edits, run the full test suite and confirm it passes.
- Verify docstring behaviors not covered by visible tests with a short independent script.
- Stop once tests pass and docstring behaviors are verified; do not re-run identical checks.
