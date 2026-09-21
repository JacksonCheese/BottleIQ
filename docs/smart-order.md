# Smart Orders

1. Import current inventory and sales history; optionally import purchases.
2. Review data alerts, case packs, and distributor lead times.
3. Open `/smart-orders`. Select a 30/60/90-day demand window, target supply, and service level.
4. Review each distributor's eligible products and estimated cost. Create a draft.
5. Inspect each explanation, change case quantities, or use zero to exclude a product.
6. Save changes. Export is disabled while edits are unsaved.
7. Download CSV, check distributor availability/pricing, then submit through the distributor's existing channel.

Creating a draft recomputes eligibility on the server rather than trusting browser totals. Order lines save the case pack, original explanation, unit cost, units, and line total. Edits accept only whole case counts in 0–10,000 and products already on that order. The server recalculates amounts with fixed-point decimals. PostgreSQL row locking and version checks prevent a stale browser tab from overwriting another saved edit; stale saves return 409 and require refresh.

A minimum-order warning appears when the estimated draft is below the vendor minimum. BottleIQ does not pad an order to meet a minimum, optimize purchasing across competing vendors, or enforce availability. Default vendor assignment can be reviewed on the product page.

Export includes vendor, SKU, product, cases, units, cost, total, and explanation. Zero-case lines are omitted. Spreadsheet formula-leading text is escaped. CSV is a purchasing review artifact, not evidence that a supplier accepted an order. There is no automatic submission and no email/SMS sending.

## Limits owners must review

- Open purchase orders are not reconciled: check outstanding deliveries to avoid duplicate buying.
- Latest inventory snapshots are not decremented by subsequent sales. Use same-day snapshots for ordering.
- Taxes, freight, deals, allocations, and vendor catalog availability are not modeled.
- Zero-demand items receive zero; out-of-stock history may understate true demand.
- Safety stock assumes roughly independent daily demand and a normal approximation.
- Recent promotions and seasonal events can make trailing demand a poor guide.
- All persisted drafts remain drafts. Receiving, cancellations, export history, and approval workflows are future work.
