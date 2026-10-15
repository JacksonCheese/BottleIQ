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

`make db` requires Docker Compose. If you already run PostgreSQL locally, start it, set `DATABASE_URL` to that server, and skip `make db`.

Open `http://localhost:3000` and select **Try the Demo**. `make seed` adds fictional data only; skip it for a real store. The API refuses to start if its database is behind the checked-in migrations and tells you to run `make migrate`. Run `make check-migrations` before each deployment. Keep `DEMO_ENABLED=false` and `COOKIE_SECURE=true` when `ENVIRONMENT=production`.

For a first-time demonstration, select **Guided walkthrough** on the home page. It tours store selection, example inventory/sales/purchase CSV previews and column mapping, the daily dashboard and alerts, product-level recommendation math, and Smart Order review/export. Example CSVs are not saved; the tour may open a synthetic order draft for practice, but it never sends an order. Use **Walkthrough** in the demo header to replay it, or close it at any step.

## Bring in store data

Create an account and store, then open **Update data**. Import inventory first, at least 90 days of sales next, and distributor purchases last. Choose the CSV export type, map each required BottleIQ field to one CSV column, preview the rows, and select **Validate & import**. Include the case pack and distributor in inventory when available. Purchase quantities are individual units. Dates use `YYYY-MM-DD`; an inventory row without a date uses the store's local date.

For sales, enter the exact first and last days covered plus the POS's independent row, unit, and line-revenue totals. The result compares each source total with the parsed file. These are an operator attestation; BottleIQ cannot prove the POS report is complete. Verify that the export covers the last 14 completed days, including days with zero sales, and that refunds and returns have been reconciled outside the import. [Published POS format checks](pos-formats.md) show what can be mapped and what must be converted first.

The result shows imported, duplicate, and rejected counts and a reconciliation status. If rows are rejected or totals disagree, open the rejection report, correct the source CSV, and upload the corrected file. Accepted rows stay saved. The issue continues to hold recommendations until an owner records a specific correction or review note under **Import history**. A note must describe actual remediation; it does not alter imported rows. Do not upload a second copy of the same export with different values unless you have reviewed how conflicting records are handled in [the import contract](csv-imports.md).

## Review a recommendation

Open **Update data → Data quality** and resolve all purchase holds before reviewing recommendations. Open **Today** for the daily priorities, then **Products** for product-level stock and sales. Check missing costs, distributors, stale exports, case packs, and confirmed incoming deliveries before purchasing. On a product page, record stock already on the way; BottleIQ subtracts the remaining expected units from the suggested order. Record partial or complete receipts as deliveries arrive. A fresh physical count supersedes earlier receipt adjustments. An overdue delivery pauses the recommendation until handled. Open **Order**, create a draft for one distributor, adjust cases, save, and export its CSV for review. Order changes and the editor are recorded in the order's `/smart-orders/{order_id}/history` API endpoint. Do not submit the CSV as an automatic purchase order.

## Staff access and account recovery

The owner can invite an admin or read-only viewer from **Store settings**. Invitations expire in seven days and are sent to the invited address; an invitee creates a password when accepting. Existing BottleIQ accounts cannot be invited into a second organization in this pilot—contact pilot support. On the sign-in page, **Forgot your password?** sends a 30-minute, single-use reset link. Resetting a password revokes all existing sessions. Configure transactional SMTP before staging; do not share reset or invitation URLs in issue reports.

## Staging release and operations

Use the existing hosting account with an HTTPS domain, a private managed PostgreSQL instance that requires TLS, and transactional SMTP. Set `ENVIRONMENT=production`, `DEMO_ENABLED=false`, `COOKIE_SECURE=true`, `WEB_ORIGIN=https://<staging-domain>`, and the managed `DATABASE_URL` with `sslmode=require` or stronger. Set `API_URL` to the private API service. Store credentials only in the host secret manager. Apply `make migrate` once as a release job before starting API replicas, then `make check-migrations` and `make check-staging`. The API refuses to start with unapplied migrations. Use the host's automated encrypted backup plan and test one restore to a separate database before accepting paid data. Configure an HTTPS `/api/health` monitor and alerts for downtime, 5xx responses, database availability, and backup failure; review structured request logs by request ID. The database-backed per-account throttle is shared across API replicas; keep ingress IP/body limits as a second layer.

Record the provider, domain, backup retention, restore test date, alert destination, and deployment owner in the private operations record. These items are not validated by `make check-staging`; the command verifies application settings, migrations, TLS endpoint, and health only. Pause paid onboarding until the live staging checks and restore test have passed.

## Report a pilot issue

Open a [BottleIQ GitHub issue](https://github.com/JacksonCheese/BottleIQ/issues) with the page, steps to reproduce, expected and actual result, store timezone, and approximate time. Include the request code shown by an API error when available. For an import problem, include the CSV header and a few fictional or redacted example rows plus the rejection report message. Do not attach an unredacted customer export or credentials. If a recommendation looks wrong, include the product SKU, on-hand and incoming quantities, case pack, sales window, and the displayed explanation; hold the purchase until a person reviews it.
