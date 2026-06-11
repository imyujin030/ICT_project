"""
pipeline.py
===========
ICT Module 4 – Intermediate Project
Student: Lim Yujin (2024270678)

Implements the 6-step data pipeline described in the project proposal:
  Step 1: Data Generation  – read inventory CSV
  Step 2: Transmission     – simulate network delay (time.sleep)
  Step 3: Collection       – store data into SQLite database
  Step 4: AI / Recovery    – filter & clean bad/missing data
  Step 5: Decision         – apply IF-THEN threshold logic
  Step 6: Dashboard        – export results for the web dashboard

Usage:
    python pipeline.py                      # run full pipeline once
    python pipeline.py --interval 5         # run every 5 seconds
    python pipeline.py --csv data/inventory.csv --db data/inventory.db
"""

import argparse
import time
import logging

from data_cleaner import load_and_clean_csv
from decision     import apply_decision_logic
from simulator    import simulate_data_loss, simulate_network_delay
from db           import init_db, upsert_inventory, fetch_all_inventory, export_to_csv

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# PIPELINE STEPS
# ──────────────────────────────────────────────

def step1_generate(csv_path: str) -> list[dict]:
    """Step 1 – Data Generation: read raw CSV file."""
    log.info("STEP 1 ▸ Data Generation — reading %s", csv_path)
    raw_rows = load_and_clean_csv(csv_path, apply_cleaning=False)
    log.info("  → %d rows loaded", len(raw_rows))
    return raw_rows


def step2_transmit(rows: list[dict], loss_rate: float = 0.15, delay: float = 1.0) -> list[dict]:
    """Step 2 – Transmission: simulate network delay + intentional data loss."""
    log.info("STEP 2 ▸ Transmission — delay=%.1fs, loss_rate=%.0f%%", delay, loss_rate * 100)
    simulate_network_delay(delay)
    transmitted, dropped = simulate_data_loss(rows, loss_rate)
    log.info("  → %d transmitted, %d dropped (%.0f%% loss)", len(transmitted), dropped, loss_rate * 100)
    return transmitted


def step3_collect(rows: list[dict], db_path: str) -> None:
    """Step 3 – Collection: upsert rows into SQLite database."""
    log.info("STEP 3 ▸ Collection — storing to %s", db_path)
    conn = init_db(db_path)
    upsert_inventory(conn, rows)
    conn.close()
    log.info("  → %d rows upserted", len(rows))


def step4_recover(csv_path: str) -> list[dict]:
    """Step 4 – AI / Recovery: clean missing or corrupt values."""
    log.info("STEP 4 ▸ AI / Recovery — cleaning data")
    cleaned = load_and_clean_csv(csv_path, apply_cleaning=True)
    recovered = sum(1 for r in cleaned if r.get("_recovered"))
    log.info("  → %d missing values recovered (set to 0 or 'No Data')", recovered)
    return cleaned


def step5_decide(rows: list[dict], threshold: int = 5) -> list[dict]:
    """Step 5 – Decision: IF stock < threshold THEN flag 'Restock Needed'."""
    log.info("STEP 5 ▸ Decision — threshold=%d", threshold)
    result = apply_decision_logic(rows, threshold)
    flagged = sum(1 for r in result if r.get("status") == "Restock Needed")
    log.info("  → %d item(s) flagged as 'Restock Needed'", flagged)
    return result


def step6_dashboard(rows: list[dict], db_path: str, output_csv: str) -> None:
    """Step 6 – Dashboard: export final dataset for web dashboard consumption."""
    log.info("STEP 6 ▸ Dashboard — exporting results")
    conn = init_db(db_path)
    upsert_inventory(conn, rows)
    export_to_csv(conn, output_csv)
    conn.close()
    log.info("  → Dashboard-ready CSV written to %s", output_csv)


# ──────────────────────────────────────────────
# MAIN RUNNER
# ──────────────────────────────────────────────

def run_pipeline(csv_path: str, db_path: str, output_csv: str,
                 threshold: int = 5, loss_rate: float = 0.15,
                 network_delay: float = 1.0) -> list[dict]:
    """Execute all 6 pipeline steps and return final processed rows."""
    log.info("=" * 55)
    log.info("  CLOSET.KR Smart Inventory Pipeline – Starting")
    log.info("=" * 55)

    raw      = step1_generate(csv_path)
    received = step2_transmit(raw, loss_rate=loss_rate, delay=network_delay)
    step3_collect(received, db_path)
    cleaned  = step4_recover(csv_path)       # re-reads full file for recovery
    decided  = step5_decide(cleaned, threshold=threshold)
    step6_dashboard(decided, db_path, output_csv)

    log.info("=" * 55)
    log.info("  Pipeline complete. %d items processed.", len(decided))
    log.info("=" * 55)
    return decided


def main():
    parser = argparse.ArgumentParser(description="CLOSET.KR 6-Step Inventory Pipeline")
    parser.add_argument("--csv",       default="data/inventory.csv",        help="Input CSV path")
    parser.add_argument("--db",        default="data/inventory.db",         help="SQLite DB path")
    parser.add_argument("--output",    default="data/dashboard_output.csv", help="Output CSV for dashboard")
    parser.add_argument("--threshold", type=int,   default=5,    help="Restock threshold")
    parser.add_argument("--loss",      type=float, default=0.15, help="Simulated data loss rate (0–1)")
    parser.add_argument("--delay",     type=float, default=1.0,  help="Simulated network delay (seconds)")
    parser.add_argument("--interval",  type=float, default=0,    help="Repeat every N seconds (0 = run once)")
    args = parser.parse_args()

    if args.interval > 0:
        log.info("Continuous mode: running every %.0f seconds. Press Ctrl+C to stop.", args.interval)
        tick = 0
        try:
            while True:
                tick += 1
                log.info("─── Tick #%d ───", tick)
                run_pipeline(
                    csv_path=args.csv, db_path=args.db, output_csv=args.output,
                    threshold=args.threshold, loss_rate=args.loss, network_delay=args.delay,
                )
                time.sleep(args.interval)
        except KeyboardInterrupt:
            log.info("Pipeline stopped by user.")
    else:
        run_pipeline(
            csv_path=args.csv, db_path=args.db, output_csv=args.output,
            threshold=args.threshold, loss_rate=args.loss, network_delay=args.delay,
        )


if __name__ == "__main__":
    main()
