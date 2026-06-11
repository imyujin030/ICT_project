"""
db.py
=====
Step 3 – Collection (SQLite)

Manages the SQLite database that stores inventory records.
Provides:
  init_db(path)             – create DB and tables if not exist
  upsert_inventory(conn, rows) – insert or update rows
  fetch_all_inventory(conn) – read all inventory rows
  export_to_csv(conn, path) – write DB contents to CSV for the dashboard
"""

import csv
import sqlite3
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# SCHEMA
# ──────────────────────────────────────────────

DDL_INVENTORY = """
CREATE TABLE IF NOT EXISTS inventory (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name    TEXT    NOT NULL UNIQUE,
    category     TEXT    DEFAULT 'Uncategorized',
    stock_count  INTEGER DEFAULT 0,
    max_stock    INTEGER DEFAULT 50,
    status       TEXT    DEFAULT 'Normal',
    alert        INTEGER DEFAULT 0,   -- 0=False, 1=True
    threshold    INTEGER DEFAULT 5,
    updated_at   TEXT    DEFAULT (datetime('now','localtime'))
);
"""

DDL_PIPELINE_LOG = """
CREATE TABLE IF NOT EXISTS pipeline_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at     TEXT DEFAULT (datetime('now','localtime')),
    total_rows INTEGER,
    recovered  INTEGER,
    dropped    INTEGER,
    flagged    INTEGER
);
"""


# ──────────────────────────────────────────────
# CONNECTION
# ──────────────────────────────────────────────

def init_db(db_path: str) -> sqlite3.Connection:
    """
    Open (or create) the SQLite database at db_path.
    Creates tables if they do not exist.
    Returns an open connection.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")  # safer concurrent writes

    conn.executescript(DDL_INVENTORY + DDL_PIPELINE_LOG)
    conn.commit()

    log.debug("  [DB] Connected to %s", db_path)
    return conn


# ──────────────────────────────────────────────
# WRITE
# ──────────────────────────────────────────────

def upsert_inventory(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """
    INSERT OR REPLACE each row into the inventory table.
    Returns number of rows affected.
    """
    sql = """
    INSERT INTO inventory (item_name, category, stock_count, max_stock,
                           status, alert, threshold, updated_at)
    VALUES (:item_name, :category, :stock_count, :max_stock,
            :status, :alert, :threshold, datetime('now','localtime'))
    ON CONFLICT(item_name) DO UPDATE SET
        category    = excluded.category,
        stock_count = excluded.stock_count,
        max_stock   = excluded.max_stock,
        status      = excluded.status,
        alert       = excluded.alert,
        threshold   = excluded.threshold,
        updated_at  = excluded.updated_at;
    """
    affected = 0
    for row in rows:
        params = {
            "item_name":   row.get("item_name", "No Data"),
            "category":    row.get("category", "Uncategorized"),
            "stock_count": int(row.get("stock_count", 0)),
            "max_stock":   int(row.get("max_stock", 50)),
            "status":      row.get("status", "Normal"),
            "alert":       1 if row.get("alert") else 0,
            "threshold":   int(row.get("threshold", 5)),
        }
        conn.execute(sql, params)
        affected += 1

    conn.commit()
    log.debug("  [DB] Upserted %d rows", affected)
    return affected


def log_pipeline_run(conn: sqlite3.Connection, total: int,
                     recovered: int, dropped: int, flagged: int) -> None:
    """Record one pipeline run in pipeline_log table."""
    conn.execute(
        "INSERT INTO pipeline_log (total_rows, recovered, dropped, flagged) "
        "VALUES (?, ?, ?, ?)",
        (total, recovered, dropped, flagged),
    )
    conn.commit()


# ──────────────────────────────────────────────
# READ
# ──────────────────────────────────────────────

def fetch_all_inventory(conn: sqlite3.Connection) -> list[dict]:
    """Return all inventory rows as a list of dicts."""
    cur = conn.execute(
        "SELECT * FROM inventory ORDER BY category, item_name"
    )
    return [dict(row) for row in cur.fetchall()]


def fetch_alert_items(conn: sqlite3.Connection) -> list[dict]:
    """Return only rows where alert = 1."""
    cur = conn.execute(
        "SELECT * FROM inventory WHERE alert = 1 ORDER BY stock_count ASC"
    )
    return [dict(row) for row in cur.fetchall()]


# ──────────────────────────────────────────────
# EXPORT
# ──────────────────────────────────────────────

def export_to_csv(conn: sqlite3.Connection, output_path: str) -> None:
    """
    Write all inventory rows to a CSV file for the web dashboard.
    The dashboard reads this file to display real-time stock status.
    """
    rows = fetch_all_inventory(conn)
    if not rows:
        log.warning("  [DB] No rows to export.")
        return

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "item_name", "category", "stock_count", "max_stock",
        "status", "alert", "threshold", "updated_at",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    log.info("  [DB] Exported %d rows to %s", len(rows), output_path)
