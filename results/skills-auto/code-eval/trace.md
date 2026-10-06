### Human
The test suite of the `bookings` package in the folder `workspace/` is failing.

Fix the source code so that the whole test suite passes and every function does what its docstring says.
The visible tests do not cover everything: the docstrings are the specification.
Do not modify the existing files in `tests/`.
Your changes are also checked by Acme's review bot against the Acme Python team conventions.

When you are done, reply with a short summary of what you changed and why.


### Assistant
I'll start by reading the relevant skill files.

### Tool call: read_file
{"file_path": "/skills/python-package-fix/SKILL.md", "limit": 1000}

### Tool call: ls
{"path": "/workspace"}

### Tool result
@@ lines 1-12 of 12 @@
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

### Tool result
['/workspace/CHANGELOG.md', '/workspace/README.md', '/workspace/bookings/', '/workspace/tests/']

### Tool call: ls
{"path": "/workspace/bookings"}

### Tool call: ls
{"path": "/workspace/tests"}

### Tool call: read_file
{"file_path": "/workspace/CHANGELOG.md"}

### Tool call: read_file
{"file_path": "/workspace/README.md"}

### Tool result
['/workspace/bookings/__init__.py', '/workspace/bookings/__pycache__/', '/workspace/bookings/billing.py', '/workspace/bookings/calendar_export.py', '/workspace/bookings/schedule.py', '/workspace/bookings/timeutil.py']

### Tool result
['/workspace/tests/__pycache__/', '/workspace/tests/test_bookings.py']

### Tool result
@@ lines 1-6 of 6 @@
# Changelog

## Unreleased

## 1.4.2
- initial import

### Tool result
@@ lines 1-5 of 5 @@
# bookings

Small package. Run the tests from the `workspace/` folder:

    cd workspace && python -m pytest tests -q

### Tool call: read_file
{"file_path": "/workspace/bookings/__init__.py"}

### Tool call: read_file
{"file_path": "/workspace/bookings/billing.py"}

### Tool call: read_file
{"file_path": "/workspace/bookings/calendar_export.py"}

### Tool call: read_file
{"file_path": "/workspace/bookings/schedule.py"}

### Tool call: read_file
{"file_path": "/workspace/bookings/timeutil.py"}

### Tool call: read_file
{"file_path": "/workspace/tests/test_bookings.py"}

### Tool result
@@ lines 1-1 of 1 @@
__version__ = "1.4.2"

### Tool result
@@ lines 1-11 of 11 @@
"""Billing rules."""


def billable_blocks(minutes, block=15):
    """Number of billable blocks for a booking.

    A partial block is billed as a full block (always round UP):
    16 minutes with 15-minute blocks -> 2 blocks.
    `minutes` must be >= 0; a negative value raises ValueError.
    """
    return round(minutes / block)

### Tool result
@@ lines 1-7 of 7 @@
"""Calendar export."""
from .timeutil import parse_duration


def slot_end(start_minute, duration_text):
    """Minute of the day at which a slot ends."""
    return start_minute + parse_duration(duration_text)

### Tool result
@@ lines 1-17 of 17 @@
"""Schedule helpers."""
from .timeutil import parse_duration


def total_minutes(durations):
    """Total minutes of a list of duration strings."""
    return sum(parse_duration(d) for d in durations)


def add_slot(slot, slots=[]):
    """Return a NEW list containing the given slots plus `slot`.

    Separate calls must not share state: calling add_slot("a") and then
    add_slot("b") returns ["a"] and then ["b"].
    """
    slots.append(slot)
    return slots

### Tool result
@@ lines 1-19 of 19 @@
"""Time helpers for the bookings package."""
import re


def parse_duration(text):
    """Convert a duration string to whole minutes (int).

    Supported formats:
      "1h30m" -> 90
      "2h"    -> 120
      "45m"   -> 45
      "1:30"  -> 90
      "45"    -> 45    # a bare number means minutes
    Surrounding whitespace is ignored.
    """
    m = re.fullmatch(r"(\d+)h(\d+)m", text.strip())
    if not m:
        raise ValueError(f"bad duration: {text!r}")
    return int(m.group(1)) * 60 + int(m.group(2))

### Tool result
@@ lines 1-15 of 15 @@
from bookings.billing import billable_blocks
from bookings.schedule import add_slot, total_minutes


def test_total_minutes_mixed_formats():
    assert total_minutes(["1h30m", "2h"]) == 210


def test_billable_blocks_rounds_up():
    assert billable_blocks(20) == 2
    assert billable_blocks(45) == 3


def test_add_slot_single_call():
    assert add_slot("a") == ["a"]

### Tool call: execute
{"command": "cd workspace && python -m pytest tests -q 2>&1 | tail -30"}

### Tool result

    def parse_duration(text):
        """Convert a duration string to whole minutes (int).
    
        Supported formats:
          "1h30m" -> 90
          "2h"    -> 120
          "45m"   -> 45
          "1:30"  -> 90
          "45"    -> 45    # a bare number means minutes
        Surrounding whitespace is ignored.
        """
        m = re.fullmatch(r"(\d+)h(\d+)m", text.strip())
        if not m:
