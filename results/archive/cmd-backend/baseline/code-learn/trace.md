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

tests\test_report.py:15: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
inventory\report.py:14: in total_value
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

inventory\pricing.py:15: InvalidOperation
_______________________ test_discount_rounding_half_up ________________________

    def test_discount_rounding_half_up():
>       assert apply_discount(Decimal("10.05"), 10) == Decimal("9.05")
E       AssertionError: assert Decimal('9.04') == Decimal('9.05')
E        +  where Decimal('9.04') = apply_discount(Decimal('10.05'), 10)
E        +    where Decimal('10.05') = Decimal('10.05')
E        +  and   Decimal('9.05') = Decimal('9.05')

tests\test_report.py:19: AssertionError
=========================== short test summary info ===========================
FAILED tests/test

### Tool call: execute
{"command": "cd workspace && python -m pytest tests -q 2>&1 | head -40"}

### Tool result
.FF...                                                                   [100%]
================================== FAILURES ===================================
____________________ test_total_value_thousands_separator _____________________

    def test_total_value_thousands_separator():
        items = [{"name": "laptop", "price": "$1,299.50", "qty": 2}]
>       assert total_value(items) == Decimal("2599.00")
               ^^^^^^^^^^^^^^^^^^

tests\test_report.py:15: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
inventory\report.py:14: in total_value
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

inventory\pricing.py:15: InvalidOperation
_______________________ test_discount_rounding_half_up ________________________

    def test_discount_rounding_half_up():
