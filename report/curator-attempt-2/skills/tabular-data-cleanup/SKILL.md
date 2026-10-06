---
name: tabular-data-cleanup
description: Use when cleaning and aggregating tabular data (CSV) into a required output artifact, including deduplication, canonicalization, and money handling.
---
- Inspect the raw file first: header, row count, and distinct values per column.
- Count missing entities (e.g. rows with unknown/blank amounts) before filtering known amounts for revenue or cleaned export.
- Deduplicate by the entity key; keep one row per distinct entity.
- Canonicalize categorical fields to the required spelling (e.g. `North, South, East, West`), trimming whitespace and fixing case.
- Normalize timestamps to UTC in `YYYY-MM-DDTHH:MM:SSZ` format.
- Store money as integer cents.
- Write the cleaned output to `workspace/clean.csv` with header order `order_id,timestamp_utc,region,amount_cents`.
- Write the required answer artifact (e.g. `answer.json`) with the required schema keys and version.
- If a diagnostic command produces identical output twice, stop repeating it; change approach or produce the deliverable.
- Verify the deliverable exists and re-read it before finishing.
