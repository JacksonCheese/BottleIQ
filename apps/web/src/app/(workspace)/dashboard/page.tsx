"use client";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  Package,
  CircleDollarSign,
  TriangleAlert,
  ShoppingCart,
  CalendarDays,
} from "lucide-react";
import { useWorkspace } from "@/components/workspace";
import {
  PageTitle,
  Panel,
  Loading,
  ErrorState,
  Empty,
  Status,
} from "@/components/ui";
import { CategoryChart } from "@/components/charts";
import { useResource } from "@/lib/use-resource";
import { money, decimal } from "@/lib/api";
import type { Dashboard } from "@/lib/types";
export default function DashboardPage() {
  const { store, user } = useWorkspace();
  const {
    data: d,
    error,
    reload,
  } = useResource<Dashboard>(`/dashboard?store_id=${store.id}`);
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!d) return <Loading />;
  return (
    <>
      <PageTitle
        eyebrow="YOUR STORE, AT A GLANCE"
        title={`A clearer view, ${user.name.split(" ")[0]}.`}
        action={
          <Link className="button" href="/smart-orders">
            <ShoppingCart size={17} />
            Build Smart Order
            <ArrowRight size={17} />
          </Link>
        }
      >
        Here’s what your shelves are telling you.
      </PageTitle>
      {!d.product_count ? (
        <Empty title="Let’s put your data to work.">
          <p>
            Import your inventory, sales history, and purchases to see your
            first recommendations.
          </p>
          <Link className="button" href="/imports">
            Import your data
            <ArrowRight size={16} />
          </Link>
        </Empty>
      ) : (
        <>
          <div className="data-caption">
            <CalendarDays size={14} />
            Inventory as of {d.latest_snapshot || "not yet imported"}
            <span>·</span>
            {d.product_count} products<span>·</span>60-day demand window
          </div>
          <div className="kpi-grid">
            <Kpi
              label="Total inventory value"
              value={money(d.inventory_value)}
              note="At your current unit costs"
              icon={<Package size={18} />}
            />
            <Kpi
              label="Cash in slow inventory"
              value={money(d.slow_value)}
              note="More than 90 days of supply"
              tone="amber"
              icon={<CircleDollarSign size={18} />}
            />
            <Kpi
              label="Dead inventory value"
              value={money(d.dead_value)}
              note="No sales in the last 90 days"
              icon={<Package size={18} />}
            />
            <Kpi
              label="Stockout risks"
              value={String(d.stockout_risks)}
              note="At or below reorder point"
              tone="red"
              icon={<TriangleAlert size={18} />}
            />
            <Kpi
              label="Recommended reorders"
              value={String(d.recommended_reorders)}
              note="Products to review this week"
              icon={<ShoppingCart size={18} />}
            />
            <Kpi
              label="Estimated Smart Order"
              value={money(d.order_cost)}
              note="Before distributor adjustments"
              tone="green"
              icon={<CircleDollarSign size={18} />}
            />
          </div>
          {d.missing_cost_count > 0 && (
            <div className="notice">
              {d.missing_cost_count} product has no cost. Its value is excluded
              from totals and its order is held.{" "}
              <Link href="/alerts">Review data issues →</Link>
            </div>
          )}
          <section className="attention-strip">
            <span className="attention-icon">
              <TriangleAlert size={21} />
            </span>
            <div>
              <strong>
                {d.stockout_risks
                  ? `${d.stockout_risks} products need a replenishment check.`
                  : "Your shelves have some breathing room."}
              </strong>
              <p>
                {money(d.slow_value + d.dead_value)} is tied up in slow and dead
                inventory. Make room for what sells.
              </p>
            </div>
            <Link href="/alerts">
              Review alerts
              <ArrowRight size={16} />
            </Link>
          </section>
          <div className="dashboard-grid">
            <Panel
              title="Your next best moves"
              subtitle="A short list for a better-stocked week"
              link={{ href: "/smart-orders", text: "View Smart Orders" }}
            >
              <div className="action-list">
                {d.actions.map((m, i) => (
                  <Link
                    href={`/products/${m.product_id}`}
                    className="action-row"
                    key={m.product_id}
                  >
                    <span className="action-index">0{i + 1}</span>
                    <div>
                      <strong>
                        Order {m.recommended_cases} cases of {m.product_name}
                      </strong>
                      <p>
                        {decimal(m.days_of_supply)} days of stock ·{" "}
                        {m.vendor_name}
                      </p>
                    </div>
                    <span className="action-cost">
                      {money(m.estimated_cost)}
                      <ArrowUpRight size={15} />
                    </span>
                  </Link>
                ))}
                {!d.actions.length && (
                  <p className="padded">
                    No eligible reorders. Check data alerts or revisit after the
                    next import.
                  </p>
                )}
              </div>
            </Panel>
            <Panel
              title="What’s on your shelves"
              subtitle="Inventory value by category"
            >
              <CategoryChart data={d.categories} />
            </Panel>
          </div>
          <div className="dashboard-grid">
            <Panel
              title="Earning their shelf space"
              subtitle="Top products by estimated 90-day gross profit"
              link={{ href: "/inventory", text: "All inventory" }}
            >
              <div className="compact-list">
                {d.top_profit.map((m) => (
                  <Link href={`/products/${m.product_id}`} key={m.product_id}>
                    <span className="bottle-tile">
                      {m.category.slice(0, 2).toUpperCase()}
                    </span>
                    <div>
                      <strong>{m.product_name}</strong>
                      <p>
                        {m.category} · {m.sales_90} units sold
                      </p>
                    </div>
                    <strong className="profit">{money(m.gross_profit)}</strong>
                  </Link>
                ))}
              </div>
            </Panel>
            <Panel
              title="Cash you could put to work"
              subtitle="Start with the slowest-moving shelf space"
              link={{
                href: "/inventory?status=slow",
                text: "Review slow stock",
              }}
            >
              <div className="compact-list">
                {d.cash_tied_up.map((m) => (
                  <Link href={`/products/${m.product_id}`} key={m.product_id}>
                    <span className="bottle-tile muted">
                      {m.category.slice(0, 2).toUpperCase()}
                    </span>
                    <div>
                      <strong>{m.product_name}</strong>
                      <p>
                        {m.days_of_supply === null
                          ? "No recent demand"
                          : `${decimal(m.days_of_supply)} days of supply`}{" "}
                        · <Status value={m.status} />
                      </p>
                    </div>
                    <strong>{money(m.inventory_value)}</strong>
                  </Link>
                ))}
              </div>
            </Panel>
          </div>
          <div className="insight-footer">
            <span className="live-dot" />
            Explainable by design. Every order is based on your demand,
            inventory, and distributor lead times.
          </div>
        </>
      )}
    </>
  );
}
function Kpi({
  label,
  value,
  note,
  icon,
  tone = "",
}: {
  label: string;
  value: string;
  note: string;
  icon: React.ReactNode;
  tone?: string;
}) {
  return (
    <article className={`kpi ${tone}`}>
      <div>
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      <p>{note}</p>
    </article>
  );
}
