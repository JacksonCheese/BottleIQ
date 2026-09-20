"use client";
import { useState } from "react";
import Link from "next/link";
import { Search, ArrowDownUp } from "lucide-react";
import type { Metric } from "@/lib/types";
import { money, decimal } from "@/lib/api";
import { Status } from "./ui";
export function InventoryTable({
  products,
  initialStatus = "",
}: {
  products: Metric[];
  initialStatus?: string;
}) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [vendor, setVendor] = useState("");
  const [status, setStatus] = useState(initialStatus);
  const [abc, setAbc] = useState("");
  const [sort, setSort] = useState<keyof Metric>("product_name");
  const [ascending, setAscending] = useState(true);
  const [page, setPage] = useState(0);
  const filtered = products
    .filter(
      (m) =>
        (!search ||
          [m.product_name, m.sku, m.upc, m.brand]
            .join(" ")
            .toLowerCase()
            .includes(search.toLowerCase())) &&
        (!category || m.category === category) &&
        (!vendor || m.vendor_id === vendor) &&
        (!abc || m.abc === abc) &&
        (!status ||
          (status === "slow"
            ? m.slow
            : status === "dead"
              ? m.dead
              : status === "stockout"
                ? m.stockout
                : m.status === status)),
    )
    .sort((a, b) => {
      const x = a[sort],
        y = b[sort];
      const result =
        typeof x === "number" && typeof y === "number"
          ? x - y
          : String(x ?? "").localeCompare(String(y ?? ""));
      return ascending ? result : -result;
    });
  const current = Math.min(
    page,
    Math.max(0, Math.ceil(filtered.length / 25) - 1),
  );
  function order(key: keyof Metric) {
    if (key === sort) setAscending(!ascending);
    else {
      setSort(key);
      setAscending(true);
    }
  }
  const cols: [string, keyof Metric][] = [
    ["Product", "product_name"],
    ["Category", "category"],
    ["Distributor", "vendor_name"],
    ["On hand", "current_quantity"],
    ["Value", "inventory_value"],
    ["Days supply", "days_of_supply"],
    ["Margin", "margin"],
    ["30D sales", "sales_30"],
    ["Status", "status"],
    ["Order", "recommended_cases"],
  ];
  return (
    <section className="panel">
      <div className="filters">
        <div className="search-input">
          <Search size={17} />
          <input
            aria-label="Search inventory"
            placeholder="Search product, SKU, UPC, brand…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
          />
        </div>
        <select
          aria-label="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="">All categories</option>
          {[...new Set(products.map((m) => m.category))].sort().map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
        <select
          aria-label="Distributor"
          value={vendor}
          onChange={(e) => setVendor(e.target.value)}
        >
          <option value="">All distributors</option>
          {[
            ...new Map(
              products
                .filter((m) => m.vendor_id)
                .map((m) => [m.vendor_id, m.vendor_name]),
            ).entries(),
          ].map(([id, name]) => (
            <option key={id} value={id!}>
              {name}
            </option>
          ))}
        </select>
        <select
          aria-label="Stock status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">All statuses</option>
          <option value="stockout">Stockout risk</option>
          <option value="slow">Slow stock</option>
          <option value="dead">Dead stock</option>
          <option value="healthy">Healthy</option>
          <option value="needs_data">Check data</option>
        </select>
        <select
          aria-label="ABC class"
          value={abc}
          onChange={(e) => setAbc(e.target.value)}
        >
          <option value="">ABC class</option>
          {["A", "B", "C"].map((a) => (
            <option key={a}>{a}</option>
          ))}
        </select>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {cols.map(([label, key]) => (
                <th
                  key={key}
                  aria-sort={
                    sort === key
                      ? ascending
                        ? "ascending"
                        : "descending"
                      : "none"
                  }
                >
                  <button onClick={() => order(key)}>
                    {label}
                    <ArrowDownUp size={12} />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.slice(current * 25, (current + 1) * 25).map((m) => (
              <tr key={m.product_id}>
                <td>
                  <Link
                    className="product-link"
                    href={`/products/${m.product_id}`}
                  >
                    {m.product_name}
                  </Link>
                  <div className="table-sub">
                    {m.sku} · {m.size} <span className="abc-tag">{m.abc}</span>
                  </div>
                </td>
                <td>{m.category}</td>
                <td className="vendor-cell">{m.vendor_name || "Unassigned"}</td>
                <td className="number">{m.current_quantity}</td>
                <td className="number">{money(m.inventory_value)}</td>
                <td className="number">
                  {m.days_of_supply === null
                    ? "No demand"
                    : decimal(m.days_of_supply)}
                </td>
                <td className="number">
                  {m.margin === null ? "—" : `${decimal(m.margin * 100)}%`}
                </td>
                <td className="number">{m.sales_30}</td>
                <td>
                  <Status value={m.status} />
                </td>
                <td className="number">
                  {m.recommended_cases ? (
                    <strong>{m.recommended_cases} cases</strong>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!filtered.length && (
          <div className="empty">
            <h3>No matching products</h3>
            <p>Try a different search or clear a filter.</p>
          </div>
        )}
      </div>
      <div className="table-footer">
        <span>
          {filtered.length} products ·{" "}
          {current * 25 + (filtered.length ? 1 : 0)}–
          {Math.min((current + 1) * 25, filtered.length)} shown
        </span>
        <div>
          <button
            className="button secondary small"
            disabled={current === 0}
            onClick={() => setPage(current - 1)}
          >
            Previous
          </button>
          <button
            className="button secondary small"
            disabled={(current + 1) * 25 >= filtered.length}
            onClick={() => setPage(current + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
