# BottleIQ Progress Report Design

Date: 2026-10-12
Status: Approved design

## Objective

Show a store owner what changed after they started using BottleIQ, in a form that can be printed and handed over. The report must be trustworthy: a fixed starting point, the same definitions the dashboard already uses, and wording that describes change since tracking began rather than claiming BottleIQ caused it.

## Approach

A **frozen Day 1 baseline plus live comparisons**.

- When tracking starts, the store's headline inventory numbers are calculated as of the chosen start date and stored permanently. Later imports or corrections cannot move the starting point.
- "Now" numbers and monthly sales/profit are calculated live from the store's data each time the report is opened. No monthly upkeep is required.

Rejected alternatives: recalculating the baseline on the fly (the starting point silently shifts when historical data is corrected) and storing a snapshot every month (depends on someone remembering to save it, and is more to build).

## Data model

New table `progress_baselines` (one per store), tenant-scoped like the other tables:

| Column | Notes |
| --- | --- |
| `id`, `organization_id`, `created_at` | Standard identity and tenant columns |
| `store_id` | Unique; composite foreign key to `stores` with `organization_id` |
| `started_on` | Store-local date tracking began; on or before today |
| `created_by_user_id` | Foreign key to `users` |
| `metrics` | JSON headline numbers captured at start (below) |

Captured `metrics`, using `analyze(..., as_of=started_on)` and the dashboard's definitions:

- `inventory_value`, `dead_value`, `slow_value` (slow excluding dead, as on the dashboard)
- `stockout_risks`, `product_count`, `missing_cost_count`
- `revenue_90`, `gross_profit_90` (trailing 90 days before the start date, estimated COGS)
- `snapshot_at` (latest inventory count used)

## API

- `GET /progress?store_id=` — any member. Returns `baseline` (or `null`), `current` headline numbers (same fields, calculated now), `comparison`, and `months`.
- `POST /progress` `{store_id, started_on?}` — owner/admin. `started_on` defaults to today in the store's timezone. Rejects a future date (422), a date with no inventory count on or before it (422, "Import an inventory count dated on or before …"), and an existing baseline (409).
- `DELETE /progress?store_id=` — owner/admin. Removes the baseline so tracking can be restarted. The UI asks for confirmation.

Store access uses the existing `get_store` tenant check.

## Profit comparison

Monthly rows cover the 12 calendar months up to and including the current month (labeled month-to-date). Each row has revenue, estimated gross profit, and the same month last year when sales history reaches it.

Gross profit follows the existing definition: revenue minus units × latest known unit cost. Revenue from products with no known cost is excluded from profit and reported separately so the page can disclose it.

The headline comparison covers complete days from `started_on` to yesterday:

1. **Year over year** when sales history reaches one year before `started_on`: revenue and gross profit since tracking versus the same dates last year.
2. **Before vs. since** otherwise: average gross profit per 30 days since tracking versus the up-to-90 days before tracking, with a note that seasonality may explain part of the change.
3. **Too early** when fewer than 7 complete days have passed since the start date.

## Page

New workspace page `/progress`, linked as **Progress** in the main navigation after Alerts.

- **Not started:** short explanation, start-date field (default today), **Start tracking** button (owner/admin only), and a tip to import 12 months of sales for year-over-year comparisons.
- **Started:** "Tracking since {date} ({n} days)" header with **Print report** and **Restart tracking** controls; four Day 1 vs. now cards (cash tied up, dead stock, slow stock, products at risk of running out) showing the change; the headline profit comparison; the monthly table; and footnotes on estimated profit and seasonality.
- Print styles hide navigation and controls so the report prints cleanly.

Wording describes change since tracking began. The page never states that BottleIQ caused a gain.

## Out of scope

- Recommendation follow-through, which needs placed orders that BottleIQ does not yet record.
- A dollar estimate of lost sales from stockouts; snapshot inventory cannot observe stockouts reliably.
- Seeding a baseline for the demo store.

## Testing

- Service tests: baseline capture as of a past date, start-date validation, monthly aggregation with missing costs, year-over-year versus before/after selection, and the too-early state.
- Route tests: viewers can read but not start or restart, duplicate starts return 409, and other organizations' stores are not accessible.
- Frontend: typecheck, lint, and existing tests pass; the page is checked in the running app.
