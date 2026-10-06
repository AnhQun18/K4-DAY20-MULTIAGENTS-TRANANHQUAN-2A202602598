---
name: structured-output-rules
description: Use when producing structured data outputs (JSON, CSV) from messy source data such as logs or sales records, where canonical formatting and schema keys are graded.
---
Normalize and validate structured outputs against the required schema.

1. Canonicalize categorical fields: trim whitespace, apply canonical spelling/casing (e.g. region names like North, South, East, West), and convert service names to lower-case with `-` replaced by `_` (payment-service -> payment_service).
2. Money: emit integer cents, never floats or formatted strings.
3. Timestamps: convert to UTC and format as `YYYY-MM-DDTHH:MM:SSZ`.
4. Deduplicate: one row per distinct entity with a known amount; drop rows with missing required values.
5. CSV: write the exact required header order (e.g. order_id,timestamp_utc,region,amount_cents).
6. JSON: include the required top-level metadata, e.g. `"schema_version": 2` and `"generated_by": "log-triage"`.
7. Sort list fields deterministically (e.g. `errors` by service, then by timestamp_utc, ascending).
8. After writing, re-read the file and assert header order, key names, value formats, and sort order.
