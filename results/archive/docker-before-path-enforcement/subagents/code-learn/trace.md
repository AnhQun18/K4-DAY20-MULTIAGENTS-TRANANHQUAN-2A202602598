### Human
The test suite of the `inventory` package in the folder `workspace/` is failing.

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
['/workspace/CHANGELOG.md', '/workspace/README.md', '/workspace/inventory/', '/workspace/tests/']

### Tool result
['/workspace/inventory/__init__.py', '/workspace/inventory/export.py', '/workspace/inventory/pricing.py', '/workspace/inventory/report.py', '/workspace/tests/test_report.py']

### Tool call: read_file
{"file_path": "workspace/README.md"}

### Tool call: read_file
{"file_path": "workspace/CHANGELOG.md"}

### Tool call: read_file
{"file_path": "workspace/inventory/__init__.py"}

### Tool call: read_file
{"file_path": "workspace/inventory/export.py"}

### Tool call: read_file
{"file_path": "workspace/inventory/pricing.py"}

### Tool call: read_file
{"file_path": "workspace/inventory/report.py"}

### Tool call: read_file
{"file_path": "workspace/tests/test_report.py"}

### Tool result
@@ lines 1-5 of 5 @@
# inventory

Small package. Run the tests from the `workspace/` folder:

    cd workspace && python -m pytest tests -q

### Tool result
@@ lines 1-6 of 6 @@
# Changelog

## Unreleased

## 0.3.1
- initial import

### Tool result
@@ lines 1-1 @@
System reminder: File exists but has empty contents

### Tool result
@@ lines 1-12 of 12 @@
"""Export helpers."""
from .pricing import parse_price


def to_csv_row(item):
    """Format one item as a CSV row: name,price,qty (price with 2 decimals).

    A name that contains a comma or a double quote is wrapped in double quotes,
    and every double quote inside it is doubled (RFC 4180).
    """
    price = parse_price(item["price"])
    return f'{item["name"]},{price:.2f},{item["qty"]}'

### Tool result
@@ lines 1-25 of 25 @@
"""Price utilities for the inventory package."""
from decimal import Decimal


def parse_price(text):
    """Convert a price string to a Decimal.

    Supported formats:
      "$1,299.50" -> Decimal("1299.50")
      "  12 "     -> Decimal("12")
      "1299.5"    -> Decimal("1299.5")
      "(12.00)"   -> Decimal("-12.00")   # accounting style: parentheses mean negative
    """
    cleaned = text.strip().replace("$", "")
    return Decimal(cleaned)


def apply_discount(price, percent):
    """Return `price` after a percentage discount.

    The result is a Decimal rounded to 2 decimal places using the
    commercial rule "round half up" (0.005 -> 0.01).
    """
    discounted = price * (100 - percent) / 100
    return discounted.quantize(Decimal("0.01"))

### Tool result
@@ lines 1-25 of 25 @@
"""Inventory reports."""
from decimal import Decimal

from .pricing import apply_discount, parse_price


def total_value(items):
    """Total value of `items` after per-item discounts.

    Each item is a dict: {"name": str, "price": str, "qty": int, "discount": percent (optional)}.
    """
    total = Decimal("0")
    for item in items:
        price = parse_price(item["price"])
        price = apply_discount(price, item.get("discount", 0))
        total += price * item["qty"]
    return total


def low_stock(items, threshold=5):
    """Names of the items whose quantity is strictly below `threshold`.

    The names are sorted alphabetically, ignoring case.
    """
    return [item["name"] for item in items if item["qty"] <= threshold]

### Tool result
@@ lines 1-32 of 32 @@
from decimal import Decimal

from inventory.export import to_csv_row
from inventory.pricing import apply_discount
from inventory.report import low_stock, total_value


def test_total_value_plain():
    items = [{"name": "pen", "price": "$2.50", "qty": 4}]
    assert total_value(items) == Decimal("10.00")


def test_total_value_thousands_separator():
    items = [{"name": "laptop", "price": "$1,299.50", "qty": 2}]
    assert total_value(items) == Decimal("2599.00")


def test_discount_rounding_half_up():
    assert apply_discount(Decimal("10.05"), 10) == Decimal("9.05")


