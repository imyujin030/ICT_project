# TROUBLESHOOTING.md

> Major bugs encountered during development of CLOSET.KR  
> and how each one was resolved.

---

## Bug 1 — Inventory Edit/Delete Affected the Wrong Item When Category Filter Was Active

### Symptom

When a category filter (e.g. "상의" / Tops) was applied in the Inventory page, clicking the **Edit** or **Delete** button on any row would modify or remove the **wrong item**.

For example, selecting "Delete" on the first row of the filtered list would delete the first item in the *unfiltered* array, not the item displayed.

### Root Cause

The edit and delete buttons were generated with **array index** (`inventory.indexOf(item)`):

```javascript
// WRONG — index depends on the current render order
<button onclick="openInvEdit(${inventory.indexOf(item)})">Edit</button>
<button onclick="deleteInvItem(${inventory.indexOf(item)})">Delete</button>
```

When a category filter was active, the rendered list was a **subset** of the full inventory array. The index in the subset did not match the index in the original array.

### Fix

Replaced all array-index references with **item ID lookups** using the unique `item.id` field:

```javascript
// CORRECT — always resolves to the right item regardless of filter
<button onclick="openInvEdit(${item.id})">Edit</button>
<button onclick="deleteInvItem(${item.id})">Delete</button>
```

Updated the functions to find items by ID:

```javascript
function openInvEdit(id) {
    const item = invById(id);   // invById = inventory.find(i => i.id === id)
    // ...
}

function deleteInvItem(id) {
    const idx = inventory.findIndex(i => i.id === id);
    inventory.splice(idx, 1);
    // ...
}
```

### Lesson Learned

Never use a rendered-list index as a reference to underlying data when the list can be filtered or reordered. Always use a stable unique identifier.

---

## Bug 2 — Delayed Orders Showed "Stock Insufficient" Even After Restock

### Symptom

An order with status `delayed` continued to show the **"재고 부족 (Stock Insufficient)"** badge in the Order List page even after the inventory was manually updated to have sufficient stock.

### Root Cause

The `hasLow` variable in `renderOrdersPage()` was using a **shortcut check**:

```javascript
// WRONG — assumes delayed = always stock insufficient
const hasLow = o.status === 'delayed' ||
               o.items.some(i => { const inv = invById(i.invId); return inv && available(inv) < i.qty; });
```

The `o.status === 'delayed'` check forced `hasLow = true` for all delayed orders, even when the actual inventory was now sufficient.

### Fix

Removed the status-based shortcut and always checked **actual available stock**:

```javascript
// CORRECT — always check real-time available stock
const hasLow = o.items.some(i => {
    const inv = invById(i.invId);
    return !inv || available(inv) < i.qty;
});
```

This means: after stock is replenished, the badge correctly changes from "재고 부족" to "확인됨 (Confirmed)", and the **Resume** button becomes available.

### Lesson Learned

UI state should always reflect live data. Do not use order status as a proxy for stock availability — they can diverge.

---

## Bug 3 — Sales Statistics Page Always Showed Zero Even During Simulation

### Symptom

Running the auto-simulation for several minutes, the **Sales Statistics** page showed `0개 (0 units)` sold for all items, even though orders were moving through the pipeline.

### Root Cause

The auto-simulation only advanced orders to `confirmed` status automatically. Orders never progressed to `processing` → `shipped`, which is the only step where `inv.sold` is incremented.

```javascript
// The only place sold count was updated:
if (o.status === 'processing') {
    inv.sold = (inv.sold || 0) + qty;  // only reached manually
}
```

### Fix

Added automatic progression for `confirmed → processing → shipped` inside `simulateTick()`:

```javascript
// Auto: confirmed → processing (30% chance per tick, if stock available)
orders.filter(o => o.status === 'confirmed').forEach(o => {
    if (Math.random() < 0.3) {
        const ok = o.items.every(i => available(invById(i.invId)) >= i.qty);
        if (ok) {
            o.items.forEach(i => { invById(i.invId).reserved += i.qty; });
            o.status = 'processing';
        }
    }
});

// Auto: processing → shipped (40% chance per tick)
orders.filter(o => o.status === 'processing').forEach(o => {
    if (Math.random() < 0.4) {
        o.items.forEach(i => {
            const inv = invById(i.invId);
            inv.count  = Math.max(0, inv.count - i.qty);
            inv.reserved = Math.max(0, inv.reserved - i.qty);
            inv.sold = (inv.sold || 0) + Math.min(i.qty, inv.count + i.qty);
        });
        o.status = 'shipped';
    }
});
```

