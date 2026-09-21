# CSV ingestion

Start at `/imports`. Choose inventory, sales, or purchases, select a UTF-8 CSV (BOM supported), review a preview, map required columns, and import. The API validates again; browser parsing is for preview only. Maximum 10 MB, 100,000 rows, 80 columns, 2,000 characters per field. Unknown columns are ignored. Required canonical headers are:

```csv
# sales.csv
 date,sku,product_name,units_sold,revenue,unit_price
# inventory.csv
 sku,product_name,quantity_on_hand,unit_cost,retail_price
# purchases.csv
 purchase_date,vendor,sku,quantity,unit_cost,invoice_number
```

(The leading spaces and comment lines above are for explanation; use the actual sample files as templates.)

Dates: `YYYY-MM-DD`, no future dates. Numbers: nonnegative, finite, up to 10,000,000. Whole bottles only. Monetary input accepts `$` and commas when correctly CSV-quoted, and at most two decimal places. A blank inventory cost is preserved as unknown and blocks purchasing; it is not treated as zero. Negative sales/returns are rejected: reconcile returns outside BottleIQ until signed inventory movement accounting is implemented.

Optional inventory columns: `snapshot_at`, `category`, `brand`, `size`, `units_per_case`, `upc`, `vendor`. Omitted snapshot date defaults to today in the store's timezone. Omitted case pack defaults to 12; imported vendors default to four-day lead time. Verify these in product and distributor settings before ordering. Inventory can enrich product metadata discovered in an earlier sales import. Distributor assignment is only filled when absent; explicit reassignment is through product settings.

Optional sale columns: `transaction_id`, `line_id`. Optional purchase columns: `line_id`, `product_name`. Missing products are created using organization-scoped SKUs. Leading zeros are preserved.

## Duplicate semantics

- Sales identity: `(store, SKU, date, transaction_id, line_id)`. Without transaction/line IDs, the contract is one daily aggregate per SKU. Aggregate multiple transactions before importing, or supply stable IDs. Identical anonymous transactions cannot be distinguished and are intentionally deduplicated.
- Inventory identity: `(store, SKU, snapshot_date)`.
- Purchase identity: `(store, SKU, purchase_date, vendor, invoice_number, line_id)`.
- A content hash distinguishes exact duplicates from different values sharing an identity.
- The file hash includes bytes and mapping. Re-uploading the same file returns the original job and its counts; it does not increment history or import again.
- Overlapping exports skip exact row duplicates. Conflicts are rejected without silently overwriting existing records.

A malformed header, encoding, or row width rejects the file before writing. Valid-width rows are individually validated within savepoints, so bad numeric/date values reject that row while valid rows succeed. Jobs report imported, duplicate, and rejected counts, and retain every rejection's source row number and reason. No raw rejected cell values or original file contents are retained. Download the text rejection report from import history.

There is no general import undo/correction workflow yet. To correct an erroneous historical record, an operator must reconcile it under a controlled database maintenance procedure. Do not change a transaction identity merely to hide a conflicting duplicate; that would double-count sales. A genuinely new inventory measurement should use its true later snapshot date.

## HTTP example

Authenticate first (HttpOnly session cookie or a cookie jar), then:

```bash
curl -b cookies.txt -X POST http://127.0.0.1:8000/imports/inventory \
  -F 'store_id=YOUR_STORE_ID' \
  -F 'mapping={"sku":"Item Code","quantity_on_hand":"Stock"}' \
  -F 'file=@inventory.csv'
```

`BaseImporter.parse` is the adapter boundary. `GenericCSVImporter` implements the current contract. Square, Clover, Lightspeed, and Korona adapters are future work, not implemented integrations.

## Performance and concurrency

A job uses one transaction with per-row savepoints. Catalog/duplicate indexes are loaded once for efficient validation; PostgreSQL uniqueness constraints remain the final authority during races. A simultaneous duplicate file can return 409, requiring a history refresh. Ingestion executes off the event loop. Next's proxy is configured for 11 MB multipart bodies and a five-minute timeout; configure equivalent limits at your deployment ingress. Jobs are not durable background tasks and are not automatically resumed after an API process crash. The uncommitted job rolls back; retry the file.
