# BottleIQ supervised pilot runbook

## Start a new pilot database

Use a dedicated PostgreSQL database and set `DATABASE_URL` in the repository-root `.env` (copy `.env.example`). For a local demo, run:

```sh
make setup
make db
make migrate
make check-migrations
make seed
make dev
```

Open `http://localhost:3000` and select **Try the Demo**. `make seed` adds fictional data only; skip it for a real store. The API refuses to start if its database is behind the checked-in migrations and tells you to run `make migrate`. Run `make check-migrations` before each deployment. Keep `DEMO_ENABLED=false` and `COOKIE_SECURE=true` when `ENVIRONMENT=production`.

## Bring in store data

Create an account and store, then open **Update data**. Import inventory first, at least 90 days of sales next, and distributor purchases last. Choose the CSV export type, map each required BottleIQ field to one CSV column, preview the rows, and select **Validate & import**. Include the case pack and distributor in inventory when available. Purchase quantities are individual units. Dates use `YYYY-MM-DD`; an inventory row without a date uses the store's local date.

The result shows imported, duplicate, and rejected counts. If rows are rejected, open the rejection report, correct the original CSV, and upload the corrected file. Accepted rows stay saved. The upload history remains on the Update data page. Do not upload a second copy of the same export with different values unless you have reviewed how conflicting records are handled in [the import contract](csv-imports.md).

## Review a recommendation

Open **Today** for the daily priorities, then **Products** for product-level stock and sales. Check missing costs, distributors, stale exports, case packs, and confirmed incoming deliveries before purchasing. On a product page, record stock already on the way; BottleIQ subtracts the remaining expected units from the suggested order. Record partial or complete receipts as deliveries arrive. A fresh physical count supersedes earlier receipt adjustments. An overdue delivery pauses the recommendation until handled. Open **Order**, create a draft for one distributor, adjust cases, save, and export its CSV for review. Order changes and the editor are recorded in the order's `/smart-orders/{order_id}/history` API endpoint.

## Report a pilot issue

Open a [BottleIQ GitHub issue](https://github.com/JacksonCheese/BottleIQ/issues) with the page, steps to reproduce, expected and actual result, store timezone, and approximate time. Include the request code shown by an API error when available. For an import problem, include the CSV header and a few fictional or redacted example rows plus the rejection report message. Do not attach an unredacted customer export or credentials. If a recommendation looks wrong, include the product SKU, on-hand and incoming quantities, case pack, sales window, and the displayed explanation; hold the purchase until a person reviews it.
