"use client";
import { useState } from "react";
import {
  ArrowRight,
  Download,
  ShoppingCart,
  Sparkles,
  Save,
} from "lucide-react";
import { useWorkspace } from "@/components/workspace";
import { PageTitle, Panel, Loading, ErrorState, Empty } from "@/components/ui";
import { api, money, decimal } from "@/lib/api";
import { useResource } from "@/lib/use-resource";
import type { Metric, Order } from "@/lib/types";
export default function Page() {
  const { store, user } = useWorkspace();
  const [target, setTarget] = useState(21);
  const [windowDays, setWindow] = useState(60);
  const [level, setLevel] = useState(0.95);
  const metrics = useResource<Metric[]>(
    `/recommendations?store_id=${store.id}&target_days=${target}&window=${windowDays}&service_level=${level}`,
  );
  const orders = useResource<Order[]>(`/smart-orders?store_id=${store.id}`);
  const [order, setOrder] = useState<Order>();
  const [edits, setEdits] = useState<Record<string, number>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const dirty =
    order?.lines.some((l) => edits[l.product_id] !== l.cases) || false;
  const groups = Object.values(
    (metrics.data || [])
      .filter((m) => m.recommended_cases > 0 && m.vendor_id)
      .reduce<
        Record<
          string,
          { id: string; name: string; items: Metric[]; total: number }
        >
      >((all, m) => {
        const g = all[m.vendor_id!] || {
          id: m.vendor_id!,
          name: m.vendor_name!,
          items: [],
          total: 0,
        };
        g.items.push(m);
        g.total += m.estimated_cost || 0;
        all[g.id] = g;
        return all;
      }, {}),
  );
  function selectOrder(o: Order) {
    setOrder(o);
    setEdits(Object.fromEntries(o.lines.map((l) => [l.product_id, l.cases])));
    setError("");
    setSaved(false);
  }
  async function create(vendor: string) {
    setBusy(true);
    setError("");
    try {
      selectOrder(
        await api<Order>("/smart-orders", {
          method: "POST",
          body: JSON.stringify({
            store_id: store.id,
            vendor_id: vendor,
            target_days: target,
            window: windowDays,
            service_level: level,
          }),
        }),
      );
      orders.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function save() {
    if (!order) return;
    setBusy(true);
    setError("");
    try {
      const next = await api<Order>(`/smart-orders/${order.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          version: order.version,
          lines: Object.entries(edits).map(([product_id, cases]) => ({
            product_id,
            cases,
          })),
        }),
      });
      selectOrder(next);
      setSaved(true);
      orders.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const total =
    order?.lines.reduce(
      (sum, l) =>
        sum + (edits[l.product_id] ?? l.cases) * l.units_per_case * l.unit_cost,
      0,
    ) || 0;
  return (
    <>
      <PageTitle
        eyebrow="LESS GUESSWORK. A BETTER PURCHASE LIST."
        title="Your next Smart Order."
        action={
          <span className="badge healthy">
            <Sparkles size={12} />
            Explainable recommendations
          </span>
        }
      >
        Review your distributors, adjust cases, and export. You make the final
        call.
      </PageTitle>
      <div className="order-controls">
        <label>
          Demand window
          <select
            value={windowDays}
            onChange={(e) => setWindow(Number(e.target.value))}
          >
            {[30, 60, 90].map((v) => (
              <option key={v} value={v}>
                {v} days
              </option>
            ))}
          </select>
        </label>
        <label>
          Target after lead time
          <select
            value={target}
            onChange={(e) => setTarget(Number(e.target.value))}
          >
            {[14, 21, 28, 42].map((v) => (
              <option key={v} value={v}>
                {v} days of supply
              </option>
            ))}
          </select>
        </label>
        <label>
          Service level
          <select
            value={level}
            onChange={(e) => setLevel(Number(e.target.value))}
          >
            <option value={0.9}>90%</option>
            <option value={0.95}>95% (recommended)</option>
            <option value={0.99}>99%</option>
          </select>
        </label>
        <p>
          Case-rounded quantities. Missing or stale data holds an item out of
          the order.
        </p>
      </div>
      {error && <ErrorState message={error} />}{" "}
      {metrics.error ? (
        <ErrorState message={metrics.error} retry={metrics.reload} />
      ) : !metrics.data ? (
        <Loading />
      ) : (
        <div className="vendor-grid">
          {groups.map((g) => (
            <article className="panel vendor-card" key={g.id}>
              <span className="vendor-icon">
                <ShoppingCart size={20} />
              </span>
              <h3>{g.name}</h3>
              <p>
                {g.items.length} products ·{" "}
                {g.items.reduce((s, m) => s + m.recommended_cases, 0)} cases
              </p>
              <strong>{money(g.total)}</strong>
              <span>estimated cost</span>
              <button
                className="button secondary"
                disabled={busy || dirty || user.role === "viewer"}
                onClick={() => create(g.id)}
              >
                Create draft
                <ArrowRight size={16} />
              </button>
            </article>
          ))}
          {groups.length === 0 && (
            <Empty title="No orders to build right now.">
              <p>
                Inventory is covered, or recommendations are held for missing
                data. Review alerts for details.
              </p>
            </Empty>
          )}
        </div>
      )}
      {order && (
        <Panel
          title={order.vendor_name}
          subtitle={`Draft · ${new Date(order.generated_at).toLocaleDateString()} · Version ${order.version}`}
        >
          <div className="notice">
            Set a line to 0 cases to exclude it. Save edits before exporting.
            {saved && <strong> Changes saved.</strong>}
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Product / recommendation</th>
                  <th>Case pack</th>
                  <th>Unit cost</th>
                  <th>Cases</th>
                  <th>Line total</th>
                </tr>
              </thead>
              <tbody>
                {order.lines.map((l) => (
                  <tr key={l.product_id}>
                    <td>
                      <strong>{l.product_name}</strong>
                      <p className="line-explanation">{l.explanation}</p>
                    </td>
                    <td>{l.units_per_case} units</td>
                    <td>{money(l.unit_cost, true)}</td>
                    <td>
                      <input
                        className="case-input"
                        type="number"
                        min={0}
                        max={10000}
                        step={1}
                        aria-label={`Cases for ${l.product_name}`}
                        value={edits[l.product_id] ?? l.cases}
                        disabled={user.role === "viewer"}
                        onChange={(e) => {
                          setEdits({
                            ...edits,
                            [l.product_id]: Math.max(
                              0,
                              Math.min(
                                10000,
                                Math.floor(Number(e.target.value)),
                              ),
                            ),
                          });
                          setSaved(false);
                        }}
                      />
                    </td>
                    <td className="number">
                      {money(
                        (edits[l.product_id] ?? l.cases) *
                          l.units_per_case *
                          l.unit_cost,
                        true,
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="order-total">
            <div>
              <small>Estimated order total</small>
              <strong>{money(total, true)}</strong>
              {order.minimum_order_amount !== null &&
                total < order.minimum_order_amount && (
                  <p className="error-text">
                    Below distributor minimum of{" "}
                    {money(order.minimum_order_amount)}. Review before sending.
                  </p>
                )}
            </div>
            <div>
              <button
                className="button secondary"
                onClick={save}
                disabled={busy || !dirty || user.role === "viewer"}
              >
                <Save size={16} />
                Save changes
              </button>
              <a
                className={`button ${dirty ? "disabled" : ""}`}
                aria-disabled={dirty}
                role="link"
                tabIndex={dirty ? -1 : 0}
                href={
                  dirty ? undefined : `/api/smart-orders/${order.id}/export`
                }
              >
                <Download size={16} />
                Export CSV
              </a>
            </div>
          </div>
          <p className="padded muted-copy">
            Taxes, freight, discounts, open purchase orders, and case
            availability are not included. Exporting does not submit an order.
          </p>
        </Panel>
      )}
      <Panel
        title="Saved drafts"
        subtitle="Reopen an order to review or export it"
      >
        {orders.error ? (
          <ErrorState message={orders.error} retry={orders.reload} />
        ) : (
          <div className="compact-list">
            {orders.data?.map((o) => (
              <button
                key={o.id}
                disabled={dirty}
                onClick={() => selectOrder(o)}
              >
                <span className="bottle-tile">
                  <ShoppingCart size={20} />
                </span>
                <div>
                  <strong>{o.vendor_name}</strong>
                  <p>
                    {new Date(o.generated_at).toLocaleString()} ·{" "}
                    {o.lines.filter((l) => l.cases > 0).length} items ·{" "}
                    {decimal(
                      o.lines.reduce((s, l) => s + l.cases, 0),
                      0,
                    )}{" "}
                    cases
                  </p>
                </div>
                <strong>{money(o.estimated_total_cost)}</strong>
                <ArrowRight size={16} />
              </button>
            ))}
            {orders.data?.length === 0 && (
              <p className="padded">
                Create your first draft from a distributor above.
              </p>
            )}
          </div>
        )}
      </Panel>
    </>
  );
}