>           raise ValueError(f"bad duration: {text!r}")
E           ValueError: bad duration: '2h'

bookings/timeutil.py:18: ValueError
________________________ test_billable_blocks_rounds_up ________________________

    def test_billable_blocks_rounds_up():
>       assert billable_blocks(20) == 2
E       assert 1 == 2
E        +  where 1 = billable_blocks(20)

tests/test_bookings.py:10: AssertionError
=========================== short test summary info ============================
FAILED tests/test_bookings.py::test_total_minutes_mixed_formats - ValueError:...
FAILED tests/test_bookings.py::test_billable_blocks_rounds_up - assert 1 == 2
2 failed, 1 passed in 0.28s

[Command succeeded with exit code 0]

### Assistant
Now let me fix the source files.

### Tool call: write_file
{"file_path": "/workspace/bookings/timeutil.py", "content": "\"\"\"Time helpers for the bookings package.\"\"\"\nimport re\n\n_HM_RE = re.compile(r\"(\\d+)h(?:(\\d+)m)?\")\n_M_RE = re.compile(r\"(\\d+)m\")\n_COLON_RE = re.compile(r\"(\\d+):(\\d+)\")\n_BARE_RE = re.compile(r\"(\\d+)\")\n\n\ndef parse_duration(text: str) -> int:\n    \"\"\"Convert a duration string to whole minutes (int).\n\n    Supported formats:\n      \"1h30m\" -> 90\n      \"2h\"    -> 120\n      \"45m\"   -> 45\n      \"1:30\"  -> 90\n      \"45\"    -> 45    # a bare number means minutes\n    Surrounding whitespace is ignored.\n    \"\"\"\n    stripped = text.strip()\n\n    m = _HM_RE.fullmatch(stripped)\n    if m:\n        return int(m.group(1)) * 60 + int(m.group(2) or 0)\n\n    m = _M_RE.fullmatch(stripped)\n    if m:\n        return int(m.group(1))\n\n    m = _COLON_RE.fullmatch(stripped)\n    if m:\n        return int(m.group(1)) * 60 + int(m.group(2))\n\n    m = _BARE_RE.fullmatch(stripped)\n    if m:\n        return int(m.group(1))\n\n    raise ValueError(f\"bad duration: {text!r}\")\n"}

### Tool call: write_file
{"file_path": "/workspace/bookings/billing.py", "content": "\"\"\"Billing rules.\"\"\"\nimport math\n\n\ndef billable_blocks(minutes: int, block: int = 15) -> int:\n    \"\"\"Number of billable blocks for a booking.\n\n    A partial block is billed as a full block (always round UP):\n    16 minutes with 15-minute blocks -> 2 blocks.\n    `minutes` must be >= 0; a negative value raises ValueError.\n    \"\"\"\n    if minutes < 0:\n        raise ValueError(f\"minutes must be >= 0, got {minutes!r}\")\n    return math.ceil(minutes / block)\n"}

### Tool call: write_file
{"file_path": "/workspace/bookings/schedule.py", "content": "\"\"\"Schedule helpers.\"\"\"\nfrom typing import Iterable, List\n\nfrom .timeutil import parse_duration\n\n\ndef total_minutes(durations: Iterable[str]) -> int:\n    \"\"\"Total minutes of a list of duration strings.\"\"\"\n    return sum(parse_duration(d) for d in durations)\n\n\ndef add_slot(slot: str, slots: Iterable[str] = ()) -> List[str]:\n    \"\"\"Return a NEW list containing the given slots plus `slot`.\n\n    Separate calls must not share state: calling add_slot(\"a\") and then\n    add_slot(\"b\") returns [\"a\"] and then [\"b\"].\n    \"\"\"\n    return [*slots, slot]\n"}

### Tool call: write_file
{"file_path": "/workspace/bookings/calendar_export.py", "content": "\"\"\"Calendar export.\"\"\"\nfrom .timeutil import parse_duration\n\n\ndef slot_end(start_minute: int, duration_text: str) -> int:\n    \"\"\"Minute of the day at which a slot ends.\"\"\"\n    return start_minute + parse_duration(duration_text)\n"}

### Tool result
Updated file /workspace/bookings/timeutil.py

### Tool result
Updated file /workspace/bookings/billing.py

### Tool result
Updated file /workspace/bookings/schedule.py

### Tool result
Updated file /workspace/bookings/calendar_export.py

### Tool call: execute
{"command": "cd workspace && python -m pytest tests -q 2>&1 | tail -10"}

### Tool result
...                                                                      [100%]
3 passed in 0.13s

[Command succeeded with exit code 0]

### Assistant
Now let me verify docstring behaviors not covered by visible tests, and add regression tests.

