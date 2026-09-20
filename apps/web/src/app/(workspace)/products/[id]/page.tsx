"use client";
import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ShoppingCart, Save } from "lucide-react";
import { useWorkspace } from "@/components/workspace";
import { PageTitle, Panel, Loading, ErrorState, Status } from "@/components/ui";
import { SalesChart } from "@/components/charts";
import { useResource } from "@/lib/use-resource";
import { api, decimal, money } from "@/lib/api";
import type { Metric, Vendor } from "@/lib/types";
export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { store, user } = useWorkspace();
  const {
    data: m,
    error,
    reload,
  } = useResource<Metric>(`/products/${id}?store_id=${store.id}`);
  const vendors = useResource<Vendor[]>("/vendors");
  const [saveError, setSaveError] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!m) return <Loading />;
  return (
    <>
      <Link className="back-link" href="/inventory">
        <ArrowLeft size={15} />
        All inventory
      </Link>
      <PageTitle
        eyebrow={`${m.sku} · ${m.category.toUpperCase()}`}
        title={m.product_name}
        action={<Status value={m.status} />}
      >
        {m.size} · {m.vendor_name || "No distributor assigned"} · ABC class{" "}
        {m.abc}
      </PageTitle>
      <div className="recommendation-callout">
        <ShoppingCart size={24} />
        <div>
          <strong>
            {m.recommended_cases
              ? `Recommended: ${m.recommended_cases} cases · ${m.recommended_units} units`
              : "No purchase recommended"}
          </strong>
          <p>{m.explanation}</p>
        </div>
        <Link className="button" href="/smart-orders">
          Review Smart Order
        </Link>
      </div>
      <div className="product-metrics">
        {[
          ["On hand", `${m.current_quantity} units`],
          ["Inventory value", money(m.inventory_value)],
          [
            "Days of supply",
            m.days_of_supply === null ? "No demand" : decimal(m.days_of_supply),
          ],
          [
            "Gross margin",
            m.margin === null ? "—" : `${decimal(m.margin * 100)}%`,
          ],
          ["Unit cost", money(m.unit_cost, true)],
          ["Retail price", money(m.retail_price, true)],
          ["30-day sales", `${m.sales_30} units`],
          ["90-day sales", `${m.sales_90} units`],
        ].map(([label, value]) => (
          <div key={label}>
            <small>{label}</small>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <Panel
        title="How this product moves"
        subtitle="Daily sales · last 90 complete calendar days"
      >
        <SalesChart data={m.sales_history} />
      </Panel>
      <div className="dashboard-grid">
        <Panel title="The math behind the recommendation">
          <dl className="definition-list">
            {[
              [
                "Average daily demand",
                `${decimal(m.average_daily_demand, 2)} units`,
              ],
              ["Demand variability (daily σ)", decimal(m.demand_std, 2)],
              ["Distributor lead time", `${m.lead_time_days} days`],
              ["Safety stock (95%)", `${decimal(m.safety_stock, 2)} units`],
              ["Reorder point", `${decimal(m.reorder_point, 2)} units`],
              ["Target inventory", `${decimal(m.target_stock, 2)} units`],
              ["Case pack", `${m.units_per_case} units`],
              ["90-day gross profit (estimate)", money(m.gross_profit)],
              ["90-day turnover (estimate)", decimal(m.turnover, 2)],
              ["90-day GMROI (estimate)", decimal(m.gmroi, 2)],
              ["90-day sell through", `${decimal(m.sell_through * 100)}%`],
            ].map(([l, v]) => (
              <div key={l}>
                <dt>{l}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
          <p className="padded muted-copy">
            COGS uses the latest unit cost. Turnover and GMROI use an unweighted
            snapshot average; with one snapshot, ending inventory is the
            denominator. Returns and lost sales are not modeled.
          </p>
        </Panel>
        <Panel
          title="Product settings"
          subtitle="Changes apply across your organization’s stores"
        >
          <form
            className="padded"
            key={`${m.product_id}-${m.vendor_id}-${m.units_per_case}`}
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setSaved(false);
              setSaveError("");
              const f = new FormData(e.currentTarget);
              try {
                await api(`/products/${m.product_id}`, {
                  method: "PATCH",
                  body: JSON.stringify({
                    default_vendor_id: f.get("vendor") || null,
                    units_per_case: Number(f.get("pack")),
                    category: f.get("category"),
                    brand: f.get("brand"),
                  }),
                });
                reload();
                setSaved(true);
              } catch (e) {
                setSaveError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Distributor
              <select name="vendor" defaultValue={m.vendor_id || ""}>
                <option value="">Unassigned</option>
                {vendors.data?.map((v) => (
                  <option value={v.id} key={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Units per case
              <input
                name="pack"
                type="number"
                min={1}
                max={1000}
                required
                defaultValue={m.units_per_case}
              />
            </label>
            <label>
              Category
              <input
                name="category"
                required
                maxLength={80}
                defaultValue={m.category}
              />
            </label>
            <label>
              Brand
              <input name="brand" maxLength={120} defaultValue={m.brand} />
            </label>
            {saveError && <ErrorState message={saveError} />}
            <button
              className="button secondary"
              disabled={busy || user.role === "viewer"}
            >
              <Save size={16} />
              {busy ? "Saving…" : "Save product settings"}
            </button>
            {saved && <p role="status">Product settings saved.</p>}
            <p className="muted-copy">
              To change stock, cost, or retail price, upload a newer dated
              inventory snapshot.
            </p>
          </form>
        </Panel>
      </div>
    </>
  );
}
