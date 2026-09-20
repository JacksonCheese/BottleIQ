import Link from "next/link";
import { ArrowUpRight, AlertCircle, Wine } from "lucide-react";
import type { ReactNode } from "react";
export function Logo() {
  return (
    <span className="logo">
      <span className="logo-mark">
        <Wine size={21} />
      </span>
      Bottle<span className="logo-iq">IQ</span>
    </span>
  );
}
export function Status({ value }: { value: string }) {
  const labels: Record<string, string> = {
    stockout: "Reorder soon",
    healthy: "Healthy",
    dead: "Dead stock",
    slow: "Slow moving",
    needs_data: "Check data",
    completed: "Imported",
    partial: "Partial import",
    rejected: "Rejected",
  };
  return <span className={`badge ${value}`}>{labels[value] || value}</span>;
}
export function Loading() {
  return (
    <div className="loading" role="status">
      <span className="spinner" />
      Loading your store intelligence…
    </div>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div role="alert" className="error-state">
      <AlertCircle size={22} />
      <div>
        <strong>Something needs a second look</strong>
        <p>{message}</p>
        {retry && (
          <button className="button secondary" onClick={retry}>
            Try again
          </button>
        )}
      </div>
    </div>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Wine size={30} />
      </span>
      <h2>{title}</h2>
      <div>{children}</div>
    </div>
  );
}
export function PageTitle({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow: string;
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{children}</p>
      </div>
      {action}
    </div>
  );
}
export function Panel({
  title,
  subtitle,
  children,
  link,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  link?: { href: string; text: string };
}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {link && (
          <Link href={link.href} className="text-link">
            {link.text}
            <ArrowUpRight size={15} />
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}
