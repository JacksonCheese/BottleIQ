# BottleIQ Dashboard UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished, action-first BottleIQ dashboard that preserves the existing API and navigation while improving hierarchy, responsive behavior, loading feedback, and accessibility.

**Architecture:** Keep data fetching and business-value composition in the dashboard route, and move display-only dashboard patterns into a focused component module. Use typed presentation props rather than coupling the new components to the full API `Metric` type. Extend the existing global stylesheet and Playwright flow instead of adding a UI framework or visual-test dependency.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5.9, Tailwind CSS 4 project globals, Lucide React, Vitest, React Testing Library, Playwright.

## Global Constraints

- Make no backend, API, analytics, or shared response-schema changes.
- Use only fields already returned by `Dashboard`; the trapped-cash total remains `slow_value + dead_value`.
- Preserve existing destinations for Smart Orders, filtered inventory, alerts, imports, inventory, and product detail pages.
- Preserve the deep forest green, warm ivory, white, muted sage, and attention-only amber direction.
- Maintain at least 4.5:1 contrast for normal text and do not use color as the sole status indicator.
- Keep body text at least 16px on mobile and interactive targets at least 44px where practical.
- Use Lucide as the only icon family; do not introduce emoji icons or another icon dependency.
- Use 150–250ms color, border, and shadow transitions only; do not use layout-shifting hover transforms.
- Respect `prefers-reduced-motion` and prevent horizontal page scrolling at 375px.
- Keep loading, error, empty-catalog, missing-cost, and empty-queue states accessible and explicit.
- Do not add dark mode or redesign pages outside the dashboard.

---

## File Structure

- Create `apps/web/src/components/dashboard.tsx`: typed, display-only dashboard components and their accessible markup.
- Create `apps/web/tests/dashboard.test.tsx`: focused component tests for links, state copy, semantics, and presentation data.
- Modify `apps/web/src/app/(workspace)/dashboard/page.tsx`: fetching, existing value formatting, mapping API data into presentation props, and state selection.
- Modify `apps/web/src/app/globals.css`: dashboard visual tokens, component layouts, skeletons, responsive rules, focus states, and reduced-motion behavior.
- Modify `apps/web/tests/e2e/smoke.spec.ts`: desktop dashboard assertions, 375px overflow guard, mobile dashboard screenshot, and navigation checks.
- Update `docs/screenshots/dashboard.png`: browser-generated desktop dashboard evidence.
- Create `docs/screenshots/mobile-dashboard.png`: browser-generated 375px dashboard evidence.

---

### Task 1: Create Typed Dashboard Presentation Components

**Files:**
- Create: `apps/web/src/components/dashboard.tsx`
- Create: `apps/web/tests/dashboard.test.tsx`

**Interfaces:**
- Consumes: `ReactNode`, `next/link`, and Lucide icons supplied by the route.
- Produces: `DecisionCard`, `DashboardNotice`, `ActionQueue`, `InventorySummary`, and `DashboardSkeleton`.
- Produces type: `DashboardActionItem = { id: string; name: string; detail: string; href: string; value?: string }`.
- `DecisionCard` accepts `label`, `value`, `description`, `href`, `action`, `icon`, and `tone: "primary" | "warning" | "neutral"`.
- `ActionQueue` accepts `title`, `subtitle`, `href`, `linkText`, `items`, `emptyMessage`, `icon`, and `tone: "order" | "cash"`.

- [ ] **Step 1: Write failing component tests**

Create `apps/web/tests/dashboard.test.tsx` with concrete coverage for accessible links, singular/plural missing-cost copy, queue content, summary content, and skeleton status:

```tsx
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
    expect(screen.getByRole("link", { name: "Fix missing costs" })).toHaveAttribute(
      "href",
      "/alerts",
    );
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
    expect(screen.getByText("No slow inventory needs attention.")).toBeVisible();
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
    expect(screen.getByRole("link", { name: "View all 96 products" })).toHaveAttribute(
      "href",
      "/inventory",
    );
  });

  it("announces the dashboard skeleton", () => {
    render(<DashboardSkeleton />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading dashboard",
    );
  });
});
```

- [ ] **Step 2: Run the focused tests and verify the missing module failure**

Run:

```bash
cd apps/web
npm test -- dashboard.test.tsx
```

Expected: FAIL because `@/components/dashboard` does not exist.

- [ ] **Step 3: Implement the typed dashboard components**

