# Smart Inventory & Order Management System

> **ICT — Intermediate Project**
> Student: Lim Yujin | Student ID: 2024270678

---

## 📹 Demo Video

**[▶ Watch the Presentation Video](https://drive.google.com/file/d/1yOO5CDoaD8G_1QvKDDwiPeVSjF-9rHki/view)**

> ⚠️ Replace the URL above with your actual YouTube video link before submission.

---

## 1. Project Overview

**The project** is a smart inventory and order management system designed for a small fashion e-commerce warehouse. It solves a critical real-world problem: when stock runs out, orders are automatically cancelled — causing permanent revenue loss.

This system prevents that by:
- Tracking stock in **real time** per SKU
- Routing stock-short orders to **Delayed** status instead of cancelling them
- Sending **automated customer notifications** when delivery is delayed
- Resuming delayed orders automatically when stock is replenished

The project is delivered as a **standalone HTML dashboard** that runs in any browser with no installation, along with a **Python data pipeline** that mirrors the 6-step architecture from the original proposal.

---

## 2. System Architecture — 6-Step Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. Data     │───▶│ 2. Transmit  │───▶│ 3. Collect   │
│  Generation  │     │ time.sleep(1)│     │   SQLite DB  │
│  (CSV file)  │     │ 15% data loss│     │              │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
┌──────────────┐     ┌──────────────┐     ┌──────▼───────┐
│  6. Dashboard│◀───│ 5. Decision  │◀───│ 4. AI/       │
│  HTML / Web  │     │ IF stock <   │     │ Recovery     │
│  Dashboard   │     │ threshold →  │     │ missing → 0  │
│              │     │ "Restock"    │     │ or 'No Data' │
└──────────────┘     └──────────────┘     └──────────────┘
```

| Step | Module | Description |
|------|--------|-------------|
| 1 | `data_cleaner.py` | Read CSV — item names & stock counts |
| 2 | `simulator.py` | `time.sleep(1)` network delay + 15% row drop |
| 3 | `db.py` | Store/update records in SQLite |
| 4 | `data_cleaner.py` | Remove bad data; missing values → `0` / `"No Data"` |
| 5 | `decision.py` | `IF stock < threshold → "Restock Needed"` |
| 6 | `dashboard/index.html` | Real-time web dashboard |

### Intentional Constraints (Proposal §4)

| Constraint | Implementation |
|-----------|----------------|
| Network delay | `time.sleep(1.0)` in `simulator.simulate_network_delay()` |
| Data loss (15%) | Random row skip in `simulator.simulate_data_loss()` |
| Missing value recovery | `"" → 0` or `"No Data"` in `data_cleaner._clean_row()` |

---

## 3. Decision Logic

```python
# decision.py — apply_decision_logic()

IF   stock == 0            → "Out of Stock"    # Critical alert
ELIF stock < threshold     → "Restock Needed"  # Red alert
ELIF stock < threshold * 2 → "Warning"         # Amber caution
ELSE                       → "Normal"          # Green OK
```

Default threshold: **5 units** (configurable in Settings page of the dashboard).

---

## 4. Order Lifecycle

```
[New Order]
     │
     ▼
  Pending ──▶ Confirmed ──▶ Processing ──▶ Shipped
                  │
                  │ (stock insufficient)
                  ▼
              Delayed ◀──────────────────────────────┐
                  │                                   │
                  │ auto: customer message sent       │
                  │                                   │
                  └──▶[stock replenished]──▶ Resume ┘

  Any active state ──▶ Cancelled ──▶ Refund (pending → processing → done)
```

**Key design decision:** Stock-short orders are set to **Delayed**, not cancelled.  
This preserves revenue. Once stock is replenished, the operator clicks **Resume** and the order continues normally.

---

## 5. Repository Structure

```
/
├── src/
│   ├── pipeline.py        # Main runner — orchestrates all 6 steps
│   ├── data_cleaner.py    # Step 1 & 4 — CSV loading + AI/Recovery
│   ├── decision.py        # Step 5 — IF-THEN threshold logic
│   ├── simulator.py       # Step 2 — network delay & data loss
│   └── db.py              # Step 3 & 6 — SQLite storage & CSV export
│
├── dashboard/
│   └── index.html         # Step 6 — Full standalone web dashboard
│                          #   9 pages: Overview, Orders, Pending,
│                          #   Delayed, Cancel/Refund, Inventory,
│                          #   Purchase Orders, Sales Stats, Settings
│
├── data/
│   ├── inventory.csv      # Sample inventory (22 fashion SKUs)
│   ├── orders.csv         # Sample order records (15 orders)
│   └── sample_output.csv  # Pipeline output after Step 5 decision
│
├── README.md              # This file
└── TROUBLESHOOTING.md     # Bugs encountered and fixes
```

---

## 6. Technology Stack

| Layer | Technology | Note |
|-------|-----------|------|
| Language | Python 3.11+ | Pipeline (`/src`) |
| Database | SQLite 3 | Via Python `sqlite3` stdlib |
| Data | CSV / Pandas-compatible | No Pandas dependency required |
| Dashboard | HTML + Vanilla JavaScript | Zero install — open in browser |
| Fonts | Noto Sans KR, JetBrains Mono | Via Google Fonts CDN |

> **Why HTML instead of Streamlit?**  
> Streamlit requires a Python runtime to be running. The HTML approach means anyone can open `dashboard/index.html` in any browser — no server, no installation, no dependencies.

---

## 7. Dashboard Features

| Page | Description |
|------|-------------|
| **Overview** | Real-time KPI cards, stock alerts, recent orders, PO status, change log |
| **Order List** | Full order table with search, status filter, inline actions |
| **Pending Queue** | Orders awaiting confirmation or processing |
| **Delay Management** | Delayed orders with customer message panel and Resume button |
| **Cancel & Refund** | Cancel reason logging, 3-stage refund flow |
| **Inventory** | 22 SKUs across 5 categories — on-hand / reserved / available |
| **Purchase Orders** | Reorder recommendations, supplier & ETA tracking, stock-in |
| **Sales Statistics** | Per-SKU sold units, category cancel/delay rates |
| **Settings** | Shop name, threshold, auto-message toggle, simulation speed |

---

## 8. How to Run the Pipeline

### Requirements

```bash
python --version   # Python 3.11 or higher recommended
```

No third-party libraries required. Uses only Python standard library.

### Run once

```bash
cd src
python pipeline.py
```

### Run with custom options

```bash
python pipeline.py \
  --csv   ../data/inventory.csv \
  --db    ../data/inventory.db \
  --output ../data/dashboard_output.csv \
  --threshold 5 \
  --loss  0.15 \
  --delay 1.0
```

### Run continuously (every N seconds)

```bash
python pipeline.py --interval 5
```

### Open the dashboard

Simply open `dashboard/index.html` in any web browser.  
No server required.

---

## 9. Sample Pipeline Output

```
[14:30:01] INFO  ═══════════════════════════════════════════════════
[14:30:01] INFO    CLOSET.KR Smart Inventory Pipeline – Starting
[14:30:01] INFO  ═══════════════════════════════════════════════════
[14:30:01] INFO  STEP 1 ▸ Data Generation — reading data/inventory.csv
[14:30:01] INFO    → 22 rows loaded
[14:30:01] INFO  STEP 2 ▸ Transmission — delay=1.0s, loss_rate=15%
[14:30:02] INFO    → 19 transmitted, 3 dropped (15% loss rate)
[14:30:02] INFO  STEP 3 ▸ Collection — storing to data/inventory.db
[14:30:02] INFO    → 19 rows upserted
[14:30:02] INFO  STEP 4 ▸ AI / Recovery — cleaning data
[14:30:02] INFO    → 0 missing values recovered
[14:30:02] INFO  STEP 5 ▸ Decision — threshold=5
[14:30:02] INFO    [ALERT] 미디 플리츠 스커트 (블랙/M)     stock=0 → Out of Stock
[14:30:02] INFO    [ALERT] 와이드 데님 팬츠 (인디고/28)   stock=1 → Restock Needed
[14:30:02] INFO    → 8 item(s) flagged as 'Restock Needed'
[14:30:02] INFO  STEP 6 ▸ Dashboard — exporting results
[14:30:02] INFO    → Dashboard-ready CSV written to data/dashboard_output.csv
[14:30:02] INFO  ═══════════════════════════════════════════════════
[14:30:02] INFO    Pipeline complete. 22 items processed.
[14:30:02] INFO  ═══════════════════════════════════════════════════
```

---

## 10. Data Description

### `data/inventory.csv`

| Column | Type | Description |
|--------|------|-------------|
| `item_name` | string | SKU name including color and size |
| `category` | string | 상의 / 하의 / 아우터 / 원피스·세트 / 액세서리 |
| `stock_count` | int | Current on-hand quantity |
| `max_stock` | int | Maximum capacity for this SKU |

### `data/orders.csv`

| Column | Type | Description |
|--------|------|-------------|
| `order_id` | string | Unique order identifier |
| `buyer` | string | Customer name |
| `item_name` | string | Ordered SKU |
| `quantity` | int | Ordered quantity |
| `status` | string | pending / confirmed / processing / shipped / delayed / cancelled |
| `created_at` | datetime | Order timestamp |
| `delay_reason` | string | Reason if delayed |
| `refund_status` | string | pending / processing / done (if cancelled) |

---

## 11. Author

| Field | Value |
|-------|-------|
| Name | Lim Yujin (임유진) |
| Student ID | 2024270678 |
| Course | ICT — Intermediate Project |
| Date | 2026.05.31 |
