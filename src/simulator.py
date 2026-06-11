"""
simulator.py
============
Intentional Constraints Design (Project Proposal §4)

Provides two simulation utilities:

  simulate_network_delay(seconds)
      Calls time.sleep() to mimic a real network transmission delay.
      Corresponds to proposal: "use time.sleep(1) to make the data
      update slowly, like a real network."

  simulate_data_loss(rows, loss_rate)
      Randomly skips rows at the given rate to mimic packet loss.
      Corresponds to proposal: "intentionally skip some data lines
      to verify the system's stability and error-handling capability."
"""

import time
import random
import logging

log = logging.getLogger(__name__)


def simulate_network_delay(seconds: float = 1.0) -> None:
    """
    Block execution for `seconds` to simulate network latency.

    Args:
        seconds: Delay duration. Proposal specifies 1.0 second.
    """
    log.debug("  [SIM] Network delay: sleeping %.1f second(s)...", seconds)
    time.sleep(seconds)


def simulate_data_loss(rows: list[dict], loss_rate: float = 0.15,
                       seed: int | None = None) -> tuple[list[dict], int]:
    """
    Randomly drop rows to simulate transmission data loss.

    Args:
        rows:      Input rows from Step 1.
        loss_rate: Fraction of rows to drop (default 0.15 = 15%).
        seed:      Optional random seed for reproducibility in tests.

    Returns:
        (transmitted_rows, n_dropped)
    """
    if seed is not None:
        random.seed(seed)

    transmitted = []
    dropped = 0

    for row in rows:
        if random.random() < loss_rate:
            # This row is "lost" in transmission
            log.debug(
                "  [SIM] Row dropped (data loss): item_name=%s",
                row.get("item_name", "?"),
            )
            dropped += 1
        else:
            transmitted.append(row)

    log.info(
        "  [SIM] Data loss simulation: %d/%d rows transmitted (%.0f%% loss rate, %d dropped)",
        len(transmitted), len(rows), loss_rate * 100, dropped,
    )
    return transmitted, dropped


def inject_missing_values(rows: list[dict], corrupt_rate: float = 0.05,
                          seed: int | None = None) -> list[dict]:
    """
    Inject missing/corrupt values into random rows to test Step 4 recovery.
    Used for testing data_cleaner.py independently.

    Args:
        rows:        Input rows.
        corrupt_rate: Fraction of rows to corrupt (default 5%).
        seed:        Optional random seed.

    Returns:
        List of rows, some with stock_count set to "" or item_name cleared.
    """
    if seed is not None:
        random.seed(seed)

    result = []
    for row in rows:
        row = dict(row)
        if random.random() < corrupt_rate:
            field = random.choice(["stock_count", "item_name"])
            original = row.get(field)
            row[field] = ""
            log.debug(
                "  [SIM] Injected missing value: %s = '%s' → ''", field, original,
            )
        result.append(row)

    return result
