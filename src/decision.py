"""
decision.py
===========
Step 5 – Decision Logic

Applies the IF-THEN rule from the project proposal:
  "If (Stock < threshold), then show a red alert on the dashboard
   and label it as 'Restock Needed'."

Status tiers:
  stock == 0            → "Out of Stock"   (critical)
  0 < stock < threshold → "Restock Needed" (danger)
  threshold <= stock < threshold*2 → "Warning"  (caution)
  stock >= threshold*2  → "Normal"         (ok)
"""

from __future__ import annotations
import logging

log = logging.getLogger(__name__)

# Status constants
STATUS_OUT_OF_STOCK   = "Out of Stock"
STATUS_RESTOCK_NEEDED = "Restock Needed"
STATUS_WARNING        = "Warning"
STATUS_NORMAL         = "Normal"
STATUS_NO_DATA        = "No Data"


def classify_stock(stock_count: int, threshold: int = 5) -> str:
    """
    Return a status string for a given stock count.

    Args:
        stock_count: Current available stock (int).
        threshold:   Minimum acceptable stock level.

    Returns:
        One of the STATUS_* constants.
    """
    if stock_count is None:
        return STATUS_NO_DATA
    if stock_count == 0:
        return STATUS_OUT_OF_STOCK
    if stock_count < threshold:
        return STATUS_RESTOCK_NEEDED
    if stock_count < threshold * 2:
        return STATUS_WARNING
    return STATUS_NORMAL


def apply_decision_logic(rows: list[dict], threshold: int = 5) -> list[dict]:
    """
    Iterate over cleaned inventory rows and attach a 'status' field
    using classify_stock().

    Args:
        rows:      List of dicts from data_cleaner.load_and_clean_csv().
        threshold: Restock threshold (configurable; default 5).

    Returns:
        Same list with 'status' and 'alert' fields added.
    """
    result = []
    for row in rows:
        count  = row.get("stock_count", 0)
        status = classify_stock(count, threshold)
        alert  = status in (STATUS_OUT_OF_STOCK, STATUS_RESTOCK_NEEDED)

        row = dict(row)
        row["status"]    = status
        row["alert"]     = alert
        row["threshold"] = threshold

        if alert:
            log.info(
                "  [ALERT] %-40s stock=%s → %s",
                row.get("item_name", "?"), count, status,
            )

        result.append(row)

    return result


def get_alert_items(rows: list[dict]) -> list[dict]:
    """Return only rows where alert is True."""
    return [r for r in rows if r.get("alert")]


def decision_summary(rows: list[dict]) -> dict:
    """Return a count breakdown by status."""
    summary: dict[str, int] = {}
    for row in rows:
        s = row.get("status", "Unknown")
        summary[s] = summary.get(s, 0) + 1
    summary["total"] = len(rows)
    return summary
