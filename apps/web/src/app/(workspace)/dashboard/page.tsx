"use client";

import Link from "next/link";
import {
  ArrowRight,
  CalendarDays,
  CircleDollarSign,
  ShoppingCart,
  TriangleAlert,
} from "lucide-react";
import { useWorkspace } from "@/components/workspace";
import { PageTitle, Panel, Loading, ErrorState, Empty } from "@/components/ui";
import { useResource } from "@/lib/use-resource";
import { money, decimal } from "@/lib/api";
import type { Dashboard } from "@/lib/types";

export default function DashboardPage() {
  const { store, user } = useWorkspace();
  const {
    data: dashboard,
    error,
    reload,
  } = useResource<Dashboard>(`/dashboard?store_id=${store.id}`);

  if (error) return <ErrorState message={error} retry={reload} />;
  if (!dashboard) return <Loading />;

  const cashTiedUp = dashboard.slow_value + dashboard.dead_value;

  return (
    <>
      <PageTitle
        eyebrow="TODAY"
        title={`Good morning, ${user.name.split(" ")[0]}.`}
      >
        Here are the three things worth looking at in your store.
      </PageTitle>

      {!dashboard.product_count ? (
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
          <div className="decision-grid">
            <DecisionCard
              eyebrow="ORDER THIS WEEK"
              title={money(dashboard.order_cost)}
              description={`${dashboard.recommended_reorders} products are ready for review.`}
              href="/smart-orders"
              action="Review order"
              icon={<ShoppingCart size={22} />}
              primary
            />
            <DecisionCard
              eyebrow="RUNNING LOW"
              title={`${dashboard.stockout_risks} products`}
              description="These may run out before your next delivery."
              href="/inventory?status=stockout"
              action="See what’s low"
              icon={<TriangleAlert size={22} />}
              tone="warning"
            />
            <DecisionCard
              eyebrow="CASH TIED UP"
              title={money(cashTiedUp)}
              description="Slow and dead stock that deserves a closer look."
              href="/inventory?status=slow"
              action="Review slow stock"
              icon={<CircleDollarSign size={22} />}
            />
          </div>

          {dashboard.missing_cost_count > 0 && (
            <div className="simple-notice">
              <TriangleAlert size={16} />
              <span>
                {dashboard.missing_cost_count}{" "}
                {dashboard.missing_cost_count === 1
                  ? "product is"
                  : "products are"}{" "}
                missing a cost, so{" "}
                {dashboard.missing_cost_count === 1 ? "it" : "they"}{" "}
                {dashboard.missing_cost_count === 1 ? "is" : "are"} not included
                in order totals.
              </span>
              <Link href="/alerts">Fix it</Link>
            </div>
          )}

          <div className="simple-dashboard-grid">
            <Panel
              title="Start here"
              subtitle="The most urgent items to order"
              link={{ href: "/smart-orders", text: "See full order" }}
            >
              <div className="simple-action-list">
                {dashboard.actions.slice(0, 3).map((product) => (
                  <Link
                    href={`/products/${product.product_id}`}
                    className="simple-action-row"
                    key={product.product_id}
                  >
                    <span className="simple-action-icon">
                      <ShoppingCart size={17} />
                    </span>
                    <div>
                      <strong>{product.product_name}</strong>
                      <p>
                        Order {product.recommended_cases} cases · Only{" "}
                        {decimal(product.days_of_supply)} days left
                      </p>
                    </div>
                    <ArrowRight size={16} />
                  </Link>
                ))}
                {!dashboard.actions.length && (
                  <div className="simple-empty-row">
                    Nothing needs ordering right now.
                  </div>
                )}
              </div>
            </Panel>

            <Panel
              title="Pause buying"
              subtitle="Products holding the most cash"
              link={{
                href: "/inventory?status=slow",
                text: "See all slow stock",
              }}
            >
              <div className="simple-action-list">
                {dashboard.cash_tied_up.slice(0, 3).map((product) => (
                  <Link
                    href={`/products/${product.product_id}`}
                    className="simple-action-row"
                    key={product.product_id}
                  >
                    <span className="simple-action-icon muted">
                      <CircleDollarSign size={17} />
                    </span>
                    <div>
                      <strong>{product.product_name}</strong>
                      <p>
                        {product.days_of_supply === null
                          ? "No recent sales"
                          : `${decimal(product.days_of_supply)} days of stock`}
                      </p>
                    </div>
                    <span className="simple-row-value">
                      {money(product.inventory_value)}
                    </span>
                  </Link>
                ))}
                {!dashboard.cash_tied_up.length && (
                  <div className="simple-empty-row">
                    No slow inventory needs attention.
                  </div>
                )}
              </div>
            </Panel>
          </div>

          <section className="inventory-snapshot">
            <div>
              <CalendarDays size={16} />
              <span>
                Inventory updated {dashboard.latest_snapshot || "not yet"}
              </span>
            </div>
            <div>
              <span>Total inventory value</span>
              <strong>{money(dashboard.inventory_value)}</strong>
            </div>
            <Link href="/inventory">
              View all {dashboard.product_count} products
              <ArrowRight size={15} />
            </Link>
          </section>
        </>
      )}
    </>
  );
}

function DecisionCard({
  eyebrow,
  title,
  description,
  href,
  action,
  icon,
  primary = false,
  tone = "",
}: {
  eyebrow: string;
  title: string;
  description: string;
  href: string;
  action: string;
  icon: React.ReactNode;
  primary?: boolean;
  tone?: string;
}) {
  return (
    <Link
      href={href}
      className={`decision-card ${primary ? "primary" : ""} ${tone}`}
    >
      <div className="decision-card-top">
        <span>{eyebrow}</span>
        <span className="decision-icon">{icon}</span>
      </div>
      <strong>{title}</strong>
      <p>{description}</p>
      <span className="decision-action">
        {action}
        <ArrowRight size={15} />
      </span>
    </Link>
  );
}
