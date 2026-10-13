"use client";
import { useState } from "react";
import type { FormEvent } from "react";
import { Printer, RotateCcw } from "lucide-react";
import { useWorkspace } from "@/components/workspace";
import { PageTitle, Panel, Loading, ErrorState } from "@/components/ui";
import { useResource } from "@/lib/use-resource";
import { api, money } from "@/lib/api";
import {
  change,
  monthLabel,
  percent,
  periodLabel,
  shortDate,
} from "@/lib/progress";
import type {
  Progress,
  ProgressComparison,
  ProgressHeadline,
} from "@/lib/types";

const products = (n: number) => `${n} ${n === 1 ? "product" : "products"}`;
const cards: {
  key: keyof ProgressHeadline;
  label: string;
  hint: string;
  lowerIsBetter: boolean | null;
  format: (n: number) => string;
}[] = [
  {
    key: "inventory_value",
    label: "Cash in stock",
    hint: "Cost of everything on the shelves.",
    lowerIsBetter: null,
    format: (n) => money(n),
  },
  {
    key: "dead_value",
    label: "Dead stock",
    hint: "No sales in 90 days.",
    lowerIsBetter: true,
    format: (n) => money(n),
  },
  {
    key: "slow_value",
    label: "Slow stock",
    hint: "More than 90 days of supply.",
    lowerIsBetter: true,
    format: (n) => money(n),
  },
  {
    key: "stockout_risks",
    label: "Running out soon",
    hint: "At or below their reorder point.",
    lowerIsBetter: true,
    format: products,
  },
];

