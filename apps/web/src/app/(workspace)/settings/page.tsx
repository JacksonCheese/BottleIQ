"use client";
import { useState } from "react";
import { useWorkspace, CreateStore } from "@/components/workspace";
import { PageTitle, Panel, ErrorState } from "@/components/ui";
import { api, money } from "@/lib/api";
import { useResource } from "@/lib/use-resource";
import type { Vendor } from "@/lib/types";
export default function Page() {
  const { store, user, refresh } = useWorkspace();
  const vendors = useResource<Vendor[]>("/vendors");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <>
      <PageTitle eyebrow="MAKE BOTTLEIQ FIT YOUR STORE" title="Store settings.">
        {store.name} · {store.timezone} · {user.role}
      </PageTitle>
      {error && <ErrorState message={error} />}{" "}
      {saved && (
        <div className="notice" role="status">
          {saved}
        </div>
      )}
      <Panel
        title="Your distributors"
        subtitle="Lead time drives safety stock and replenishment quantities"
      >
        <div className="padded vendor-settings">
          {vendors.data?.map((v) => (
            <form
              key={v.id}
              onSubmit={async (e) => {
                e.preventDefault();
                setBusy(true);
                setError("");
                setSaved("");
                const f = new FormData(e.currentTarget);
                try {
                  await api(`/vendors/${v.id}`, {
                    method: "PATCH",
                    body: JSON.stringify({
                      name: v.name,
                      default_lead_time_days: Number(f.get("lead")),
                      minimum_order_amount:
                        f.get("minimum") === ""
                          ? null
                          : Number(f.get("minimum")),
                    }),
                  });
                  vendors.reload();
                  setSaved(`${v.name} saved.`);
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <div>
                <strong>{v.name}</strong>
                <p>
                  {v.minimum_order_amount === null
                    ? "No minimum configured"
                    : `${money(v.minimum_order_amount)} minimum`}
                </p>
              </div>
              <label>
                Lead time (days)
                <input
                  name="lead"
                  type="number"
                  min={0}
                  max={90}
                  defaultValue={v.default_lead_time_days}
                  required
                />
              </label>
              <label>
                Minimum order ($)
                <input
                  name="minimum"
                  type="number"
                  min={0}
                  max={10000000}
                  step=".01"
                  defaultValue={v.minimum_order_amount ?? ""}
                />
              </label>
              <button
                className="button secondary small"
                disabled={busy || user.role === "viewer"}
              >
                Save
              </button>
            </form>
          ))}
        </div>
        {vendors.error && (
          <ErrorState message={vendors.error} retry={vendors.reload} />
        )}
      </Panel>
      {user.role !== "viewer" && (
        <div className="dashboard-grid">
          <Panel title="Add a distributor">
            <form
              className="padded"
              onSubmit={async (e) => {
                e.preventDefault();
                const form = e.currentTarget;
                const f = new FormData(form);
                setBusy(true);
                setError("");
                try {
                  await api("/vendors", {
                    method: "POST",
                    body: JSON.stringify({
                      name: f.get("name"),
                      default_lead_time_days: Number(f.get("lead")),
                    }),
                  });
                  vendors.reload();
                  form.reset();
                  setSaved("Distributor added.");
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <label>
                Distributor name
                <input name="name" required maxLength={160} />
              </label>
              <label>
                Lead time (days)
                <input
                  name="lead"
                  type="number"
                  required
                  min={0}
                  max={90}
                  defaultValue={4}
                />
              </label>
              <button className="button" disabled={busy}>
                Add distributor
              </button>
            </form>
          </Panel>
          <CreateStore onCreated={refresh} />
        </div>
      )}
      {user.role === "owner" && !user.demo && (
        <Panel
          title="Invite a teammate"
          subtitle="Send a seven-day invitation to an admin or read-only viewer"
        >
          <form
            className="padded"
            onSubmit={async (event) => {
              event.preventDefault();
              setBusy(true);
              setError("");
              setSaved("");
              const form = event.currentTarget;
              const values = new FormData(form);
              try {
                await api("/auth/invitations", {
                  method: "POST",
                  body: JSON.stringify({
                    email: values.get("email"),
                    role: values.get("role"),
                  }),
                });
                setSaved("Invitation sent. The link expires in seven days.");
                form.reset();
              } catch (cause) {
                setError((cause as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Email
              <input name="email" type="email" required />
            </label>
            <label>
              Role
              <select name="role">
                <option value="viewer">Viewer · read only</option>
                <option value="admin">Admin · can edit data and orders</option>
              </select>
            </label>
            <button className="button" disabled={busy}>
              Send invitation
            </button>
          </form>
        </Panel>
      )}
      <div className="notice">
        Demo workspace: synthetic data only. Live store data belongs in a
        separate account with demo mode disabled on the server.
      </div>
    </>
  );
}
