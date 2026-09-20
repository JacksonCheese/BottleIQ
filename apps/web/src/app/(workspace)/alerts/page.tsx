"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, TriangleAlert } from "lucide-react";
import { useWorkspace } from "@/components/workspace";
import { PageTitle, Loading, ErrorState, Empty } from "@/components/ui";
import { useResource } from "@/lib/use-resource";
import { money } from "@/lib/api";
import type { Alert } from "@/lib/types";
export default function Page() {
  const { store } = useWorkspace();
  const [severity, setSeverity] = useState("");
  const { data, error, reload } = useResource<Alert[]>(
    `/alerts?store_id=${store.id}`,
  );
  return (
    <>
      <PageTitle eyebrow="FOCUS WHERE IT MATTERS" title="Needs attention.">
        A practical list of risks, opportunities, and data to resolve.
      </PageTitle>
      <div className="tabs">
        {[
          ["", "All alerts"],
          ["critical", "Critical"],
          ["warning", "Warning"],
          ["info", "Insights"],
        ].map(([v, l]) => (
          <button
            key={v}
            className={severity === v ? "active" : ""}
            onClick={() => setSeverity(v)}
          >
            {l}{" "}
            <span>
              {data?.filter((a) => !v || a.severity === v).length || 0}
            </span>
          </button>
        ))}
      </div>
      {error ? (
        <ErrorState message={error} retry={reload} />
      ) : !data ? (
        <Loading />
      ) : data.filter((a) => !severity || a.severity === severity).length ? (
        <div className="alerts-list">
          {data
            .filter((a) => !severity || a.severity === severity)
            .map((a, i) => (
              <article
                className="panel alert-card"
                key={`${a.product_id}-${i}`}
              >
                <span className={`alert-symbol ${a.severity}`}>
                  <TriangleAlert size={21} />
                </span>
                <div>
                  <div className="alert-label">
                    {a.severity} · {a.title}
                  </div>
                  <h3>{a.product_name}</h3>
                  <p>
                    {a.description}. {a.recommended_action}.
                  </p>
                  {a.financial_impact !== null && (
                    <small>
                      {money(a.financial_impact)} current inventory value
                    </small>
                  )}
                </div>
                <Link
                  href={`/products/${a.product_id}`}
                  className="button secondary small"
                >
                  Review product
                  <ArrowUpRight size={15} />
                </Link>
              </article>
            ))}
        </div>
      ) : (
        <Empty title="Nothing to flag here.">
          <p>
            Alerts appear when your data identifies a risk or an opportunity.
          </p>
        </Empty>
      )}
    </>
  );
}
