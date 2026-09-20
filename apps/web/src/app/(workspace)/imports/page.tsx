"use client";
import { useState } from "react";
import Papa from "papaparse";
import { Upload, FileSpreadsheet, CheckCircle2 } from "lucide-react";
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
  sales: ["date", "sku", "product_name", "units_sold", "revenue", "unit_price"],
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
  sales: ["transaction_id", "line_id"],
  purchases: ["product_name", "line_id"],
};
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
  const jobs = useResource<ImportJob[]>(`/imports?store_id=${store.id}`);
  async function inspect(selected?: File) {
    setFile(selected);
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
    const h = parsed.data[0].map((v) => v.replace(/^\uFEFF/, ""));
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
    try {
      setResult(
        await api<ImportJob>(`/imports/${kind}`, {
          method: "POST",
          body: form,
        }),
      );
      jobs.reload();
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
            <div className="tabs">
              {Object.keys(fields).map((k) => (
                <button
                  key={k}
                  className={kind === k ? "active" : ""}
                  onClick={() => {
                    setKind(k);
                    setFile(undefined);
                    setHeaders([]);
                    setResult(undefined);
                    setError("");
                  }}
                >
                  {k[0].toUpperCase() + k.slice(1)}
                </button>
              ))}
            </div>
            <label className="dropzone">
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
                <div className="mapping-grid">
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
                    user.role === "viewer" ||
                    fields[kind].some((f) => !mapping[f])
                  }
                  onClick={submit}
                >
                  <Upload size={16} />
                  {busy ? "Validating and importing…" : "Validate & import"}
                </button>
              </>
            )}
            {error && <ErrorState message={error} />}{" "}
            {result && (
              <div className="import-result" role="status">
                <CheckCircle2 size={20} />
                <div>
                  <strong>
                    {result.rows_imported} imported · {result.rows_duplicate}{" "}
                    duplicates · {result.rows_rejected} rejected
                  </strong>
                  <p>
                    Job status: {result.status}. Re-uploading the same file
                    returns this saved result.
                  </p>
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
                totals per SKU, or unique transaction and line IDs for
                transaction exports.
              </p>
              <p>
                <strong>Purchases:</strong> quantities are individual units, not
                cases. Include a distributor and invoice number.
              </p>
              <p>
                <strong>Dates:</strong> use YYYY-MM-DD. An omitted inventory
                date means today in the store’s timezone.
              </p>
              <p>
                Identical rows are skipped. Conflicting duplicates are rejected,
                preserving existing records. Negative quantities and returns
                need source reconciliation before import.
              </p>
            </div>
          </Panel>
        </div>
      </div>
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