### Lesson Learned

In a simulation, ensure all pipeline stages are automated if analytics depend on them. A feature that requires manual action may never produce data during testing.

---

## Bug 4 — Category Statistics Double-Counted Orders With Multiple Items

### Symptom

An order containing one "상의 (Tops)" item and one "하의 (Bottoms)" item was counted **twice** for both categories in the Sales Statistics page, inflating the order counts.

### Root Cause

The category stats loop iterated over **items** inside each order, not over orders:

```javascript
// WRONG — iterates items, counts the same order multiple times per category
orders.forEach(o => {
    o.items.forEach(i => {
        const inv = invById(i.invId);
        const cat = inv.cat;
        catStats[cat].orders++;   // incremented for EACH item, not each order
        if (o.status === 'cancelled') catStats[cat].cancelled++;
    });
});
```

### Fix

Used a `Set` to deduplicate categories per order before incrementing:

```javascript
// CORRECT — each order counted once per category
orders.forEach(o => {
    const cats = new Set(
        o.items.map(i => { const inv = invById(i.invId); return inv ? inv.cat : null; })
               .filter(Boolean)
    );
    cats.forEach(cat => {
        catStats[cat].orders++;
        if (o.status === 'cancelled') catStats[cat].cancelled++;
        if (o.status === 'delayed')   catStats[cat].delayed++;
    });
});
```

### Lesson Learned

When aggregating order-level statistics from item-level data, always deduplicate at the order level first.

---

## Bug 5 — `renderSettingsPage()` Reset Inputs to Default Every Time

### Symptom

When navigating away from the Settings page and coming back, all input fields (threshold, shop name, etc.) reverted to their hardcoded default values, losing any changes the user had made.

### Root Cause

`renderSettingsPage()` was an **empty function**:

```javascript
function renderSettingsPage() {}  // did nothing
```

The HTML inputs had hardcoded `value=""` defaults. Each time the page was shown, they were never updated to reflect `cfg` (the runtime config object).

### Fix

Implemented `renderSettingsPage()` to read from the `cfg` object and push current values into each input:

```javascript
function renderSettingsPage() {
    const sn = document.getElementById('set-shop-name');
    if (sn) sn.value = cfg.shopName;

    const st = document.getElementById('set-threshold');
    if (st) st.value = cfg.threshold;

    const sm = document.getElementById('set-auto-msg');
    if (sm) sm.value = cfg.autoMsg ? '1' : '0';

    const si = document.getElementById('set-sim-interval');
    if (si) si.value = cfg.simInterval / 1000;
}
```

Also added `onchange="applyAutoMsg()"` to the auto-message select element, which had been missing and causing the setting to never actually save.

### Lesson Learned

Render functions must always sync from the data model to the UI. Leaving a render function empty means the UI diverges from the application state.

---

## Bug 6 — "Delayed" Box Invisible on Order Lifecycle Slide (PowerPoint)

### Symptom

In the PowerPoint presentation (slide 7 / slide 5 in v2), the **"Delayed" box** was rendered behind the dark explanation callout box and appeared invisible in LibreOffice Impress preview images.

### Root Cause

PptxGenJS renders shapes in the **order they are added** to the slide. The dark callout box was added *after* the Delayed box, covering it completely (z-order issue).

### Fix

Reordered the `addShape()` calls so that the dark callout box is added **first**, and the Delayed box is added **after**:

```javascript
// Draw dark callout FIRST (renders underneath)
s.addShape(pres.shapes.RECTANGLE, { x:0.5, y:3.7, ...dark callout... });

// Draw Delayed box SECOND (renders on top)
s.addShape(pres.shapes.RECTANGLE, { x:1.9, y:2.82, ...cyan Delayed box... });
```

### Note

LibreOffice Impress and PowerPoint handle z-order slightly differently. The fix resolves the issue in PowerPoint (the intended viewer). Minor rendering differences in LibreOffice previews are expected.

### Lesson Learned

When generating PPTX programmatically, draw background elements first and foreground elements last. There is no "bring to front" API in PptxGenJS — order of calls is the only z-order control.
