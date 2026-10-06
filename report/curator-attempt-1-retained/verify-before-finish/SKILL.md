---
name: verify-before-finish
description: Use when a task requires producing output artifacts (files, JSON, CSV) or fixing code, and you are about to declare completion. Prevents declaring success without the required deliverable existing on disk.
---
Before writing a final summary, confirm every required output artifact exists and is well-formed.

1. List the exact output paths the task requires (e.g. answer.json, clean.csv, errors.json, CHANGELOG.md, tests/test_regressions.py).
2. After producing them, run a single verification command that reads each file back and asserts its presence and shape (parse JSON, read CSV header, count rows).
3. Never end a run with only a plan, a partial edit, or a summary of intent. If a required file is missing, create it before finishing.
4. If you catch yourself repeating the same diagnostic command with identical output, stop: the loop is not making progress. Change approach or write the artifact.
5. Keep a short checklist of required deliverables and tick each one off explicitly in your final message.
