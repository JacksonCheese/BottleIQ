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

export function DashboardNotice({
  missingCostCount,
}: {
  missingCostCount: number;
}) {
  const singular = missingCostCount === 1;

  return (
    <div className="dashboard-notice">
      <TriangleAlert aria-hidden="true" size={18} />
      <p role="status">
        <strong>
          {missingCostCount} {singular ? "product is" : "products are"} missing
          {singular ? " a cost" : " costs"}.
        </strong>{" "}
        {singular ? "It is" : "They are"} excluded from the suggested order
        total.
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
  const headingId = `${tone}-queue-title`;

  return (
    <section className="dashboard-queue" aria-labelledby={headingId}>
      <header>
        <div>
          <h2 id={headingId}>{title}</h2>
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
    <section
      className="dashboard-inventory-summary"
      aria-label="Inventory summary"
    >
      <div>
        <CalendarDays aria-hidden="true" size={18} />
        <span>{formatSnapshot(latestSnapshot)}</span>
      </div>
      <div>
        <span>Total inventory value</span>
        <strong>{inventoryValue}</strong>
      </div>
      <Link href="/inventory">
        View all {productCount} products
        <ArrowRight aria-hidden="true" size={16} />
      </Link>
    </section>
  );
}

export function DashboardSkeleton() {
  return (
    <div
      className="dashboard-skeleton"
      role="status"
      aria-label="Loading dashboard"
    >
      <span className="sr-only">Loading dashboard</span>
      <div className="dashboard-skeleton-title" />
      <div className="dashboard-skeleton-decisions">
        <div />
        <div />
        <div />
      </div>
      <div className="dashboard-skeleton-queues">
        <div />
        <div />
      </div>
    </div>
  );
}
