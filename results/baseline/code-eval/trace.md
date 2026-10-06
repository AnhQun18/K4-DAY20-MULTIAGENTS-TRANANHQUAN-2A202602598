### Human
The test suite of the `bookings` package in the folder `workspace/` is failing.

Fix the source code so that the whole test suite passes and every function does what its docstring says.
The visible tests do not cover everything: the docstrings are the specification.
Do not modify the existing files in `tests/`.
Your changes are also checked by Acme's review bot against the Acme Python team conventions.

When you are done, reply with a short summary of what you changed and why.


### Assistant
I'll start by exploring the workspace structure.

### Tool call: ls
{"path": "workspace"}

### Tool call: glob
{"pattern": "workspace/**/*.py"}

### Tool result
['/workspace/CHANGELOG.md', '/workspace/README.md', '/workspace/bookings/', '/workspace/tests/']

### Tool result
['/workspace/bookings/__init__.py', '/workspace/bookings/billing.py', '/workspace/bookings/calendar_export.py', '/workspace/bookings/schedule.py', '/workspace/bookings/timeutil.py', '/workspace/tests/test_bookings.py']

### Tool call: read_file
{"file_path": "workspace/README.md"}

### Tool call: read_file
{"file_path": "workspace/CHANGELOG.md"}

### Tool call: read_file
{"file_path": "workspace/bookings/__init__.py"}

### Tool result
@@ lines 1-5 of 5 @@
# bookings

Small package. Run the tests from the `workspace/` folder:

    cd workspace && python -m pytest tests -q

### Tool result
@@ lines 1-6 of 6 @@
# Changelog

## Unreleased

## 1.4.2
- initial import

### Tool result
@@ lines 1-1 of 1 @@
__version__ = "1.4.2"

### Tool call: read_file
{"file_path": "workspace/bookings/timeutil.py"}

### Tool call: read_file
{"file_path": "workspace/bookings/schedule.py"}

### Tool call: read_file
{"file_path": "workspace/bookings/billing.py"}

### Tool call: read_file
{"file_path": "workspace/bookings/calendar_export.py"}

### Tool call: read_file
{"file_path": "workspace/tests/test_bookings.py"}

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
2 failed, 1 passed in 0.20s

[Command succeeded with exit code 0]

### Assistant
Now let me fix each module according to the docstrings.

### Tool call: write_file
{"file_path": "workspace/bookings/timeutil.py", "content": "\"\"\"Time helpers for the bookings package.\"\"\"\nimport re\n\n_HOURS_MINUTES_RE = re.compile(r\"(\\d+)h(?:(\\d+)m)?\")\n_MINUTES_RE = re.compile(r\"(\\d+)m\")\n_CLOCK_RE = re.compile(r\"(\\d+):(\\d+)\")\n_BARE_MINUTES_RE = re.compile(r\"(\\d+)\")\n\n\ndef parse_duration(text):\n    \"\"\"Convert a duration string to whole minutes (int).\n\n    Supported formats:\n      \"1h30m\" -> 90\n      \"2h\"    -> 120\n      \"45m\"   -> 45\n      \"1:30\"  -> 90\n      \"45\"    -> 45    # a bare number means minutes\n    Surrounding whitespace is ignored.\n    \"\"\"\n    stripped = text.strip()\n\n    m = _HOURS_MINUTES_RE.fullmatch(stripped)\n    if m:\n        hours = int(m.group(1))\n        minutes = int(m.group(2)) if m.group(2) else 0\n        return hours * 60 + minutes\n\n    m = _MINUTES_RE.fullmatch(stripped)\n    if m:\n        return int(m.group(1))\n\n    m = _CLOCK_RE.fullmatch(stripped)\n    if m:\n        return int(m.group(1)) * 60 + int(m.group(2))\n\n    m = _BARE_MINUTES_RE.fullmatch(stripped)\n    if m:\n        return int(m.group(1))\n\n    raise ValueError(f\"bad duration: {text!r}\")\n"}

### Tool call: write_file
{"file_path": "workspace/bookings/schedule.py", "content": "\"\"\"Schedule helpers.\"\"\"\nfrom .timeutil import parse_duration\n\n\ndef total_minutes(durations):\n    \"\"\"Total minutes of a list of duration strings.\"\"\"\n    return sum(parse_duration(d) for d in durations)\n\n\ndef add_slot(slot, slots=None):\n    \"\"\"Return a NEW list containing the given slots plus `slot`.\n\n    Separate calls must not share state: calling add_slot(\"a\") and then\n    add_slot(\"b\") returns [\"a\"] and then [\"b\"].\n    \"\"\"\n    if slots is None:\n        slots = []\n    return [*slots, slot]\n"}

### Tool call: write_file
{"file_path": "workspace/bookings/billing.py", "content": "\"\"\"Billing rules.\"\"\"\nimport math\n\n\ndef billable_blocks(minutes, block=15):\n    \"\"\"Number of billable blocks for a booking.\n\n    A partial block is billed as a full block (always round UP):\n    16 minutes with 15-minute blocks -> 2 blocks.\n    `minutes` must be >= 0; a negative value raises ValueError.\n    \"\"\"\n    if minutes < 0:\n        raise ValueError(f\"minutes must be >= 0, got {minutes!r}\")\n    return math.ceil(minutes / block)\n"}

### Tool result
Updated file /workspace/bookings/timeutil.py

### Tool result
Updated file /workspace/bookings/schedule.py

### Tool result
Updated file /workspace/bookings/billing.py

### Tool call: execute
{"command": "cd workspace && python -m pytest tests -q 2>&1 | tail -10"}

### Tool result
...                                                                      [100%]
3 passed in 0.14s

[Command succeeded with exit code 0]

