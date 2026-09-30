"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Metric, Store } from "@/lib/types";

type SampleKind = "inventory" | "sales" | "purchases";
type TourStep = {
  title: string;
  description: string;
  useful: string;
  path: string;
  target: string;
  sample?: SampleKind;
};

const steps: TourStep[] = [
  {
    title: "Start with your store",
    description:
      "Choose the location you want to review. This demo opens Cedar & Cask’s Downtown store; another location would have its own stock and recommendations.",
    useful: "Every number that follows belongs to the selected store.",
    path: "/dashboard",
    target: "store-select",
  },
  {
    title: "Bring in an inventory count",
    description:
      "We loaded an example CSV preview with a product, on-hand units, cost, price, distributor, and case pack. In your store, choose an inventory export from your POS.",
    useful:
      "A recent count anchors stock value and prevents ordering bottles you already have.",
    path: "/imports",
    target: "import-example",
    sample: "inventory",
  },
  {
    title: "Match the CSV columns",
    description:
      "BottleIQ matches each required field to a column. You can change these selections before validating and importing a real file. The example stays in preview mode.",
    useful:
      "Correct mapping keeps a quantity or price from being read as the wrong field.",
    path: "/imports",
    target: "import-mapping",
    sample: "inventory",
  },
  {
    title: "Add sales history",
    description:
      "The sales example shows dates, SKU, units sold, revenue, and unit price. A real store should provide at least 90 days of history when available.",
    useful:
      "Sales pace and variability turn a shelf count into days of supply and reorder timing.",
    path: "/imports",
    target: "import-mapping",
    sample: "sales",
  },
  {
    title: "Add distributor purchases",
    description:
      "The purchase example includes date, distributor, SKU, quantity in individual units, cost, and invoice number.",
    useful:
      "Purchase records provide replenishment context and make distributor spending easier to review.",
    path: "/imports",
    target: "import-mapping",
    sample: "purchases",
  },
  {
    title: "See the order opportunity",
    description:
      "Today turns the imported data into a short decision list. This card estimates the cost of products ready for order review.",
    useful:
      "It brings the most urgent purchasing work to the front without placing an order for you.",
    path: "/dashboard",
    target: "dashboard-order",
  },
  {
    title: "Spot stockout risk",
    description:
      "These products may run out before the next delivery. Open the card to review the individual SKUs and their remaining supply.",
    useful: "Protects sales and customer trust on fast-moving bottles.",
    path: "/dashboard",
    target: "dashboard-stockout",
  },
  {
    title: "Find cash tied up on shelves",
    description:
      "Slow and dead stock is valued here. These bottles may deserve a pause before you buy more.",
    useful:
      "Moves attention from excess inventory to products customers actually want.",
    path: "/dashboard",
    target: "dashboard-cash",
  },
  {
    title: "Review alerts",
    description:
      "Alerts collect urgent risks, opportunities, and missing information. Filter by severity, then open a product to investigate.",
    useful:
      "Missing costs or stale data can make a suggested purchase unreliable.",
    path: "/alerts",
    target: "alert-filters",
  },
  {
    title: "Inspect every product",
    description:
      "Search and filter your products by stock status, category, distributor, or ABC class. Each row shows sales, stock, margin, and suggested cases.",
    useful:
      "A quick way to verify a recommendation against what is on the shelf.",
    path: "/inventory",
    target: "inventory-table",
  },
  {
    title: "Understand one recommendation",
    description:
      "The product page combines on-hand and confirmed incoming stock, compares that position with target stock, then rounds the gap to whole cases.",
    useful:
      "You can see the reason for a suggestion before adding it to a purchase list.",
    path: "product",
    target: "recommendation",
  },
  {
    title: "Check the math and assumptions",
    description:
      "Demand, variability, distributor lead time, safety stock, margin, and turnover appear here. The sales chart above shows the history behind the estimate.",
    useful:
      "These are planning estimates. Check promotions, returns, and unrecorded orders before buying.",
    path: "product",
    target: "recommendation-math",
  },
  {
    title: "Tune the order plan",
    description:
      "Change the demand window, desired days of supply, or service level to see how the suggested quantities respond.",
    useful:
      "Different delivery patterns and risk tolerance call for different coverage.",
    path: "/smart-orders",
    target: "order-controls",
  },
  {
    title: "Build by distributor",
    description:
      "BottleIQ groups recommended products by distributor and estimates the cost. Continue to open a synthetic draft for practice.",
    useful:
      "One reviewed draft per distributor is easier to check against case packs and minimums.",
    path: "/smart-orders",
    target: "vendor-grid",
  },
  {
    title: "Review and adjust the draft",
    description:
      "Edit case counts, remove a line by setting it to zero, and save before exporting. The synthetic draft is never sent to a distributor.",
    useful:
      "A person retains the final purchasing decision; edits are recorded in order history.",
    path: "/smart-orders",
    target: "order-editor",
  },
  {
    title: "Export only after review",
    description:
      "Export downloads a CSV for your distributor workflow. Check delivery timing, open orders, promotions, freight, and taxes first.",
    useful:
      "The walkthrough ends with a reviewable purchase list, not an automatic purchase.",
    path: "/smart-orders",
    target: "order-export",
  },
];

