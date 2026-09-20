import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Loading, ErrorState, Empty, Status } from "@/components/ui";
import { InventoryTable } from "@/components/inventory-table";
import type { Metric } from "@/lib/types";
import { money, decimal } from "@/lib/api";
const product = {
  product_id: "1",
  product_name: "Cedar Whiskey",
  sku: "0001",
  upc: "001234",
  brand: "Cedar",
  category: "Whiskey",
  vendor_id: "v1",
  vendor_name: "Pacific",
  current_quantity: 8,
  inventory_value: 144,
  days_of_supply: 2,
  margin: 0.38,
  sales_30: 120,
  status: "stockout",
  recommended_cases: 8,
  stockout: true,
  slow: false,
  dead: false,
  abc: "A",
  size: "750 ml",
} as Metric;
describe("owner-facing states", () => {
  it("announces loading", () => {
    render(<Loading />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });
  it("shows a useful error and retries", () => {
    const retry = vi.fn();
    render(<ErrorState message="Database unavailable" retry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Database unavailable");
    fireEvent.click(screen.getByText("Try again"));
    expect(retry).toHaveBeenCalledOnce();
  });
  it("explains an empty workspace", () => {
    render(
      <Empty title="Import your data">
        <p>Upload sales</p>
      </Empty>,
    );
    expect(screen.getByText("Upload sales")).toBeVisible();
  });
  it("uses clear stock labels", () => {
    render(<Status value="stockout" />);
    expect(screen.getByText("Reorder soon")).toBeVisible();
  });
  it("preserves unknown money", () => {
    expect(money(null)).toBe("—");
    expect(decimal(null)).toBe("—");
  });
});
describe("inventory exploration", () => {
  it("shows product links and case quantities", () => {
    render(<InventoryTable products={[product]} />);
    expect(screen.getByRole("link", { name: "Cedar Whiskey" })).toHaveAttribute(
      "href",
      "/products/1",
    );
    expect(screen.getByText("8 cases")).toBeVisible();
  });
  it("searches UPC and reports no results", () => {
    render(<InventoryTable products={[product]} />);
    fireEvent.change(screen.getByLabelText("Search inventory"), {
      target: { value: "001234" },
    });
    expect(screen.getByText("Cedar Whiskey")).toBeVisible();
    fireEvent.change(screen.getByLabelText("Search inventory"), {
      target: { value: "unknown" },
    });
    expect(screen.getByText("No matching products")).toBeVisible();
  });
  it("filters by stock status", () => {
    render(<InventoryTable products={[product]} />);
    fireEvent.change(screen.getByLabelText("Stock status"), {
      target: { value: "dead" },
    });
    expect(screen.queryByText("Cedar Whiskey")).not.toBeInTheDocument();
  });
  it("sorts quantities numerically", () => {
    render(
      <InventoryTable
        products={[
          product,
          {
            ...product,
            product_id: "2",
            product_name: "Other",
            current_quantity: 2,
          },
        ]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "On hand" }));
    expect(screen.getAllByRole("row")[1]).toHaveTextContent("Other");
  });
});