### Assistant
Now let me verify the docstring spec beyond the visible tests.

### Tool call: execute
{"command": "cd workspace && python -c \"\nfrom bookings.timeutil import parse_duration\nfrom bookings.schedule import add_slot, total_minutes\nfrom bookings.billing import billable_blocks\nfrom bookings.calendar_export import slot_end\n\nfor t, exp in [('1h30m',90),('2h',120),('45m',45),('1:30',90),('45',45),(' 1h30m ',90),('0h0m',0),('0',0)]:\n    got = parse_duration(t)\n    assert got == exp, (t, got, exp)\nprint('parse_duration ok')\n\nfor bad in ['', 'abc', '1h30', 'h30m', '1:2:3', '-5', '1.5h']:\n    try:\n        parse_duration(bad)\n    except ValueError:\n        pass\n    else:\n        raise AssertionError('should raise: %r' % bad)\nprint('parse_duration errors ok')\n\nassert add_slot('a') == ['a']\nassert add_slot('b') == ['b']\nassert add_slot('b', ['a']) == ['a','b']\nbase = ['a']\nassert add_slot('b', base) == ['a','b'] and base == ['a']\nprint('add_slot ok')\n\nassert total_minutes([]) == 0\nassert total_minutes(['1h30m','2h']) == 210\nprint('total_minutes ok')\n\nassert billable_blocks(0) == 0\nassert billable_blocks(15) == 1\nassert billable_blocks(16) == 2\nassert billable_blocks(20) == 2\nassert billable_blocks(45) == 3\nassert billable_blocks(30, block=30) == 1\nassert billable_blocks(31, block=30) == 2\nfor bad in [-1, -0.5]:\n    try:\n        billable_blocks(bad)\n    except ValueError:\n        pass\n    else:\n        raise AssertionError('should raise: %r' % bad)\nprint('billable_blocks ok')\n\nassert slot_end(600, '1h30m') == 690\nassert slot_end(

### Tool result
parse_duration ok
parse_duration errors ok
add_slot ok
total_minutes ok
billable_blocks ok
slot_end ok

[Command succeeded with exit code 0]

### Assistant
All behaviors match the docstrings. Let me double-check the final state of the files.

### Tool call: read_file
{"file_path": "workspace/bookings/timeutil.py"}

### Tool call: read_file
{"file_path": "workspace/bookings/schedule.py"}

### Tool call: read_file
{"file_path": "workspace/bookings/billing.py"}

### Tool result
@@ lines 1-41 of 41 @@
"""Time helpers for the bookings package."""
import re

_HOURS_MINUTES_RE = re.compile(r"(\d+)h(?:(\d+)m)?")
_MINUTES_RE = re.compile(r"(\d+)m")
_CLOCK_RE = re.compile(r"(\d+):(\d+)")
_BARE_MINUTES_RE = re.compile(r"(\d+)")


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
    stripped = text.strip()

    m = _HOURS_MINUTES_RE.fullmatch(stripped)
    if m:
        hours = int(m.group(1))
        minutes = int(m.group(2)) if m.group(2) else 0
        return hours * 60 + minutes

    m = _MINUTES_RE.fullmatch(stripped)
    if m:
        return int(m.group(1))

    m = _CLOCK_RE.fullmatch(stripped)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))

    m = _BARE_MINUTES_RE.fullmatch(stripped)
    if m:
        return int(m.group(1))

    raise ValueError(f"bad duration: {text!r}")

### Tool result
@@ lines 1-18 of 18 @@
"""Schedule helpers."""
from .timeutil import parse_duration


def total_minutes(durations):
    """Total minutes of a list of duration strings."""
    return sum(parse_duration(d) for d in durations)


def add_slot(slot, slots=None):
    """Return a NEW list containing the given slots plus `slot`.

    Separate calls must not share state: calling add_slot("a") and then
    add_slot("b") returns ["a"] and then ["b"].
    """
    if slots is None:
        slots = []
    return [*slots, slot]

### Tool result
@@ lines 1-14 of 14 @@
"""Billing rules."""
import math


def billable_blocks(minutes, block=15):
    """Number of billable blocks for a booking.

    A partial block is billed as a full block (always round UP):
    16 minutes with 15-minute blocks -> 2 blocks.
    `minutes` must be >= 0; a negative value raises ValueError.
    """
    if minutes < 0:
        raise ValueError(f"minutes must be >= 0, got {minutes!r}")
    return math.ceil(minutes / block)

### Assistant
All tests pass and every function now matches its docstring.

## Summary

Fixed three source files in `workspace/bookings/` (no test files touched):

**`bookings/timeutil.py`** — `parse_duration` only handled the `"1h30m"` form and raised on everything else. Rewrote it to support all documented formats: `"1h30m"`, `"2h"` (hours-only), `"45m"`, `"1:30"` (clock form), and bare `"45"` (minutes), with surrounding whitespace stripped. Patterns are precompiled at module level and matched with `fullmatch`, and unsupported input still raises `ValueError`.

**`bookings/schedule.py`** — `add_slot` used a mutable default argument (`slots=[]`), so calls shared state and it mutated the caller's list. Changed the default to `None` and made the function return a new list (`[*slots, slot]`), so separate calls no longer leak state and the input list is never modified.

**`bookings/billing.py`** — `billable_blocks` used `round()`, which rounds to nearest (and banker's-rounds), contradicting the "always round UP" rule. Switched to `math.ceil(minutes / block)` and added the documented `ValueError` for negative `minutes`.

`bookings/calendar_export.py` was already correct and left unchanged. Verified with `python -m pytest tests -q` (3 passed) plus extra checks covering the docstring cases not exercised by the visible tests (hours-only, clock form, whitespace, zero, custom block sizes, negative-input errors, and non-mutation of the input list).