def test_total_value_with_discount():
    items = [{"name": "desk", "price": "100.00", "qty": 1, "discount": 15}]
    assert total_value(items) == Decimal("85.00")


def test_low_stock_basic():
    assert low_stock([{"name": "pen", "qty": 2}, {"name": "ink", "qty": 9}]) == ["pen"]


def test_csv_row_plain_name():
    assert to_csv_row({"name": "pen", "price": "2.5", "qty": 4}) == "pen,2.50,4"

### Tool call: execute
{"command": "cd workspace && python -m pytest tests -q 2>&1 | tail -40"}

### Tool result
               ^^^^^^^^^^^^^^^^^^

tests/test_report.py:15: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
inventory/report.py:14: in total_value
    price = parse_price(item["price"])
            ^^^^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

text = '$1,299.50'

    def parse_price(text):
        """Convert a price string to a Decimal.
    
        Supported formats:
          "$1,299.50" -> Decimal("1299.50")
          "  12 "     -> Decimal("12")
          "1299.5"    -> Decimal("1299.5")
          "(12.00)"   -> Decimal("-12.00")   # accounting style: parentheses mean negative
        """
        cleaned = text.strip().replace("$", "")
>       return Decimal(cleaned)
               ^^^^^^^^^^^^^^^^
E       decimal.InvalidOperation: [<class 'decimal.ConversionSyntax'>]

inventory/pricing.py:15: InvalidOperation
________________________ test_discount_rounding_half_up ________________________

    def test_discount_rounding_half_up():
>       assert apply_discount(Decimal("10.05"), 10) == Decimal("9.05")
E       AssertionError: assert Decimal('9.04') == Decimal('9.05')
E        +  where Decimal('9.04') = apply_discount(Decimal('10.05'), 10)
E        +    where Decimal('10.05') = Decimal('10.05')
E        +  and   Decimal('9.05') = Decimal('9.05')

tests/test_report.py:19: AssertionError
=========================== short test summary info ============================
FAILED tests/

### Tool call: execute
{"command": "cd workspace && ls -a && ls -a tests && cat pytest.ini setup.cfg pyproject.toml tox.ini 2>/dev/null; ls -a .."}

### Tool result
.
..
.pytest_cache
CHANGELOG.md
README.md
inventory
tests
.
..
__pycache__
test_report.py
.
..
workspace

[Command succeeded with exit code 0]

### Tool call: execute
{"command": "cd workspace && python -c \"\nfrom decimal import Decimal\nprint(Decimal('10.05')*(100-10)/100)\nprint(Decimal('10.05')*Decimal(90)/Decimal(100))\n\""}

### Tool result
9.045
9.045

[Command succeeded with exit code 0]

### Tool call: execute
{"command": "cd workspace && python -c \"\nfrom decimal import Decimal, ROUND_HALF_UP\nprint(Decimal('9.045').quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))\nprint(Decimal('9.045').quantize(Decimal('0.01')))\n\""}

### Tool result
9.05
9.04

[Command succeeded with exit code 0]

### Assistant
Now let me delegate the implementation with full context.