export default function Page() {
  const { store, user } = useWorkspace();
  const path = `/progress?store_id=${store.id}`;
  const { data, error, reload } = useResource<Progress>(path);
  const [startOn, setStartOn] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const canEdit = user.role !== "viewer";
  async function act(request: () => Promise<unknown>) {
    setBusy(true);
    setActionError("");
    try {
      await request();
      reload();
    } catch (e) {
      setActionError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return <Loading />;
  const baseline = data.baseline;
  if (!baseline) {
    const start = (e: FormEvent) => {
      e.preventDefault();
      act(() =>
        api("/progress", {
          method: "POST",
          body: JSON.stringify({
            store_id: store.id,
            started_on: startOn || data.today,
          }),
        }),
      );
    };
    return (
      <>
        <PageTitle eyebrow="SINCE YOU STARTED" title="Track your progress.">
          Save this store’s numbers as a starting point, then see what changes
          as you use BottleIQ.
        </PageTitle>
        <Panel
          title="Start tracking"
          subtitle="Your starting numbers are saved and never recalculated."
        >
          <form className="padded progress-start" onSubmit={start}>
            <label>
              Start date
              <input
                type="date"
                value={startOn || data.today}
                max={data.today}
                onChange={(e) => setStartOn(e.target.value)}
              />
            </label>
            <p className="muted-copy">
              Use the day you started working with this store. It needs an
              inventory count dated on or before that day. Import 12 months of
              sales to compare each month with the same month last year.
            </p>
            <button className="button" disabled={busy || !canEdit}>
              {busy ? "Saving starting numbers…" : "Start tracking"}
            </button>
            {!canEdit && (
              <p className="muted-copy">
                Ask an owner or admin to start tracking.
              </p>
            )}
            {actionError && <ErrorState message={actionError} />}
          </form>
        </Panel>
      </>
    );
  }
  const restart = () => {
    if (
      window.confirm(
        "Restart tracking? The saved starting numbers for this store will be deleted.",
      )
    )
      act(() => api(path, { method: "DELETE" }));
  };
  const uncosted = data.months.reduce((t, m) => t + m.revenue_without_cost, 0);
  const startMonth = baseline.started_on.slice(0, 7);
  return (
    <>
      <PageTitle
        eyebrow="SINCE YOU STARTED"
        title="Your progress."
        action={
          <div className="progress-actions no-print">
            <button
              className="button secondary small"
              onClick={() => window.print()}
            >
              <Printer size={15} />
              Print report
            </button>
            {canEdit && (
              <button
                className="button secondary small"
                disabled={busy}
                onClick={restart}
              >
                <RotateCcw size={15} />
                Restart tracking
              </button>
            )}
          </div>
        }
      >
        {store.name} · tracking since {shortDate(baseline.started_on)} (
        {data.comparison?.days_tracked ?? 0} days).
      </PageTitle>
      {actionError && <ErrorState message={actionError} />}
      <div className="progress-cards">
        {cards.map((card) => {
          const before = Number(baseline.metrics[card.key] ?? 0);
          const now = Number(data.current[card.key] ?? 0);
          const d = change(before, now, card.lowerIsBetter);
          return (
            <article className="panel progress-card" key={card.key}>
              <div className="eyebrow">{card.label}</div>
              <div className="progress-values">
                <div>
                  <small>Day 1</small>
                  <strong>{card.format(before)}</strong>
                </div>
                <div>
                  <small>Now</small>
                  <strong>{card.format(now)}</strong>
                </div>
              </div>
              <p className={`progress-change ${d.tone}`}>
                {d.delta === 0
                  ? "No change"
                  : `${d.delta > 0 ? "Up" : "Down"} ${card.format(Math.abs(d.delta))}${
                      d.percent === null
                        ? ""
                        : ` (${Math.abs(Math.round(d.percent * 100))}%)`
                    }`}
              </p>
              <small className="muted-copy">{card.hint}</small>
            </article>
          );
        })}
      </div>
      <div className="progress-panels">
        {data.comparison && <Comparison comparison={data.comparison} />}
        <Panel
          title="Month by month"
          subtitle="Revenue and estimated gross profit, with the same month last year when history allows."
        >
          {data.months.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Revenue</th>
                    <th>Est. gross profit</th>
                    <th>Profit same month last year</th>
                    <th>Change</th>
                  </tr>
                </thead>
                <tbody>
                  {data.months.map((m) => {
                    const d = m.last_year
                      ? change(m.last_year.gross_profit, m.gross_profit, false)
                      : null;
                    return (
                      <tr key={m.month}>
                        <td>
                          {monthLabel(m.month)}
                          {m.month_to_date && " (to date)"}
                          {m.month >= startMonth && (
                            <span className="progress-tag">Tracking</span>
                          )}
                        </td>
                        <td>{money(m.revenue)}</td>
                        <td>{money(m.gross_profit)}</td>
                        <td>
                          {m.last_year ? money(m.last_year.gross_profit) : "—"}
                        </td>
                        <td
                          className={`progress-change ${d?.tone ?? "neutral"}`}
                        >
                          {d?.percent == null ? "—" : percent(d.percent)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="padded muted-copy">
              No complete months of sales history yet.
            </p>
          )}
        </Panel>
        <p className="notice">
          Gross profit is estimated from each product’s latest known cost.
          {uncosted > 0 &&
            ` ${money(uncosted)} of revenue in the monthly table comes from products without a cost and is left out of profit.`}{" "}
          These numbers show what changed since tracking began. Seasons, prices,
          promotions and other decisions also affect them.
        </p>
      </div>
    </>
  );
}

function Comparison({ comparison: c }: { comparison: ProgressComparison }) {
  if (
    c.kind === "too_early" ||
    c.kind === "no_history" ||
    !c.since ||
    !c.before
  )
    return (
      <Panel title="Sales since you started">
        <p className="padded muted-copy">
          {c.kind === "no_history"
            ? "There are no sales before the start date to compare with. Import earlier sales history to see a before-and-after comparison."
            : `Sales comparisons appear after 7 full days of tracking. ${Math.max(0, 7 - c.days_tracked)} more to go.`}
        </p>
      </Panel>
    );
  const sameDates = c.kind === "year_over_year";
  const { since, before } = c;
  return (
    <Panel
      title={
        sameDates
          ? "Since you started vs. the same dates last year"
          : "Average 30 days: before vs. since you started"
      }
    >
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th />
              <th>{sameDates ? "Same dates last year" : "Before tracking"}</th>
              <th>Since you started</th>
              <th>Change</th>
            </tr>
          </thead>
          <tbody>
            {(
              [
                ["Revenue", "revenue"],
                ["Estimated gross profit", "gross_profit"],
              ] as const
            ).map(([label, key]) => {
              const d = change(before[key], since[key], false);
              return (
                <tr key={key}>
                  <td>{label}</td>
                  <td>{money(before[key])}</td>
                  <td>{money(since[key])}</td>
                  <td className={`progress-change ${d.tone}`}>
                    {d.percent === null ? "—" : percent(d.percent)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="notice">
        {sameDates
          ? `${periodLabel(since.start, since.end)} compared with ${periodLabel(before.start, before.end)}.`
          : `Per-30-day averages for ${periodLabel(before.start, before.end)} (before tracking) and ${periodLabel(since.start, since.end)} (since). Seasons and holidays can explain part of any change.`}
      </p>
    </Panel>
  );
}
