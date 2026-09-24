# Inventory intelligence definitions

## Date window and completeness

Use the store's local date as `as_of`. The current, incomplete sales day is excluded. Default demand is 60 complete calendar days, configurable to 30/60/90. Build a zero-filled daily series from the store's first observed sale date to `as_of`; a short history uses only observed calendar days. Zero-sale records are accepted and help establish coverage. At least 14 calendar days are required before an order is eligible.

This assumes an export covers all days in its range. Missing export days cannot be distinguished from no-sale days in V1. Stockouts can suppress observed demand; this engine does not infer lost sales. No per-SKU launch dates or promotion forecasts are available. Check coverage and recent promotions during onboarding.

## Demand and order calculations

For daily unit quantities `q[d]` in the selected window:

| Metric | Definition |
| --- | --- |
| Average daily demand (ADD) | `sum(q) / calendar_days` |
| Daily variability | population standard deviation `std(q, ddof=0)` |
| Lead-time demand | `ADD × lead_days` |
| Safety stock | `NormalInverseCDF(service_level) × std(q) × sqrt(lead_days)` |
| Reorder point | `ADD × lead_days + safety_stock` |
| Target stock | `ADD × (lead_days + target_days) + safety_stock` |
| Inventory position | `on_hand + confirmed incoming units due within lead_days + target_days` |
| Recommended cases | `ceil(max(0, target_stock − inventory_position) / units_per_case)` |
| Recommended units | `cases × units_per_case` |
| Days of supply | `on_hand / ADD`; null when ADD is zero |

Defaults: 95% service level (`Z ≈ 1.644854`), vendor-specific lead time (4 days for newly imported vendors), 21 days of inventory after lead time, case pack 12 when absent. Owners should verify both defaults. Target is configurable 7–60 days via API (common presets in the UI); service level supports 80–99.9% via API.

This is a **weekly periodic-review fill-to-target policy**. A product above its reorder point may still warrant an order. Reorder point is the stockout warning threshold, not an ordering gate. Zero-demand and over-target items receive zero. Rounding may carry more inventory than the target; no case-breaking or budget optimization is modeled. With zero variability the formula produces zero safety stock; this is a model assumption, not certainty.

Owners record only confirmed incoming deliveries, with quantities in units and an expected date. An open delivery due inside the planning window reduces the new order. An overdue open delivery is excluded and holds the recommendation until it is reviewed. After receipt appears in a new inventory snapshot, the owner marks the incoming record handled. Existing order drafts do not recalculate; create a new draft after changing incoming stock. Days of supply remains based on on-hand inventory. Stockout risk projects average demand through lead time and counts confirmed arrivals on their expected dates; an arrival after stock runs out does not hide the risk.

Orders are held if cost is missing/zero, vendor is missing, inventory is missing or over seven days old, total observed history is under 14 days, the latest store sales record is over seven days old, or an incoming delivery is overdue. Each metric contains blockers and a human-readable explanation. A held recommendation has zero units, and unknown costs remain null.

## Profitability and inventory health

| Metric | Calculation and caveat |
| --- | --- |
| Inventory value | `ending units × latest snapshot cost`; unknown costs excluded from totals and disclosed |
| Gross margin | `(retail price − cost) / retail price`; null for missing cost or zero retail |
| Gross profit | trailing 90-day revenue minus units sold times latest cost; estimated COGS |
| Average inventory cost | unweighted average of available inventory snapshot values in 90 days; with one snapshot, ending value |
| Turnover | trailing 90-day estimated COGS / estimated average inventory cost; not annualized |
| GMROI | trailing 90-day estimated gross profit / estimated average inventory cost; not annualized |
| Sell through | trailing 90-day units / (trailing 90-day units + ending units) |
| Dead stock | no sales in `dead_days` (default 90), on hand > 0, and store history spans that interval |
| Slow stock | on hand > 0 and days supply > `slow_days` (default 90), or no demand |
| Stockout risk | ADD > 0 and on hand ≤ reorder point |
| Abnormal demand | last 7-day average ≥ 2 × previous 28-day average, baseline > 0, increase ≥ 1 unit/day |
| ABC | descending 90-day revenue; A up to 80%, B up to 95%, C thereafter |

For ABC, the item that crosses a threshold remains in the earlier class; zero-total catalogs are C. Ties break by product ID. Profitability ratios are null where their denominator is zero. Slow and dead flags can overlap; dashboard slow value explicitly excludes dead value so the two dollar cards are additive. Alerts may show both a stockout risk and a data blocker; owners must resolve the blocker before ordering.

Financial impact on an alert means the product's current inventory cost, **not projected savings or lost revenue**. No ROI claim is made from synthetic data. GMROI and turnover are always labeled estimates because snapshot sampling and latest-cost COGS are approximations.

## Manual examples in the synthetic fixture

- `BTL-0001`: 4/day, 8 on hand, 4-day lead, σ=0, pack 12. Safety=0, point=16, target=100, deficit=92, cases=8, units=96, cost=$1,728 at $18/unit.
- `BTL-0021`: 2/day, 70 on hand, 4-day lead, σ=0, pack 12. Point=8, target=50, deficit=0, days supply=35, order=0.
- `BTL-0081`: no sales in 90 days, positive stock. ADD=0, point=target=0, days supply=null, order=0, dead and slow.

See `docs/engineering-report.md` for verified values and test results from the delivered build.
