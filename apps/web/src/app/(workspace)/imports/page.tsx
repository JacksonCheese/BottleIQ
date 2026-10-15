"use client";
import { useState } from "react";
import Papa from "papaparse";
import {
  Upload,
  FileSpreadsheet,
  CheckCircle2,
  TriangleAlert,
} from "lucide-react";
import { useWorkspace } from "@/components/workspace";
import { PageTitle, Panel, ErrorState, Status } from "@/components/ui";
import { api } from "@/lib/api";
import { useResource } from "@/lib/use-resource";
import type { ImportJob } from "@/lib/types";
const fields: Record<string, string[]> = {
  inventory: [
    "sku",
    "product_name",
    "quantity_on_hand",
    "unit_cost",
    "retail_price",
  ],
  sales: ["date", "sku", "product_name", "units_sold", "revenue"],
  purchases: [
    "purchase_date",
    "vendor",
    "sku",
    "quantity",
    "unit_cost",
    "invoice_number",
  ],
};
const optional: Record<string, string[]> = {
  inventory: [
    "snapshot_at",
    "category",
    "brand",
    "size",
    "units_per_case",
    "upc",
    "vendor",
  ],
  sales: ["unit_price", "transaction_id", "line_id", "event_type"],
  purchases: ["product_name", "line_id"],
};
function exampleCsv(kind: string) {
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
  const priorDay = new Date(Date.now() - 2 * 86400000)
    .toISOString()
    .slice(0, 10);
  if (kind === "inventory")
    return "sku,product_name,quantity_on_hand,unit_cost,retail_price,vendor,units_per_case\nTOUR-001,Example Whiskey,8,18,29,Example Distributor,12\n";
  if (kind === "sales")
    return `date,sku,product_name,units_sold,revenue,unit_price\n${priorDay},TOUR-001,Example Whiskey,4,116,29\n${yesterday},TOUR-001,Example Whiskey,3,87,29\n`;
  return `purchase_date,vendor,sku,quantity,unit_cost,invoice_number\n${yesterday},Example Distributor,TOUR-001,12,18,EXAMPLE-001\n`;
}
export default function Page() {
  const { store, user } = useWorkspace();
  const [kind, setKind] = useState("inventory");
  const [file, setFile] = useState<File>();
  const [headers, setHeaders] = useState<string[]>([]);
  const [preview, setPreview] = useState<string[][]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ImportJob>();
  const [samplePreview, setSamplePreview] = useState(false);
  const [coverageStart, setCoverageStart] = useState("");
  const [coverageEnd, setCoverageEnd] = useState("");
  const [sourceRows, setSourceRows] = useState("");
  const [sourceUnits, setSourceUnits] = useState("");
  const [sourceRevenue, setSourceRevenue] = useState("");
  const jobs = useResource<ImportJob[]>(`/imports?store_id=${store.id}`);
  const quality = useResource<{
    products_checked: number;
    products_held: number;
    reasons: Record<string, number>;
  }>(`/imports/quality?store_id=${store.id}`);
  async function inspect(selected?: File, example = false) {
    setFile(selected);
    setSamplePreview(example);
    setResult(undefined);
    setError("");
    setHeaders([]);
    if (!selected) return;
    if (selected.size > 10 * 1024 * 1024) {
      setError("Choose a CSV smaller than 10 MB.");
      setFile(undefined);
      return;
    }
    const text = await selected.text();
    const parsed = Papa.parse<string[]>(text, {
      preview: 5,
      skipEmptyLines: true,
    });
    if (parsed.errors.length || !parsed.data[0]?.length) {
      setError("This file could not be read as CSV. Check its format.");
      return;
    }
    const h = parsed.data[0].map((v) => v.replace(/^\uFEFF/, "").trim());
    if (h.some((value) => !value) || new Set(h).size !== h.length) {
      setError(
        "Every CSV column needs a unique name. Fix the header row and try again.",
      );
      return;
    }
    setHeaders(h);
    setPreview(parsed.data.slice(1));
    setMapping(
      Object.fromEntries(
        [...fields[kind], ...optional[kind]]
          .filter((f) => h.includes(f))
          .map((f) => [f, f]),
      ),
    );
  }
  async function submit() {
    if (!file) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    form.append("store_id", store.id);
    form.append("mapping", JSON.stringify(mapping));
    if (kind === "sales") {
      form.append("coverage_start", coverageStart);
      form.append("coverage_end", coverageEnd);
      form.append("expected_rows", sourceRows);
      form.append("expected_units", sourceUnits);
      form.append("expected_revenue", sourceRevenue);
    }
    try {
      setResult(
        await api<ImportJob>(`/imports/${kind}`, {
          method: "POST",
          body: form,
        }),
      );
      jobs.reload();
      quality.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="GOOD DATA. BETTER DECISIONS."
        title="Bring your store into focus."
      >
        Import inventory first, then sales history and distributor purchases.
      </PageTitle>
      <div className="import-layout">
        <Panel title="Import a CSV" subtitle="1. Choose your export type">
          <div className="padded">
            <div className="tabs" data-tour="import-tabs">
              {Object.keys(fields).map((k) => (
                <button
                  key={k}
                  className={kind === k ? "active" : ""}
                  data-tour-kind={k}
                  onClick={() => {
                    setKind(k);
                    setFile(undefined);
                    setHeaders([]);
                    setResult(undefined);
                    setError("");
                    setSamplePreview(false);
                  }}
                >
                  {k[0].toUpperCase() + k.slice(1)}
                </button>
              ))}
            </div>
            {user.demo && (
              <div className="import-example" data-tour="import-example">
                <button
                  type="button"
                  className="button secondary small"
                  data-tour="sample-import"
                  onClick={() =>
                    inspect(
                      new File([exampleCsv(kind)], `example-${kind}.csv`, {
                        type: "text/csv",
                      }),
                      true,
                    )
                  }
                >
                  Preview example {kind} CSV
                </button>
                <span>Practice preview only. No demo data is saved.</span>
              </div>
            )}
            <label className="dropzone" data-tour="import-upload">
              <Upload size={28} />
              <strong>{file ? file.name : "Choose your CSV export"}</strong>
              <span>UTF-8 CSV · Up to 10 MB · 100,000 rows</span>
              <input
                key={kind}
                aria-label="CSV file"
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => inspect(e.target.files?.[0])}
              />
            </label>
            {headers.length > 0 && (
              <>
                <h3>2. Match your columns</h3>
                <p className="muted-copy">
                  Select the column in your export for each BottleIQ field.
                </p>
                <div
                  className="mapping-grid"
                  data-tour="import-mapping"
                  data-tour-preview-kind={samplePreview ? kind : undefined}
                >
                  {[...fields[kind], ...optional[kind]].map((f) => (
                    <label key={f}>
                      {f.replaceAll("_", " ")}
                      {fields[kind].includes(f) ? " *" : " (optional)"}
                      <select
                        aria-label={`Map ${f}`}
                        value={mapping[f] || ""}
                        onChange={(e) =>
                          setMapping({ ...mapping, [f]: e.target.value })
                        }
                      >
                        <option value="">Select a column</option>
                        {headers.map((h) => (
                          <option key={h}>{h}</option>
                        ))}
                      </select>
                    </label>
                  ))}
                </div>
                {kind === "sales" && !samplePreview && (
                  <div className="padded guidance">
                    <h3>3. Reconcile your sales export</h3>
                    <p>
                      Enter the date range and totals shown by your POS before
                      uploading. BottleIQ holds recommendations if totals differ
                      or the last 14 completed days are not covered.
                    </p>
                    <label>
                      First day covered
                      <input
                        aria-label="First day covered"
                        type="date"
                        value={coverageStart}
                        onChange={(e) => setCoverageStart(e.target.value)}
                        required
                      />
                    </label>
                    <label>
                      Last day covered
                      <input
                        aria-label="Last day covered"
                        type="date"
                        value={coverageEnd}
                        onChange={(e) => setCoverageEnd(e.target.value)}
                        required
                      />
                    </label>
                    <label>
                      Source row count
                      <input
                        aria-label="Source row count"
                        type="number"
                        min="0"
                        value={sourceRows}
                        onChange={(e) => setSourceRows(e.target.value)}
                        required
                      />
                    </label>
                    <label>
                      Source units sold
                      <input
                        aria-label="Source units sold"
                        type="number"
                        value={sourceUnits}
                        onChange={(e) => setSourceUnits(e.target.value)}
                        required
                      />
                    </label>
                    <label>
                      Source sales revenue
                      <input
                        aria-label="Source sales revenue"
                        type="number"
                        step="0.01"
                        value={sourceRevenue}
                        onChange={(e) => setSourceRevenue(e.target.value)}
                        required
                      />
                    </label>
                  </div>
                )}
                <details>
                  <summary>Preview first {preview.length} rows</summary>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          {headers.map((h) => (
                            <th key={h}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {preview.map((row, i) => (
                          <tr key={i}>
                            {row.map((v, j) => (
                              <td key={j}>{v}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
                <button
                  className="button import-submit"
                  disabled={
                    busy ||
                    samplePreview ||
                    user.role === "viewer" ||
                    fields[kind].some((f) => !mapping[f]) ||
                    (kind === "sales" &&
                      !samplePreview &&
                      !(
                        coverageStart &&
                        coverageEnd &&
                        sourceRows &&
                        sourceUnits &&
                        sourceRevenue
                      ))
                  }
                  onClick={submit}
                >
                  <Upload size={16} />
                  {samplePreview
                    ? "Example preview — not imported"
                    : busy
                      ? "Validating and importing…"
                      : "Validate & import"}
                </button>
              </>
            )}
            {error && <ErrorState message={error} />}{" "}
            {result && (
              <div
                className={`import-result ${result.rows_rejected ? "has-errors" : ""}`}
                role="status"
              >
                {result.rows_rejected ? (
                  <TriangleAlert size={20} />
                ) : (
                  <CheckCircle2 size={20} />
                )}
                <div>
                  <strong>
                    {result.rows_imported} imported · {result.rows_duplicate}{" "}
                    duplicates · {result.rows_rejected} rejected
                  </strong>
                  <p>
                    {result.rows_rejected
                      ? result.rows_imported
                        ? "Some rows were saved. Fix the rejected rows in your CSV, then upload the corrected file."
                        : "No rows were saved. Fix the issues below in your CSV, then upload it again."
                      : result.import_type === "sales" &&
                          result.reconciliation?.status !== "matched"
                        ? "Rows were saved, but recommendations remain held until the declared coverage and source totals match."
                        : "Your data is ready. Re-uploading the same file returns this saved result."}
                  </p>
                  {result.reconciliation?.status && (
                    <p>
                      <strong>
                        Reconciliation: {result.reconciliation.status}.
                      </strong>{" "}
                      {result.reconciliation.status !== "matched" &&
                      result.import_type === "sales"
                        ? "Recommendations remain on hold until the export is complete and matches the POS totals."
                        : ""}
                    </p>
                  )}
                  {result.reconciliation?.checks && (
                    <ul>
                      {Object.entries(result.reconciliation.checks).map(
                        ([name, check]) => (
                          <li key={name}>
                            {name}: source{" "}
                            {String(check.source ?? "not provided")} · file{" "}
                            {String(check.imported_file)}
                          </li>
                        ),
                      )}
                    </ul>
                  )}
                  {result.error_summary.length > 0 && (
                    <>
                      <a
                        href={`/api/imports/${result.id}/errors`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Download full rejection report
                      </a>
                      <ul>
                        {result.error_summary.slice(0, 5).map((e) => (
                          <li key={e.row}>
                            Row {e.row}: {e.message}
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                  {result.warnings.length > 0 && (
                    <>
                      <p>
                        {result.warnings.length}{" "}
                        {result.warnings.length === 1
                          ? "row needs"
                          : "rows need"}{" "}
                        a closer look:
                      </p>
                      <ul>
                        {result.warnings.slice(0, 5).map((e) => (
                          <li key={e.row}>
                            Row {e.row}: {e.message}
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        </Panel>
        <div>
          <Panel title="A smooth first import">
            <div className="padded guidance">
              <FileSpreadsheet size={28} />
              <h3>A few things to know</h3>
              <p>
                <strong>Inventory:</strong> one row per SKU and snapshot date.
                Include case pack, category, and distributor when available.
              </p>
              <p>
                <strong>Sales:</strong> at least 90 days is best. Use daily
                totals per SKU, or a transaction export with transaction IDs.
                Repeated lines for a product in one transaction are added
                together. Unit price is optional.
              </p>
              <p>
                <strong>Purchases:</strong> quantities are individual units, not
                cases. Include a distributor and invoice number.
              </p>
              <p>
                <strong>Dates:</strong> YYYY-MM-DD or MM/DD/YYYY. An omitted
                inventory date means today in the store’s timezone.
              </p>
              <p>
                Identical rows are skipped. Conflicting duplicates are rejected,
                preserving existing records. Negative on-hand counts are
                recorded as 0 and flagged for a shelf count. Returns need source
                reconciliation before import.
              </p>
            </div>
          </Panel>
        </div>
      </div>
      <Panel
        title="Data quality and purchase holds"
        subtitle="Current checks for this store"
      >
        <div className="padded">
          {quality.error && (
            <ErrorState message={quality.error} retry={quality.reload} />
          )}
          {quality.data && (
            <>
              <p>
                <strong>
                  {quality.data.products_held} of{" "}
                  {quality.data.products_checked} products held.
                </strong>{" "}
                Review every reason before exporting an order.
              </p>
              {quality.data.products_checked === 0 ? (
                <p>
                  Import inventory and sales before reviewing recommendations.
                </p>
              ) : Object.entries(quality.data.reasons).length ? (
                <ul>
                  {Object.entries(quality.data.reasons).map(
                    ([reason, count]) => (
                      <li key={reason}>
                        {reason}: {count} products
                      </li>
                    ),
                  )}
                </ul>
              ) : (
                <p>No data-quality holds are currently reported.</p>
              )}
            </>
          )}
        </div>
      </Panel>
      <Panel
        title="Import history"
        subtitle="The latest 100 uploads for this store"
      >
        {jobs.error ? (
          <ErrorState message={jobs.error} retry={jobs.reload} />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Imported</th>
                  <th>Duplicates</th>
                  <th>Rejected</th>
                  <th>Reconciliation</th>
                  <th>Review</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {jobs.data?.map((j) => (
                  <tr key={j.id}>
                    <td>{j.filename}</td>
                    <td>{j.import_type}</td>
                    <td>
                      <Status value={j.status} />
                    </td>
                    <td>{j.rows_imported}</td>
                    <td>{j.rows_duplicate}</td>
                    <td>
                      {j.rows_rejected ? (
                        <a
                          href={`/api/imports/${j.id}/errors`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {j.rows_rejected} · report
                        </a>
                      ) : (
                        0
                      )}
                    </td>
                    <td>{j.reconciliation?.status ?? "legacy / unverified"}</td>
                    <td>
                      {j.resolved_at ? (
                        `Resolved: ${j.resolution_note}`
                      ) : user.role === "owner" &&
                        (j.rows_rejected > 0 ||
                          j.warnings.length > 0 ||
                          ["mismatch", "rejected"].includes(
                            j.reconciliation?.status ?? "",
                          )) ? (
                        <details>
                          <summary>Resolve after correction</summary>
                          <form
                            onSubmit={async (event) => {
                              event.preventDefault();
                              const form = event.currentTarget;
                              const note = new FormData(form).get("note");
                              try {
                                await api(`/imports/${j.id}/resolve`, {
                                  method: "POST",
                                  body: JSON.stringify({ note }),
                                });
                                jobs.reload();
                                quality.reload();
                              } catch (cause) {
                                setError((cause as Error).message);
                              }
                            }}
                          >
                            <label>
                              Correction or review note
                              <input
                                name="note"
                                required
                                minLength={10}
                                maxLength={500}
                              />
                            </label>
                            <button className="button secondary small">
                              Record resolution
                            </button>
                          </form>
                        </details>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>{new Date(j.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {jobs.data?.length === 0 && (
              <p className="padded">Your imports will appear here.</p>
            )}
          </div>
        )}
      </Panel>
    </>
  );
}
