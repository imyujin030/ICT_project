"""
data_cleaner.py
===============
Step 4 – AI / Recovery

Reads the inventory CSV and applies data cleaning rules:
  - Missing item_name   → replaced with "No Data"
  - Missing / negative stock_count → replaced with 0
  - Non-numeric stock_count → replaced with 0
  - Marks each recovered row with _recovered=True for audit logging

This mirrors the project proposal's AI/Recovery step:
  "If a value is missing, the system will show '0' or 'No Data'
   to prevent system errors."
"""

import csv
import logging
from pathlib import Path

log = logging.getLogger(__name__)

REQUIRED_FIELDS = {"item_name", "stock_count"}


def _clean_row(row: dict) -> dict:
    """Apply recovery rules to a single CSV row. Returns cleaned row."""
    cleaned = dict(row)
    recovered = False

    # ── item_name ──────────────────────────────────────
    name = cleaned.get("item_name", "").strip()
    if not name:
        cleaned["item_name"] = "No Data"
        recovered = True
        log.debug("  [RECOVER] item_name missing → 'No Data'")

    # ── stock_count ────────────────────────────────────
    raw_count = cleaned.get("stock_count", "").strip()
    try:
        count = int(float(raw_count))
        if count < 0:
            log.debug("  [RECOVER] stock_count negative (%s) → 0", raw_count)
            count = 0
            recovered = True
    except (ValueError, TypeError):
        log.debug("  [RECOVER] stock_count invalid ('%s') → 0", raw_count)
        count = 0
        recovered = True
    cleaned["stock_count"] = count

    # ── category (optional field) ──────────────────────
    if "category" in cleaned and not cleaned["category"].strip():
        cleaned["category"] = "Uncategorized"
        recovered = True

    # ── max_stock (optional field) ─────────────────────
    if "max_stock" in cleaned:
        try:
            ms = int(float(cleaned["max_stock"]))
            cleaned["max_stock"] = max(1, ms)
        except (ValueError, TypeError):
            cleaned["max_stock"] = 50
            recovered = True

    cleaned["_recovered"] = recovered
    return cleaned


def load_and_clean_csv(csv_path: str, apply_cleaning: bool = True) -> list[dict]:
    """
    Load CSV from csv_path.
    If apply_cleaning is True, run recovery logic on each row.
    Returns list of row dicts.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            # Strip whitespace from all values
            row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

            if apply_cleaning:
                row = _clean_row(row)
            else:
                row["_recovered"] = False

            rows.append(row)

    return rows


def summarize_cleaning(rows: list[dict]) -> dict:
    """Return a summary dict of how many rows were recovered."""
    total = len(rows)
    recovered = sum(1 for r in rows if r.get("_recovered"))
    return {
        "total_rows": total,
        "recovered_rows": recovered,
        "clean_rows": total - recovered,
        "recovery_rate_pct": round(recovered / total * 100, 1) if total else 0,
    }
