# POS export intake status

These checks use fictional rows with column names and behaviors described in vendor documentation. They are **schema checks**, not validation of three merchant exports. A paid pilot still needs three redacted, actual store exports and a signed-off reconciliation for each location and date range.

| Published format | BottleIQ status | Pilot action |
| --- | --- | --- |
| [Square Item Library CSV](https://squareup.com/help/us/en/article/5153-import-items-online) | Tested inventory mapping using `SKU`, `Item Name`, `Price`, `Default Unit Cost`, vendor, and the selected location's `Current quantity` column. | Export one location, confirm the current-quantity column matches that store, and verify unit cost and case pack. Square exports can vary by subscription and location. |
| [Lightspeed Retail R-Series item export](https://retail-support.lightspeedhq.com/hc/en-us/articles/115004963387-Importing-and-updating-items-using-a-spreadsheet) | Tested inventory mapping using `Custom SKU`, `Item`, `QOH`, `Default Cost`, `Default - Price`, and `Vendor`. | Confirm the store and whether `QOH` is a physical count or an estimate. Map the actual file's headers; the vendor says export columns can vary. |
| [Shopify POS order CSV](https://help.shopify.com/en/manual/fulfillment/managing-orders/exporting-orders) | **Held / unsupported as a direct sales upload.** The generic importer rejects it because order rows require carry-forward fields, timestamps, and line-level revenue calculations. Refunds are also order-level. | Do not map `Total` or `Subtotal` to each line. Prepare a reviewed daily SKU sales file with unique order/line IDs and reconcile refunds, discounts, tax, and POS source before import. |

The fixtures in `data/pos-schemas/` reproduce the documented shapes with invented values. The tests assert that Square and Lightspeed mappings preserve leading-zero SKUs, quantities, and vendors, and that Shopify orders fail closed. Real exports are required before declaring any POS integration certified.

For each live pilot export, record the POS version, location, exact header row, date range, source row count, item units, and line-level revenue. The sales upload compares those independent source totals with parsed rows. A missing attestation, mismatch, rejected return, or unresolved import error holds recommendations. The owner must correct the source and record a resolution note; a note alone is not evidence of reconciliation. Keep customer names, email addresses, and payment details out of BottleIQ imports.