>       assert apply_discount(Decimal("10.

### Assistant
Now let me fix the three bugs. First, `parse_price`:

### Tool call: edit_file
{"file_path": "workspace/inventory/pricing.py", "old_string": "\"\"\"Price utilities for the inventory package.\"\"\"\nfrom decimal import Decimal\n\n\ndef parse_price(text):\n    \"\"\"Convert a price string to a Decimal.\n\n    Supported formats:\n      \"$1,299.50\" -> Decimal(\"1299.50\")\n      \"  12 \"     -> Decimal(\"12\")\n      \"1299.5\"    -> Decimal(\"1299.5\")\n      \"(12.00)\"   -> Decimal(\"-12.00\")   # accounting style: parentheses mean negative\n    \"\"\"\n    cleaned = text.strip().replace(\"$\", \"\")\n    return Decimal(cleaned)\n\n\ndef apply_discount(price, percent):\n    \"\"\"Return `price` after a percentage discount.\n\n    The result is a Decimal rounded to 2 decimal places using the\n    commercial rule \"round half up\" (0.005 -> 0.01).\n    \"\"\"\n    discounted = price * (100 - percent) / 100\n    return discounted.quantize(Decimal(\"0.01\"))", "new_string": "\"\"\"Price utilities for the inventory package.\"\"\"\nfrom decimal import ROUND_HALF_UP, Decimal\n\n\ndef parse_price(text):\n    \"\"\"Convert a price string to a Decimal.\n\n    Supported formats:\n      \"$1,299.50\" -> Decimal(\"1299.50\")\n      \"  12 \"     -> Decimal(\"12\")\n      \"1299.5\"    -> Decimal(\"1299.5\")\n      \"(12.00)\"   -> Decimal(\"-12.00\")   # accounting style: parentheses mean negative\n    \"\"\"\n    cleaned = text.strip().replace(\"$\", \"\").replace(\",\", \"\")\n    negative = cleaned.startswith(\"(\") and cleaned.endswith(\")\")\n    if negative:

### Tool result
Successfully replaced 1 instance(s) of the string in '/workspace/inventory/pricing.py'

### Assistant
Now `low_stock` (strictly below, sorted case-insensitively) and `to_csv_row` (RFC 4180 quoting):

### Tool call: edit_file
{"file_path": "workspace/inventory/report.py", "new_string": "def low_stock(items, threshold=5):\n    \"\"\"Names of the items whose quantity is strictly below `threshold`.\n\n    The names are sorted alphabetically, ignoring case.\n    \"\"\"\n    names = [item[\"name\"] for item in items if item[\"qty\"] < threshold]\n    return sorted(names, key=str.lower)", "old_string": "def low_stock(items, threshold=5):\n    \"\"\"Names of the items whose quantity is strictly below `threshold`.\n\n    The names are sorted alphabetically, ignoring case.\n    \"\"\"\n    return [item[\"name\"] for item in items if item[\"qty\"] <= threshold]"}

### Tool call: edit_file
{"file_path": "workspace/inventory/export.py", "new_string": "    price = parse_price(item[\"price\"])\n    name = item[\"name\"]\n    if \",\" in name or '\"' in name:\n        name = '\"' + name.replace('\"', '\"\"') + '\"'\n    return f'{name},{price:.2f},{item[\"qty\"]}'", "old_string": "    price = parse_price(item[\"price\"])\n    return f'{item[\"name\"]},{price:.2f},{item[\"qty\"]}'"}

### Tool result
Successfully replaced 1 instance(s) of the string in '/workspace/inventory/report.py'

### Tool result
Successfully replaced 1 instance(s) of the string in '/workspace/inventory/export.py'

### Tool call: execute
{"command": "cd workspace && python -m pytest tests -q 2>&1 | tail -5"}

### Tool result
......                                                                   [100%]
6 passed in 0.04s

[Command succeeded with exit code 0]

### Assistant
All tests pass. Let me verify the docstring-specified behaviors that the visible tests don't cover:

### Tool call: execute
{"command": "cd workspace && python -c \"\nfrom decimal import Decimal\nfrom inventory.pricing import parse_price, apply_discount\nfrom inventory.report import low_stock, total_value\nfrom inventory.export import to_csv_row\n\nassert parse_price('\\$1,299.50') == Decimal('1299.50')\nassert parse_price('  12 ') == Decimal('12')\nassert parse_price('1299.5') == Decimal('1299.5')\nassert parse_price('(12.00)') == Decimal('-12.00')\nassert parse_price('(\\$1,000.00)') == Decimal('-1000.00')\nassert apply_discount(Decimal('10.05'), 10) == Decimal('9.05')\nassert apply_discount(Decimal('0.005'), 0) == Decimal('0.01')\nassert apply_discount(Decimal('100'), 0) == Decimal('100.00')\n# strictly below threshold, case-insensitive sort\nassert low_stock([{'name':'Zed','qty':1},{'name':'apple','qty':4},{'name':'Banana','qty':5}]) == ['apple','Zed']\nassert low_stock([{'name':'a','qty':5}], 5) == []\nassert low_stock([{'name':'a','qty':4}], 5) == ['a']\n# RFC 4180 quoting\nassert to_csv_row({'name':'pen','price':'2.5','qty':4}) == 'pen,2.50,4'\nassert to_csv_row({'name':'a,b','price':'2.5','qty':4}) == '\\\"a,b\\\",2.50,4'\nassert to_csv_row({'name':'a\\\"b','price':'2.5','qty':4}) == '\\\"a\\\"\\\"b\\\",2.50,4'\nassert to_csv_row({'name':'a,\\\"b\\\"','price':'2.5','qty':4}) == '\\\"a,\\\"\\\"b\\\"\\\"\\\",2.50,4'\nassert total_value([{'name':'x','price':'\\$1,299.50','qty':2}]) == Decimal('2599.00')\nprint('all docstring checks OK')\n\""}

### Tool result
<no output>
[Command succeeded with exit code 0]

### Tool call: execute
{"command": "cd workspace && python -c \"\nfrom decimal import Decimal\nfrom inventory.pricing import parse_price, apply_discount\nfrom inventory.report import low_stock, total_value\nfrom inventory.export import to_csv_row\nassert parse_price('(12.00)') == Decimal('-12.00')\nassert parse_price('(\\$1,000.00)') == Decimal('-1000.00')\nassert apply_discount(Decimal('0.005'), 0) == Decimal('0.01')\nassert low_stock([{'name':'Zed','qty':1},{'name':'apple','qty':4},{'name':'Banana','qty':5}]) == ['apple','Zed']\nassert low_stock([{'name':'a','qty':5}], 5) == []\nassert to_csv_row({'name':'a,b','price':'2.5','qty':4}) == '\\\"a,b\\\",2.50,4'\nassert to_csv_row({'name':'a\\\"b','price':'2.5','qty':4}) == '\\\"a\\\"\\\"b\\\",2.50,4'\nprint('OK')\n\""}

### Tool result
<no output>
[Command succeeded with exit code 0]

### Assistant
The shell seems to swallow output. Let me write a temp script file instead:

### Tool call: write_file
{"file_path": "workspace/_check.py", "content": "from decimal import Decimal\n\nfrom inventory.export import to_csv_row\nfrom inventory.pricing import apply_discount, parse_price\nfrom inventory.report import low_stock, total_value\n\nassert parse_price(\"$1,299.50\") == Decimal(\"1299.50\")\nassert parse_price(\"  12 \") == Decimal(\"12\")\nassert parse_price(\"1299.5\") == Decimal(\"1299.5\")\nassert parse_price(\"(12.00)\") == Decimal(\"-12.00\")\nassert parse_price(\"($1,000.00)\") == Decimal(\"-1000.00\")\nassert apply_discount(Decimal(\"10.05\"), 10) == Decimal(\"9.05\")\nassert apply_discount(Decimal(\"0.005\"), 0) == Decimal(\"0.01\")\nassert apply_discount(Decimal(\"100\"), 0) == Decimal(\"100.00\")\nassert low_stock([{\"name\": \"Zed\", \"qty\": 1}, {\"name\": \"apple\", \"qty\": 4}, {\"name\": \"Banana\", \"qty\": 5}]) == [\"apple\", \"Zed\"]\nassert low_stock([{\"name\": \"a\", \"qty\": 5}], 5) == []\nassert low_stock([{\"name\": \"a\", \"qty\": 4}], 5) == [\"a\"]\nassert to_csv_row({\"name\": \"pen\", \"price\": \"2.5\", \"qty\": 4}) == \"pen,2.50,4\"\nassert to_csv_row({\"name\": \"a,b\", \"price\": \"2.5\", \"qty\": 4}) == '\"a,b\",2.50,4'\nassert to_csv_row({\"name\": 'a\"b', \"price\": \"2.5\", \"qty\": 4}) == '\"a\"\"b\",2.50,4'\nassert to_csv_row({\"name\": 'a,\"b\"', \"price\": \"2.5\", \"qty\": 4}) == '\"a,\"\"b\"\"\",2.50,4'\nassert total_value([{\"name\": \"x\", \"price\": \"$1,299.50\", \"qty\": 2}]) == Decimal(\"2599.00\")\nprint(\"all docstring check

### Tool result
Updated file /workspace/_check.py

### Tool call: execute
{"command": "cd workspace && python _check.py"}

### Tool result
all docstring checks OK

[Command succeeded with exit code 0]

### Assistant
All docstring-specified behaviors verified. Cleaning up the temp file:

### Tool call: delete
{"file_path": "workspace/_check.py"}

### Tool result
Deleted /workspace/_check.py

### Tool call: execute
{"command": "cd workspace && python -m pytest tests -q 2>&1 | tail -3"}

### Tool result
......                                                                   [100%]
6 passed in 0.03s

[Command succeeded with exit code 0]

### Assistant
All 6 tests pass. Summary of changes:

**`inventory/pricing.py`**
- `parse_price`: now strips thousands separators (`,`) and handles accounting-style parentheses, returning a negative `Decimal` for `"(12.00)"`. Previously `"$1,299.50"` raised `InvalidOperation` and parentheses were ignored.
- `apply_discount`: quantizes with `rounding=ROUND_HALF_UP` (imported from `decimal`) so the documented commercial "round half up" rule holds (`10.05` at 10% → `9.05`, not `9.04`).

**`inventory/report.py`**
- `low_stock`: uses a strict `<` comparison (docstring says "strictly below") and sorts the names alphabetically ignoring case via `key=str.lower`. Previously it used `<=` and returned unsorted names.

**`inventory/export.py`**
- `to_csv_row`: implements RFC 4180 quoting — a name containing a comma or double quote is wrapped in double quotes with inner quotes doubled. Previously names were emitted raw.

No files in `tests/` were modified.