type Highlight = { top: number; left: number; width: number; height: number };

export function DemoWalkthrough({
  store,
  start,
}: {
  store: Store;
  start: number;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [index, setIndex] = useState<number | null>(null);
  const [product, setProduct] = useState<{ storeId: string; path: string }>();
  const [error, setError] = useState("");
  const [highlight, setHighlight] = useState<Highlight | null>(null);
  const card = useRef<HTMLElement>(null);

  const productPath = product?.storeId === store.id ? product.path : "";

  useEffect(() => {
    if (sessionStorage.getItem("bottleiq:walkthrough") === "start") {
      const timer = window.setTimeout(() => {
        sessionStorage.removeItem("bottleiq:walkthrough");
        setIndex(0);
      }, 0);
      return () => window.clearTimeout(timer);
    }
  }, []);

  useEffect(() => {
    if (start > 0) {
      const timer = window.setTimeout(() => {
        setError("");
        setIndex(0);
      }, 0);
      return () => window.clearTimeout(timer);
    }
  }, [start]);

  useEffect(() => {
    if (index === null || productPath) return;
    let active = true;
    api<Metric[]>(`/inventory?store_id=${store.id}`)
      .then((products) => {
        if (active) {
          const product =
            products.find((item) => item.recommended_cases > 0) || products[0];
          if (product)
            setProduct({
              storeId: store.id,
              path: `/products/${product.product_id}`,
            });
          else setError("The demo has no products to tour. Reseed demo data.");
        }
      })
      .catch(() => {
        if (active) setError("Could not load a demo product. Try again later.");
      });
    return () => {
      active = false;
    };
  }, [index, productPath, store.id]);

  const step = index === null ? null : steps[index];
  const destination = step?.path === "product" ? productPath : step?.path;

  useEffect(() => {
    if (destination && pathname !== destination) {
      router.push(destination);
    }
  }, [destination, pathname, router]);

  useEffect(() => {
    if (!step?.sample || pathname !== "/imports") return;
    const sample = step.sample;
    const timer = window.setInterval(() => {
      const tab = document.querySelector<HTMLButtonElement>(
        `[data-tour-kind="${sample}"]`,
      );
      if (!tab) return;
      if (!tab.classList.contains("active")) {
        tab.click();
        return;
      }
      const button = document.querySelector<HTMLButtonElement>(
        '[data-tour="sample-import"]',
      );
      if (button) {
        button.click();
        window.clearInterval(timer);
      }
    }, 100);
    return () => window.clearInterval(timer);
  }, [index, pathname, step?.sample]);

  useEffect(() => {
    if (step?.target !== "order-editor" || pathname !== "/smart-orders") return;
    let opened = false;
    const timer = window.setInterval(() => {
      if (document.querySelector('[data-tour="order-editor"]')) {
        window.clearInterval(timer);
        return;
      }
      if (opened) return;
      const existing = document.querySelector<HTMLButtonElement>(
        '[data-tour="saved-drafts"] button:not([disabled])',
      );
      const create = document.querySelector<HTMLButtonElement>(
        '[data-tour="vendor-grid"] button:not([disabled])',
      );
      const action = existing || create;
      if (action) {
        opened = true;
        action.click();
      }
    }, 250);
    return () => window.clearInterval(timer);
  }, [index, pathname, step?.target]);

  useEffect(() => {
    if (!step || pathname !== destination) return;
    let scrolled = false;
    const measure = () => {
      if (
        step.sample &&
        document
          .querySelector("[data-tour-preview-kind]")
          ?.getAttribute("data-tour-preview-kind") !== step.sample
      ) {
        setHighlight(null);
        return;
      }
      const element = document.querySelector<HTMLElement>(
        `[data-tour="${step.target}"]`,
      );
      if (!element) {
        setHighlight(null);
        return;
      }
      if (!scrolled) {
        element.scrollIntoView({
          block: window.innerWidth < 650 ? "start" : "center",
          behavior: "instant",
        });
        if (window.innerWidth < 650)
          window.scrollBy({ top: -115, behavior: "instant" });
        scrolled = true;
      }
      const bounds = element.getBoundingClientRect();
      const left = Math.max(8, bounds.left - 8);
      const top = Math.max(8, bounds.top - 8);
      const next = {
        left,
        top,
        width: Math.max(
          0,
          Math.min(window.innerWidth - left - 8, bounds.width + 16),
        ),
        height: Math.max(
          0,
          Math.min(window.innerHeight - top - 8, bounds.height + 16),
        ),
      };
      setHighlight((previous) =>
        previous &&
        previous.left === next.left &&
        previous.top === next.top &&
        previous.width === next.width &&
        previous.height === next.height
          ? previous
          : next,
      );
    };
    measure();
    const timer = window.setInterval(measure, 200);
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [destination, index, pathname, step]);

  useEffect(() => {
    if (index !== null) card.current?.focus({ preventScroll: true });
  }, [index]);

  useEffect(() => {
    if (index === null) return;
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIndex(null);
    };
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [index]);

  if (!step || index === null) return null;

  const phase = index < 5 ? "SET UP" : index < 12 ? "UNDERSTAND" : "ORDER";
  const visibleHighlight = pathname === destination ? highlight : null;
  const bottom = visibleHighlight
    ? visibleHighlight.top + visibleHighlight.height
    : 0;
  const mobile = window.innerWidth < 650;
  let cardStyle;
  if (mobile) {
    cardStyle = { left: 12, right: 12, bottom: 12 };
  } else if (visibleHighlight) {
    const right = visibleHighlight.left + visibleHighlight.width;
    const sideTop = Math.max(
      16,
      Math.min(visibleHighlight.top, window.innerHeight - 360),
    );
    if (window.innerWidth - right >= 420) {
      cardStyle = { left: right + 16, top: sideTop };
    } else if (visibleHighlight.left >= 420) {
      cardStyle = { left: visibleHighlight.left - 406, top: sideTop };
    } else {
      cardStyle = {
        left: Math.max(
          16,
          Math.min(visibleHighlight.left, window.innerWidth - 410),
        ),
        top:
          bottom + 330 < window.innerHeight
            ? bottom + 14
            : Math.max(16, visibleHighlight.top - 322),
      };
    }
  } else {
    cardStyle = {
      left: Math.max(16, (window.innerWidth - 390) / 2),
      top: Math.max(16, (window.innerHeight - 320) / 2),
    };
  }

  return (
    <div className="tour-layer" aria-label="Guided demo walkthrough">
      {visibleHighlight ? (
        <>
          <div
            className="tour-shade"
            style={{ top: 0, left: 0, right: 0, height: visibleHighlight.top }}
          />
          <div
            className="tour-shade"
            style={{ top: bottom, left: 0, right: 0, bottom: 0 }}
          />
          <div
            className="tour-shade"
            style={{
              top: visibleHighlight.top,
              left: 0,
              width: visibleHighlight.left,
              height: visibleHighlight.height,
            }}
          />
          <div
            className="tour-shade"
            style={{
              top: visibleHighlight.top,
              left: visibleHighlight.left + visibleHighlight.width,
              right: 0,
              height: visibleHighlight.height,
            }}
          />
          <div className="tour-highlight" style={visibleHighlight} />
        </>
      ) : (
        <div className="tour-shade" style={{ inset: 0 }} />
      )}
      <section
        className="tour-card"
        role="dialog"
        aria-labelledby="tour-title"
        tabIndex={-1}
        ref={card}
        style={cardStyle}
      >
        <div className="tour-card-top">
          <span>
            {phase} · {index + 1} OF {steps.length}
          </span>
          <button
            type="button"
            aria-label="Close walkthrough"
            onClick={() => setIndex(null)}
          >
            <X size={18} />
          </button>
        </div>
        <div className="tour-progress" aria-hidden="true">
          <span style={{ width: `${((index + 1) / steps.length) * 100}%` }} />
        </div>
        <h2 id="tour-title">{step.title}</h2>
        <p>{step.description}</p>
        {index === 0 && (
          <p className="tour-store">Current store: {store.name}</p>
        )}
        <div className="tour-why">
          <strong>Why it helps</strong>
          <span>{step.useful}</span>
        </div>
        {error && (
          <p role="alert" className="error-text">
            {error}
          </p>
        )}
        {!visibleHighlight && !error && (
          <p role="status" className="tour-loading">
            Loading this part of the demo…
          </p>
        )}
        <div className="tour-actions">
          <button
            type="button"
            className="button secondary small"
            disabled={index === 0}
            onClick={() => setIndex(index - 1)}
          >
            <ArrowLeft size={15} /> Back
          </button>
          <button
            type="button"
            className="button small"
            disabled={!visibleHighlight}
            onClick={() =>
              setIndex(index === steps.length - 1 ? null : index + 1)
            }
          >
            {index === steps.length - 1 ? "Finish" : "Next"}
            {index < steps.length - 1 && <ArrowRight size={15} />}
          </button>
        </div>
        <small>
          Synthetic store · example CSVs are preview-only · no order is sent
        </small>
      </section>
    </div>
  );
}