### Tool call: task
{"description": "Fix the `inventory` package in the sandbox folder `workspace/` so its whole test suite passes and every function matches its docstring.\n\nPATHS: all paths are relative to the sandbox root and never start with '/'. The package is at `workspace/inventory/` (files: `__init__.py` (empty), `pricing.py`, `report.py`, `export.py`) and the tests are at `workspace/tests/test_report.py`. Run tests with: `cd workspace && python -m pytest tests -q`.\n\nRULES:\n- Do NOT modify anything under `workspace/tests/`.\n- Only change source files under `workspace/inventory/`.\n- The docstrings are the specification (the visible tests do not cover everything), so implement exactly what each docstring says, including edge cases.\n- Follow the Acme Python team conventions: module and function docstrings in the existing style, type hints are NOT used in this codebase (keep the existing style: no type annotations), keep functions small and readable, use `decimal` for money, no mutable default arguments, no bare `except`, keep imports at the top of the module, and keep the public API names unchanged.\n- Do not add new dependencies; standard library only.\n- Do not add new files unless truly necessary; prefer editing the existing modules.\n\nKNOWN BUGS TO FIX (verified by me):\n1. `workspace/inventory/pricing.py::parse_price` — docstring says it supports `\"$1,299.50\"` -> `Decimal(\"1299.50\")`, `\"  12 \"` -> `Decimal(\"12\")`, `\"1299.5\"` -> `Decimal(\"1299.5\")`, and accounting st

### Tool result
All tests pass and every documented edge case behaves as specified. Here is the report.

## Report

### Files changed (all under `workspace/inventory/`)

**1. `workspace/inventory/pricing.py`**
- Import changed to `from decimal import ROUND_HALF_UP, Decimal` (imports kept at top).
- `parse_price` — now strips whitespace, removes `$` and `,`, and negates parenthesized (accounting) values.
- `apply_discount` — now quantizes with `rounding=ROUND_HALF_UP`.

Final content of the changed functions:
```python
def parse_price(text):
    """Convert a price string to a Decimal.

    Supported formats:
      "$1,299.50" -> Decimal("1299.50")
      "  12 "     -> Decimal("12")
      "1299.5"    -> Decimal("1299.5")
      "(12.00)"   -> Decimal("-12.00")   # accounting style: parentheses mean negative
    """
    cleaned = text.strip().replace("$", "").replace(",", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        return -Decimal(cleaned[1:-1])
    return Decimal(cleaned)


def apply_discount(price, percent):
    """Return `price` after a percentage discount.

    The result is a Decimal rounded to 2 decimal places using the
    commercial rule "round half up" (0.005 -> 0.01).
    """
    discounted = price * (100 - percent) / 100
    return discounted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

**2. `workspace/inventory/report.py`**
- `low_stock` — now uses strict `<` and sorts case-insensitively. `total_value` was re-read against its docstring and already 

### Assistant
Let me independently verify the changes and check edge cases myself.

### Tool call: read_file
{"file_path": "workspace/inventory/pricing.py"}

### Tool call: read_file
{"file_path": "workspace/inventory/report.py"}

### Tool call: read_file
{"file_path": "workspace/inventory/export.py"}

### Tool result
@@ lines 1-27 of 27 @@
"""Price utilities for the inventory package."""
from decimal import ROUND_HALF_UP, Decimal


def parse_price(text):
    """Convert a price string to a Decimal.

    Supported formats:
      "$1,299.50" -> Decimal("1299.50")
      "  12 "     -> Decimal("12")
      "1299.5"    -> Decimal("1299.5")
      "(12.00)"   -> Decimal("-12.00")   # accounting style: parentheses mean negative
    """
    cleaned = text.strip().replace("$", "").replace(",", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        return -Decimal(cleaned[1:-1])
    return Decimal(cleaned)


def apply_discount(price, percent):
    """Return `price` after a percentage discount.

    The result is a Decimal rounded to 2 decimal places using the
    commercial rule "round half up" (0.005 -> 0.01).
    """
    discounted = price * (100 - percent) / 100
    return discounted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

### Tool result
@@ lines 1-26 of 26 @@
"""Inventory reports."""
from decimal import Decimal

from .pricing import apply_discount, parse_price


def total_value(items):
    """Total value of `items` after per-item discounts.

    Each item is a dict: {"name": str, "price": str, "qty": int, "discount": percent (optional)}.
    """
    total = Decimal("0")
    for item in items:
        price = parse_price(item["price"])
        price = apply_discount(price, item.get("discount", 0))
        total += price * item["qty"]
    return total


def low_stock(items, threshold=5):
    """Names of the items whose quantity is strictly below `threshold`.

    The names are sorted alphabetically, ignoring case.
    """
    names = [item["name"] for item in items if item["qty"] < threshold]
    return sorted(names, key=str.lower)

### Tool result
@@ lines 1-15 of 15 @@
"""Export helpers."""
from .pricing import parse_price


def to_csv_row(item):
    """Format one item as a CSV row: name,price,qty (price with 2 decimals).

    A name that contains a comma or a double quote is wrapped in double quotes,
    and every double quote inside it is doubled (RFC 4180).
    """
    price = parse_price(item["price"])
    name = item["name"]
    if "," in name or '"' in name:
        name = '"' + name.replace('"', '""') + '"'
    return f'{name},{price:.2f},{item["qty"]}'

### Tool call: execute
{"command": "cd workspace && python -m pytest tests -q 2>&1 | tail -5 && python - <<'EOF'\nfrom decimal import Decimal\nfrom inventory.pricing import parse_price, apply_discount\nfrom inventory.report import low_stock, total_value\nfrom inventory.export import to_csv_row\n\n# parse_price documented formats\nassert parse_price(\"$1,299.50\") == Decimal(\"1299.50\")\nassert parse_price(\"  12 \") == Decimal(\"12\")\nassert parse_price(\"1299.5\") == Decimal(\"1299.5\")\nassert parse_price(\"(12.00)\") == Decimal(\"-12.00\")\nassert parse_price(\"($1,299.50)\") == Decimal(\"-1299.50\")\n\n# half-up rounding\nassert apply_discount(Decimal(\"10.05\"), 10) == Decimal(\"9.05\")\nassert apply_discount(Decimal(\"0.005\"), 0) == Decimal(\"0.01\")\nassert apply_discount(Decimal(\"0.015\"), 0) == Decimal(\"0.02\")\nassert apply_discount(Decimal(\"100.00\"), 15) == Decimal(\"85.00\")\nassert apply_discount(Decimal(\"10.00\"), 0) == Decimal(\"10.00\")\n\n# low_stock: strictly below, case-insensitive sort\nitems = [{\"name\": \"Zebra\", \"qty\": 1}, {\"name\": \"apple\", \"qty\": 4}, {\"name\": \"Mango\", \"qty\": 5}]\nassert low_stock(items) == [\"apple\", \"Zebra\"], low_stock(items)\nassert low_stock(items, threshold=1) == []\nassert low_stock(items, threshold=5) == [\"apple\", \"Zebra\"]\n\n# total_value\nassert total_value([]) == Decimal(\"0\")\nassert total_value([{\"name\": \"pen\", \"price\": \"$2.50\", \"qty\": 4}]) == Decimal(\"10.00\")\nassert total_value([{\"name\": \"d\", \"pri

### Tool result
......                                                                   [100%]
6 passed in 0.31s
all edge cases OK

[Command succeeded with exit code 0]

### Tool call: execute
{"command": "cd workspace && git status --short 2>/dev/null; git diff --stat 2>/dev/null; echo \"---\"; python -m pytest tests -q 2>&1 | tail -3"}

### Tool result
---
......                                                                   [100%]
6 passed in 6.09s

[Command succeeded with exit code 0]

### Assistant
All 6 tests pass and the documented edge cases behave as specified. No test files were touched.

## Summary

Fixed three source modules in `workspace/inventory/` (tests untouched, no new files or dependencies):

**`workspace/inventory/pricing.py`**
- `parse_price`: it only stripped whitespace and removed `$`, so `"$1,299.50"` raised `decimal.InvalidOperation` and accounting-style negatives were ignored. It now also removes thousands separators and negates values wrapped in parentheses, matching all four documented formats (`"$1,299.50"`, `"  12 "`, `"1299.5"`, `"(12.00)"`).
- `apply_discount`: `quantize(Decimal("0.01"))` used the context default `ROUND_HALF_EVEN`, giving `9.04` for `10.05` at 10%. It now passes `rounding=ROUND_HALF_UP` (imported from `decimal`), so the documented commercial half-up rule holds (`0.005 -> 0.01`).

**`workspace/inventory/report.py`**
- `low_stock`: used `<=` and returned items in input order. It now selects quantities strictly below the threshold and sorts the names alphabetically ignoring case (`sorted(..., key=str.lower)`), as the docstring requires.
- `total_value` was re-checked against its docstring and already correct (optional `discount` defaulting to 0), so it was left unchanged.

**`workspace/inventory/export.py`**
- `to_csv_row`: never quoted names. It now applies the RFC 4180 rule from the docstring — a name containing a comma or a double quote is wrapped in double quotes with inner quotes doubled — while still formatting the price wi