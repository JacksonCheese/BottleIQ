import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CircleDollarSign, ShoppingCart } from "lucide-react";
import {
  ActionQueue,
  DashboardNotice,
  DashboardSkeleton,
  DecisionCard,
  InventorySummary,
} from "@/components/dashboard";

describe("dashboard presentation", () => {
  it("exposes a decision as one descriptive link", () => {
    render(
      <DecisionCard
        label="BUILD THIS WEEK’S ORDER"
        value="$31,943"
        description="17 products are ready for review."
        href="/smart-orders"
        action="Review order"
        icon={<ShoppingCart aria-hidden="true" />}
        tone="primary"
      />,
    );

    expect(
      screen.getByRole("link", { name: /build this week’s order/i }),
    ).toHaveAttribute("href", "/smart-orders");
    expect(screen.getByText("$31,943")).toBeVisible();
  });

  it("explains the consequence of one missing cost", () => {
    render(<DashboardNotice missingCostCount={1} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "1 product is missing a cost",
    );
    expect(
      screen.getByRole("link", { name: "Fix missing costs" }),
    ).toHaveAttribute("href", "/alerts");
  });

  it("uses plural copy for multiple missing costs", () => {
    render(<DashboardNotice missingCostCount={2} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "2 products are missing costs",
    );
  });

  it("renders an action queue and its values", () => {
    render(
      <ActionQueue
        title="Order first"
        subtitle="Products most likely to run out"
        href="/smart-orders"
        linkText="See full order"
        emptyMessage="Nothing needs ordering right now."
        icon={ShoppingCart}
        tone="order"
        items={[
          {
            id: "1",
            name: "Orchard Vale Classic Liqueur",
            detail: "Order 7 cases · 0.9 days left",
            href: "/products/1",
            value: "$1,248",
          },
        ]}
      />,
    );

    expect(
      screen.getByRole("link", { name: /Orchard Vale Classic Liqueur/i }),
    ).toHaveAttribute("href", "/products/1");
    expect(screen.getByText("$1,248")).toBeVisible();
  });

  it("renders an explicit empty queue", () => {
    render(
      <ActionQueue
        title="Pause buying"
        subtitle="Products holding the most cash"
        href="/inventory?status=slow"
        linkText="See slow stock"
        emptyMessage="No slow inventory needs attention."
        icon={CircleDollarSign}
        tone="cash"
        items={[]}
      />,
    );
    expect(
      screen.getByText("No slow inventory needs attention."),
    ).toBeVisible();
  });

  it("shows inventory freshness and catalog size", () => {
    render(
      <InventorySummary
        latestSnapshot="2026-09-20"
        inventoryValue="$211,848"
        productCount={96}
      />,
    );
    expect(screen.getByText("Updated Sep 20, 2026")).toBeVisible();
    expect(
      screen.getByRole("link", { name: "View all 96 products" }),
    ).toHaveAttribute("href", "/inventory");
  });

  it("announces the dashboard skeleton", () => {
    render(<DashboardSkeleton />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading dashboard");
  });
});