Create `apps/web/src/components/dashboard.tsx`. Use semantic `section`, `article`, and link markup; keep product rows fully clickable; include text with all status colors; and format the ISO snapshot without timezone drift:

```tsx
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";

export type DashboardActionItem = {
  id: string;
  name: string;
  detail: string;
  href: string;
  value?: string;
};

export function DecisionCard({
  label,
  value,
  description,
  href,
  action,
  icon,
  tone,
}: {
  label: string;
  value: string;
  description: string;
  href: string;
  action: string;
  icon: ReactNode;
  tone: "primary" | "warning" | "neutral";
}) {
  return (
    <Link href={href} className={`dashboard-decision ${tone}`}>
      <span className="dashboard-decision-top">
        <span>{label}</span>
        <span className="dashboard-decision-icon">{icon}</span>
      </span>
      <strong>{value}</strong>
      <p>{description}</p>
      <span className="dashboard-decision-action">
        {action}
        <ArrowRight aria-hidden="true" size={17} />
      </span>
    </Link>
  );
}

export function DashboardNotice({ missingCostCount }: { missingCostCount: number }) {
  const singular = missingCostCount === 1;
  return (
    <div className="dashboard-notice" role="status">
      <TriangleAlert aria-hidden="true" size={18} />
      <p>
        <strong>
          {missingCostCount} {singular ? "product is" : "products are"} missing
          {singular ? " a cost" : " costs"}.
        </strong>{" "}
        {singular ? "It is" : "They are"} excluded from the suggested order total.
      </p>
      <Link href="/alerts">
        Fix missing costs <ArrowUpRight aria-hidden="true" size={15} />
      </Link>
    </div>
  );
}

export function ActionQueue({
  title,
  subtitle,
  href,
  linkText,
  items,
  emptyMessage,
  icon: Icon,
  tone,
}: {
  title: string;
  subtitle: string;
  href: string;
  linkText: string;
  items: DashboardActionItem[];
  emptyMessage: string;
  icon: LucideIcon;
  tone: "order" | "cash";
}) {
  return (
    <section className="dashboard-queue" aria-labelledby={`${tone}-queue-title`}>
      <header>
        <div>
          <h2 id={`${tone}-queue-title`}>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <Link href={href}>
          {linkText} <ArrowUpRight aria-hidden="true" size={15} />
        </Link>
      </header>
      <div className="dashboard-queue-list">
        {items.map((item) => (
          <Link className="dashboard-action-row" href={item.href} key={item.id}>
            <span className={`dashboard-action-icon ${tone}`}>
              <Icon aria-hidden="true" size={18} />
            </span>
            <span className="dashboard-action-copy">
              <strong>{item.name}</strong>
              <span>{item.detail}</span>
            </span>
            {item.value ? (
              <strong className="dashboard-action-value">{item.value}</strong>
            ) : (
              <ArrowRight aria-hidden="true" size={17} />
            )}
          </Link>
        ))}
        {!items.length && (
          <div className="dashboard-queue-empty">
            <CheckCircle2 aria-hidden="true" size={18} />
            <span>{emptyMessage}</span>
          </div>
        )}
      </div>
    </section>
  );
}

function formatSnapshot(value: string | null) {
  if (!value) return "Not imported yet";
  const [year, month, day] = value.split("-").map(Number);
  return `Updated ${new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(year, month - 1, day))}`;
}

export function InventorySummary({
  latestSnapshot,
  inventoryValue,
  productCount,
}: {
  latestSnapshot: string | null;
  inventoryValue: string;
  productCount: number;
}) {
  return (
    <section className="dashboard-inventory-summary" aria-label="Inventory summary">
      <div>
        <CalendarDays aria-hidden="true" size={18} />
        <span>{formatSnapshot(latestSnapshot)}</span>
      </div>
      <div>
        <span>Total inventory value</span>
        <strong>{inventoryValue}</strong>
      </div>
      <Link href="/inventory">
        View all {productCount} products <ArrowRight aria-hidden="true" size={16} />
      </Link>
    </section>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="dashboard-skeleton" role="status" aria-label="Loading dashboard">
      <span className="sr-only">Loading dashboard</span>
      <div className="dashboard-skeleton-title" />
      <div className="dashboard-skeleton-decisions">
        <div /><div /><div />
      </div>
      <div className="dashboard-skeleton-queues">
        <div /><div />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:

```bash
cd apps/web
npm test -- dashboard.test.tsx
```

Expected: all dashboard component tests PASS.

- [ ] **Step 5: Commit the presentation components**

```bash
git add apps/web/src/components/dashboard.tsx apps/web/tests/dashboard.test.tsx
git commit -m "feat: add dashboard presentation components"
```

---

### Task 2: Compose the Action-First Dashboard and Its States

**Files:**
- Modify: `apps/web/src/app/(workspace)/dashboard/page.tsx`
- Modify: `apps/web/tests/e2e/smoke.spec.ts`

**Interfaces:**
- Consumes: all exports from `@/components/dashboard` created in Task 1.
- Consumes: `Dashboard`, `Metric`, `money`, `decimal`, `useResource`, and `useWorkspace` without changing their signatures.
- Produces: three ordered decisions, a conditional missing-cost notice, two three-item action queues, the inventory summary, a page-specific skeleton, and the existing empty/error states.

- [ ] **Step 1: Tighten the desktop browser assertions before restructuring the page**

In the first Playwright test, replace the current two dashboard assertions with the action hierarchy and destination checks:

```ts
await expect(
  page.getByRole("heading", { name: "Good morning, Alex." }),
).toBeVisible();
await expect(
  page.getByRole("link", { name: /Build this week’s order/i }),
).toHaveAttribute("href", "/smart-orders");
await expect(
  page.getByRole("link", { name: /Prevent stockouts/i }),
).toHaveAttribute("href", "/inventory?status=stockout");
await expect(
  page.getByRole("link", { name: /Free trapped cash/i }),
).toHaveAttribute("href", "/inventory?status=slow");
await expect(page.getByRole("heading", { name: "Order first" })).toBeVisible();
await expect(page.getByRole("heading", { name: "Pause buying" })).toBeVisible();
await expect(
  page.getByRole("region", { name: "Inventory summary" }),
).toContainText("Total inventory value");
```

- [ ] **Step 2: Run the desktop browser test and verify the new copy fails**

Run with the seeded services active:

```bash
cd apps/web
npm run test:e2e -- --grep "demo owner"
```

Expected: FAIL because the route still uses `ORDER THIS WEEK`, `RUNNING LOW`, and the previous queue headings.

- [ ] **Step 3: Replace local dashboard markup with the presentation components**

In `apps/web/src/app/(workspace)/dashboard/page.tsx`:

1. Remove the local `DecisionCard` function.
2. Import `ActionQueue`, `DashboardNotice`, `DashboardSkeleton`, `DecisionCard`, and `InventorySummary` from `@/components/dashboard`.
3. Return `<DashboardSkeleton />` while `dashboard` is absent.
4. Keep `<ErrorState message={error} retry={reload} />` for errors.
5. Preserve the existing empty-catalog import link.
6. Map the two API collections into `DashboardActionItem` values before the JSX:

```tsx
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
```

7. Render the approved information order:

```tsx
<PageTitle
  eyebrow="TODAY’S PRIORITIES"
  title={`Good morning, ${user.name.split(" ")[0]}.`}