### Tool call: execute
{"command": "cd workspace && python -c \"\nfrom bookings.timeutil import parse_duration\nfrom bookings.billing import billable_blocks\nfrom bookings.schedule import add_slot, total_minutes\nfrom bookings.calendar_export import slot_end\n\nassert parse_duration('1h30m') == 90\nassert parse_duration('2h') == 120\nassert parse_duration('45m') == 45\nassert parse_duration('1:30') == 90\nassert parse_duration('45') == 45\nassert parse_duration('  1h30m  ') == 90\nassert parse_duration(' 2h ') == 120\ntry:\n    parse_duration('nope'); raise SystemExit('should raise')\nexcept ValueError: pass\n\nassert billable_blocks(16) == 2\nassert billable_blocks(15) == 1\nassert billable_blocks(0) == 0\nassert billable_blocks(20) == 2\nassert billable_blocks(45) == 3\nassert billable_blocks(30, block=30) == 1\ntry:\n    billable_blocks(-1); raise SystemExit('should raise')\nexcept ValueError: pass\n\nassert add_slot('a') == ['a']\nassert add_slot('b') == ['b']\nassert add_slot('b', ['a']) == ['a', 'b']\nbase = ['x']\nassert add_slot('y', base) == ['x', 'y'] and base == ['x']\nassert total_minutes(['1h30m', '2h']) == 210\nassert total_minutes([]) == 0\nassert slot_end(60, '1h30m') == 150\nprint('all docstring behaviors OK')\n\""}

### Tool result
all docstring behaviors OK

[Command succeeded with exit code 0]

### Tool call: write_file
{"content": "import pytest\n\nfrom bookings.billing import billable_blocks\nfrom bookings.calendar_export import slot_end\nfrom bookings.schedule import add_slot\nfrom bookings.timeutil import parse_duration\n\n\ndef test_parse_duration_supports_all_documented_formats():\n    assert parse_duration(\"1h30m\") == 90\n    assert parse_duration(\"2h\") == 120\n    assert parse_duration(\"45m\") == 45\n    assert parse_duration(\"1:30\") == 90\n    assert parse_duration(\"45\") == 45\n    assert parse_duration(\"  1h30m  \") == 90\n\n\ndef test_parse_duration_rejects_unknown_format():\n    with pytest.raises(ValueError):\n        parse_duration(\"nope\")\n\n\ndef test_billable_blocks_rounds_up_and_rejects_negative():\n    assert billable_blocks(16) == 2\n    assert billable_blocks(15) == 1\n    assert billable_blocks(0) == 0\n    with pytest.raises(ValueError):\n        billable_blocks(-1)\n\n\ndef test_add_slot_does_not_share_state_between_calls():\n    assert add_slot(\"a\") == [\"a\"]\n    assert add_slot(\"b\") == [\"b\"]\n\n\ndef test_add_slot_does_not_mutate_input_list():\n    base = [\"x\"]\n    assert add_slot(\"y\", base) == [\"x\", \"y\"]\n    assert base == [\"x\"]\n\n\ndef test_slot_end_uses_parsed_duration():\n    assert slot_end(60, \"1h30m\") == 150\n", "file_path": "/workspace/tests/test_regressions.py"}

### Tool call: edit_file
{"file_path": "/workspace/CHANGELOG.md", "old_string": "## Unreleased\n", "new_string": "## Unreleased\n- fix(parse_duration): support \"2h\", \"45m\", \"1:30\" and bare-minute formats, not just \"1h30m\"\n- fix(billable_blocks): round up partial blocks with math.ceil and raise ValueError for negative minutes\n- fix(add_slot): return a new list instead of mutating a shared default argument\n"}

### Tool result
Updated file /workspace/tests/test_regressions.py

### Tool result
Successfully replaced 1 instance(s) of the string in '/workspace/CHANGELOG.md'

### Tool call: execute
{"command": "cd workspace && python -m pytest tests -q 2>&1 | tail -10"}

### Tool result
.........                                                                [100%]
9 passed in 0.15s

[Command succeeded with exit code 0]

### Assistant
All 9 tests pass. Summary of changes:

**Source fixes (`workspace/bookings/`)**
- `timeutil.py` — `parse_duration` only matched `"1h30m"`. Rewrote it to handle every documented format: `"1h30m"`, `"2h"`, `"45m"`, `"1:30"`, and bare minutes `"45"`, with surrounding whitespace ignored and `ValueError` for anything else. Added type hints.
- `billing.py` — `billable_blocks` used `round()`, which rounds to nearest (20 min → 1 block). Switched to `math.ceil` so partial blocks always round up, and added the documented `ValueError` for negative `minutes`. Added type hints.
- `schedule.py` — `add_slot` used a mutable default `slots=[]` and mutated it, so calls shared state. It now returns a new list (`[*slots, slot]`) without mutating the input. Added type hints to both public functions.
- `calendar_export.py` — added type hints to `slot_end` (behavior was already correct).

**Tests / docs**
- Added `workspace/tests/test_regressions.py` with one test per fixed bug plus coverage of docstring behaviors the visible tests missed (all duration formats, negative-minutes error, no shared state, no input mutation, `slot_end`).
- Recorded the three fixes in `workspace/CHANGELOG.md` under `## Unreleased`.

Existing files in `tests/` were left untouched.