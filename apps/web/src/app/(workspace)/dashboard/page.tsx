"use client";

import Link from "next/link";
import {
  ArrowRight,
  CircleDollarSign,
  ShoppingCart,
  TriangleAlert,
} from "lucide-react";
import {
  ActionQueue,
  DashboardNotice,
  DashboardSkeleton,
  DecisionCard,
  InventorySummary,
} from "@/components/dashboard";
import { useWorkspace } from "@/components/workspace";
import { PageTitle, ErrorState, Empty } from "@/components/ui";
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
  if (!dashboard) return <DashboardSkeleton />;

  const cashTiedUp = dashboard.slow_value + dashboard.dead_value;
  const orderItems = dashboard.actions.slice(0, 3).map((product) => ({
    id: product.product_id,
    name: product.product_name,
    detail: `Order ${product.recommended_cases} cases · ${decimal(product.days_of_supply)} days left`,
    href: `/products/${product.product_id}`,
    value: money(product.estimated_cost),
  }));
  const pauseItems = dashboard.cash_tied_up.slice(0, 3).map((product) => ({
    id: product.product_id,
    name: product.product_name,
    detail:
      product.days_of_supply === null
        ? "No recent sales"
        : `${decimal(product.days_of_supply)} days of stock`,
    href: `/products/${product.product_id}`,
    value: money(product.inventory_value),
  }));

  return (
    <>
      <PageTitle
        eyebrow="TODAY’S PRIORITIES"
        title={`Good morning, ${user.name.split(" ")[0]}.`}
      >
        Start with the decisions that protect availability and cash flow.
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
          <div className="dashboard-decision-grid">
            <DecisionCard
              label="BUILD THIS WEEK’S ORDER"
              value={money(dashboard.order_cost)}
              description={`${dashboard.recommended_reorders} products are ready for review.`}
              href="/smart-orders"
              action="Review suggested order"
              icon={<ShoppingCart aria-hidden="true" size={23} />}
              tone="primary"
            />
            <DecisionCard
              label="PREVENT STOCKOUTS"
              value={`${dashboard.stockout_risks} products`}
              description="Likely to run out before the next delivery."
              href="/inventory?status=stockout"
              action="Review low stock"
              icon={<TriangleAlert aria-hidden="true" size={23} />}
              tone="warning"
            />
            <DecisionCard
              label="FREE TRAPPED CASH"
              value={money(cashTiedUp)}
              description="Slow and dead stock worth a closer look."
              href="/inventory?status=slow"
              action="Review slow stock"
              icon={<CircleDollarSign aria-hidden="true" size={23} />}
              tone="neutral"
            />
          </div>

          {dashboard.missing_cost_count > 0 && (
            <DashboardNotice missingCostCount={dashboard.missing_cost_count} />
          )}

          <div className="dashboard-queue-grid">
            <ActionQueue
              title="Order first"
              subtitle="Products most likely to run out"
              href="/smart-orders"
              linkText="See full order"
              items={orderItems}
              emptyMessage="Nothing needs ordering right now."
              icon={ShoppingCart}
              tone="order"
            />
            <ActionQueue
              title="Pause buying"
              subtitle="Products holding the most cash"
              href="/inventory?status=slow"
              linkText="See all slow stock"
              items={pauseItems}
              emptyMessage="No slow inventory needs attention."
              icon={CircleDollarSign}
              tone="cash"
            />
          </div>

          <InventorySummary
            latestSnapshot={dashboard.latest_snapshot}
            inventoryValue={money(dashboard.inventory_value)}
            productCount={dashboard.product_count}
          />
        </>
      )}
    </>
  );
}