>
  Start with the decisions that protect availability and cash flow.
</PageTitle>

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
```

- [ ] **Step 4: Run component, browser, and type checks**

Run:

```bash
cd apps/web
npm test -- dashboard.test.tsx
npm run typecheck
npm run test:e2e -- --grep "demo owner"
```

Expected: all three commands PASS. The dashboard browser test continues into inventory and Smart Orders, confirming that the refresh did not break the workflow.

- [ ] **Step 5: Commit the route composition**

```bash
git add 'apps/web/src/app/(workspace)/dashboard/page.tsx' apps/web/tests/e2e/smoke.spec.ts
git commit -m "feat: reorganize dashboard around owner decisions"
```

---

### Task 3: Apply the Responsive Operational-Clarity Visual System

**Files:**
- Modify: `apps/web/src/app/globals.css`
- Modify: `apps/web/tests/e2e/smoke.spec.ts`

**Interfaces:**
- Consumes: the class names emitted by Task 1 and the page ordering from Task 2.
- Produces: desktop three-column decisions, two-column queues, 1150px queue collapse, 760px single-column flow, 375px overflow safety, visible focus states, skeleton geometry, and reduced-motion compliance.

- [ ] **Step 1: Add a failing 375px overflow and touch-navigation browser check**

Update the responsive Playwright test so it inspects the dashboard before opening navigation:

```ts
test("responsive dashboard and navigation stay usable", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await page.getByRole("button", { name: "Try the Demo" }).click();
  await expect(
    page.getByRole("heading", { name: "Good morning, Alex." }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Build this week’s order/i }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../../docs/screenshots/mobile-dashboard.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("link", { name: "Update data", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Bring your store into focus." }),
  ).toBeVisible();
});
```

- [ ] **Step 2: Run the responsive browser test before styling**

Run:

```bash
cd apps/web
npm run test:e2e -- --grep "responsive dashboard"
```

Expected: the structure renders, but visual inspection of the screenshot shows unstyled new class names and the test may report overflow.

- [ ] **Step 3: Replace the legacy dashboard-specific CSS block**

In `apps/web/src/app/globals.css`, remove the old `.decision-*`, `.simple-*`, and `.inventory-snapshot` rules. Keep unrelated legacy `.kpi-*`, `.dashboard-grid`, charts, and other page styles until a later full-app refresh.

Add the new rules with these exact constraints:

```css
.dashboard-decision-grid {
  display: grid;
  grid-template-columns: 1.15fr 1fr 1fr;
  gap: 16px;
  margin-bottom: 18px;
}
.dashboard-decision {
  min-height: 236px;
  padding: 24px;
  border: 1px solid #dfe4dc;
  border-radius: 14px;
  background: #fff;
  display: flex;
  flex-direction: column;
  transition: border-color 0.2s ease, box-shadow 0.2s ease,
    background-color 0.2s ease;
}
.dashboard-decision:hover {
  border-color: #bdc9ba;
  box-shadow: 0 14px 35px rgba(35, 61, 45, 0.08);
}
.dashboard-decision:focus-visible,
.dashboard-queue a:focus-visible,
.dashboard-notice a:focus-visible,
.dashboard-inventory-summary a:focus-visible {
  outline: 3px solid #9eb98b;
  outline-offset: 3px;
}
.dashboard-decision.primary {
  color: #f7faF4;
  background: #245d49;
  border-color: #245d49;
}
.dashboard-decision.warning {
  background: #fcf8ef;
  border-color: #eadfc8;
}
.dashboard-decision-top,
.dashboard-decision-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.dashboard-decision-top {
  color: #5e6f61;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.35px;
}
.dashboard-decision.primary .dashboard-decision-top {
  color: #d9e7d2;
}
.dashboard-decision-icon {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: #edf2ea;
  display: grid;
  place-items: center;
}
.dashboard-decision.primary .dashboard-decision-icon {
  background: rgba(255, 255, 255, 0.12);
}
.dashboard-decision.warning .dashboard-decision-icon {
  color: #8a642d;
  background: #f1e5cd;
}
.dashboard-decision > strong {
  margin-top: 30px;
  color: #20352b;
  font-size: clamp(30px, 2.4vw, 40px);
  line-height: 1.05;
  letter-spacing: -1.4px;
  font-variant-numeric: tabular-nums;
}
.dashboard-decision.primary > strong {
  color: #fff;
}
.dashboard-decision > p {
  margin-top: 10px;
  color: #5f6d63;
  font-size: 13px;
  line-height: 1.55;
}
.dashboard-decision.primary > p {
  color: #d1dfcf;
}
.dashboard-decision-action {
  margin-top: auto;
  padding-top: 24px;
  color: #365f4a;
  font-size: 13px;
  font-weight: 700;
}
.dashboard-decision.primary .dashboard-decision-action {
  color: #eff7ea;
}
.dashboard-notice {
  min-height: 56px;
  padding: 14px 16px;
  border: 1px solid #e8d8b8;
  border-radius: 10px;
  background: #fcf7eb;
  color: #684f2d;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  line-height: 1.5;
}
.dashboard-notice > svg {
  flex: 0 0 auto;
  color: #936a2d;
}
.dashboard-notice a {
  min-height: 44px;
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #315d47;
  font-weight: 700;
  white-space: nowrap;
}
.dashboard-queue-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin: 18px 0;
}
.dashboard-queue {
  overflow: hidden;
  border: 1px solid #dfe4dc;
  border-radius: 14px;
  background: #fff;
}
.dashboard-queue > header {
  min-height: 88px;
  padding: 20px 22px;
  border-bottom: 1px solid #e8ece6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.dashboard-queue h2 {
  color: #20352b;
  font-size: 18px;
}
.dashboard-queue header p {
  margin-top: 5px;
  color: #647169;
  font-size: 12px;
}
.dashboard-queue header a {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #315d47;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}
.dashboard-action-row {
  min-height: 82px;
  padding: 14px 20px;
  border-bottom: 1px solid #edf0eb;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 13px;
  transition: background-color 0.18s ease;
}
.dashboard-action-row:last-child { border-bottom: 0; }
.dashboard-action-row:hover { background: #f7f9f5; }
.dashboard-action-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: grid;
  place-items: center;
}
.dashboard-action-icon.order { color: #315f49; background: #e9f1e7; }
.dashboard-action-icon.cash { color: #7a6036; background: #f4ecdc; }
.dashboard-action-copy strong,
.dashboard-action-copy span { display: block; }
.dashboard-action-copy strong {
  color: #26392e;
  font-size: 13px;
  line-height: 1.4;
}
.dashboard-action-copy span {
  margin-top: 4px;
  color: #6c766f;
  font-size: 11px;
  line-height: 1.45;
}
.dashboard-action-value {
  color: #425b49;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}
.dashboard-queue-empty {
  min-height: 82px;
  padding: 20px;
  color: #5d6f62;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}
.dashboard-inventory-summary {
  min-height: 76px;
  padding: 16px 20px;
  border: 1px solid #dfe4dc;
  border-radius: 14px;
  background: #fff;
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  gap: 30px;
  color: #5f6d63;
  font-size: 12px;
}
.dashboard-inventory-summary > div,
.dashboard-inventory-summary > a {
  display: flex;
  align-items: center;
  gap: 8px;
}
.dashboard-inventory-summary > div:nth-child(2) {
  align-items: baseline;
}
.dashboard-inventory-summary strong {
  color: #20352b;
  font-size: 17px;
  font-variant-numeric: tabular-nums;
}
.dashboard-inventory-summary a {
  min-height: 44px;
  color: #315d47;
  font-weight: 700;
}
.dashboard-skeleton { min-height: 620px; }
.dashboard-skeleton-title,
.dashboard-skeleton-decisions > div,
.dashboard-skeleton-queues > div {
  border-radius: 14px;
  background: linear-gradient(90deg, #e9ede7 25%, #f5f7f3 50%, #e9ede7 75%);
  background-size: 200% 100%;
  animation: dashboard-shimmer 1.4s ease-in-out infinite;
}
.dashboard-skeleton-title { width: min(420px, 78%); height: 82px; margin-bottom: 28px; }
.dashboard-skeleton-decisions,
.dashboard-skeleton-queues { display: grid; gap: 16px; }
.dashboard-skeleton-decisions { grid-template-columns: repeat(3, 1fr); }
.dashboard-skeleton-decisions > div { height: 236px; }
.dashboard-skeleton-queues { grid-template-columns: repeat(2, 1fr); margin-top: 18px; }
.dashboard-skeleton-queues > div { height: 330px; }
@keyframes dashboard-shimmer {
  to { background-position: -200% 0; }
}
```

- [ ] **Step 4: Add explicit responsive rules**

Add the following adjustments inside the existing breakpoints:

```css
@media (max-width: 1150px) {
  .dashboard-decision-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .dashboard-queue-grid { grid-template-columns: 1fr; }
  .dashboard-skeleton-queues { grid-template-columns: 1fr; }
}

@media (max-width: 760px) {
  .page-title p { font-size: 16px; line-height: 1.55; }
  .dashboard-decision-grid,
  .dashboard-skeleton-decisions { grid-template-columns: 1fr; }
  .dashboard-decision { min-height: 216px; padding: 21px; }
  .dashboard-decision > p,
  .dashboard-decision-action { font-size: 16px; }
  .dashboard-notice { align-items: flex-start; flex-wrap: wrap; font-size: 16px; }
  .dashboard-notice a { width: 100%; margin-left: 30px; }
  .dashboard-queue > header { align-items: flex-start; flex-direction: column; gap: 8px; }
  .dashboard-queue h2 { font-size: 20px; }
  .dashboard-queue header p,
  .dashboard-queue header a,
  .dashboard-action-copy strong,
  .dashboard-action-copy span,
  .dashboard-action-value,
  .dashboard-queue-empty { font-size: 16px; }
  .dashboard-action-row { min-height: 94px; padding: 16px; grid-template-columns: 42px minmax(0, 1fr) auto; }
  .dashboard-action-value { max-width: 78px; text-align: right; }
  .dashboard-inventory-summary { grid-template-columns: 1fr; gap: 8px; font-size: 16px; }
  .dashboard-inventory-summary > div:nth-child(2) { justify-content: space-between; }
  .dashboard-inventory-summary a { font-size: 16px; }
  .dashboard-skeleton-title { height: 100px; }
  .dashboard-skeleton-decisions > div { height: 216px; }
}
```

The existing global `@media (prefers-reduced-motion: reduce)` block already disables transitions and animation. Confirm the new skeleton animation is covered by that rule.

- [ ] **Step 5: Run responsive browser, component, lint, and type checks**

Run:

```bash
cd apps/web
npm run test:e2e -- --grep "responsive dashboard"
npm test -- dashboard.test.tsx
npm run lint
npm run typecheck
```

Expected: all commands PASS; `mobile-dashboard.png` shows no horizontal clipping and all action copy is at least 16px.

- [ ] **Step 6: Commit the responsive visual system**

```bash
git add apps/web/src/app/globals.css apps/web/tests/e2e/smoke.spec.ts docs/screenshots/mobile-dashboard.png
git commit -m "style: polish responsive dashboard experience"
```

---

### Task 4: Complete Cross-Viewport Visual QA and Full Verification

**Files:**
- Modify if assertions reveal a defect: `apps/web/src/components/dashboard.tsx`
- Modify if layout reveals a defect: `apps/web/src/app/globals.css`
- Modify if structure reveals a defect: `apps/web/src/app/(workspace)/dashboard/page.tsx`
- Modify: `docs/screenshots/dashboard.png`
- Verify: `docs/screenshots/mobile-dashboard.png`

**Interfaces:**
- Consumes: the finished dashboard route and styles from Tasks 1–3.
- Produces: passing repository frontend checks and browser-generated screenshots at representative desktop and mobile widths.

- [ ] **Step 1: Format and run the complete frontend verification suite**

Run:

```bash
cd apps/web
npm run format
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

Expected: every command exits successfully. Review formatter changes before staging and keep them limited to dashboard files.

- [ ] **Step 2: Run the complete browser flow and regenerate screenshots**

With the seeded API and web app active, run:

```bash
cd apps/web
npm run test:e2e
```

Expected: all browser tests PASS; `docs/screenshots/dashboard.png` and `docs/screenshots/mobile-dashboard.png` are regenerated from the running application.

- [ ] **Step 3: Inspect the dashboard at all required widths**

Use browser responsive mode at 375×812, 768×1024, 1024×768, and 1440×1000. At every width confirm:

- no horizontal page scrolling;
- decision cards appear in order: weekly order, stockout prevention, trapped cash;
- missing-cost copy and action remain adjacent when present;
- product names and values do not overlap;
- all visible interactive controls can be reached by keyboard and show focus;
- queue and inventory links remain at least 44px tall where practical;
- loading skeleton dimensions match the final content closely;
- the empty catalog and both zero-result queue messages are legible;
- reduced-motion mode removes shimmer and transitions.

If a defect appears, add the narrowest component assertion or Playwright assertion that reproduces it, verify the assertion fails, make the smallest correction in the relevant file, and rerun the focused test before continuing.

- [ ] **Step 4: Review the final diff for scope and accessibility**

Run:

```bash
git diff --check
git status --short
git diff --stat HEAD~3..HEAD
rg -n "emoji|transform: translate|font-size: ([0-9]|1[0-5])px" \
  apps/web/src/components/dashboard.tsx \
  'apps/web/src/app/(workspace)/dashboard/page.tsx' \
  apps/web/src/app/globals.css
```

Expected: no whitespace errors, no new icon family or emoji markup, no hover transform in the new dashboard rules, and any sub-16px text is confined to desktop-only labels rather than mobile body copy.

- [ ] **Step 5: Commit final QA adjustments and screenshots**

```bash
git add apps/web/src/components/dashboard.tsx \
  'apps/web/src/app/(workspace)/dashboard/page.tsx' \
  apps/web/src/app/globals.css \
  apps/web/tests/dashboard.test.tsx \
  apps/web/tests/e2e/smoke.spec.ts \
  docs/screenshots/dashboard.png \
  docs/screenshots/mobile-dashboard.png
git commit -m "test: verify refreshed dashboard experience"
```

If Step 4 required no corrections and the screenshots were already committed in Task 3, skip the empty commit.
