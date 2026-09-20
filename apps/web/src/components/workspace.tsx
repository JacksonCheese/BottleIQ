"use client";
import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode, FormEvent } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  Upload,
  Bell,
  Settings,
  LogOut,
  ArrowUpRight,
  Store as StoreIcon,
  Menu,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Store, User } from "@/lib/types";
import { Logo, Loading, ErrorState } from "./ui";
type WorkspaceState = {
  store: Store;
  user: User;
  stores: Store[];
  refresh: () => void;
};
const Context = createContext<WorkspaceState | null>(null);
export function useWorkspace() {
  const value = useContext(Context);
  if (!value) throw new Error("Workspace required");
  return value;
}
const nav = [
  { href: "/dashboard", name: "Overview", icon: LayoutDashboard },
  { href: "/inventory", name: "Inventory", icon: Package },
  { href: "/smart-orders", name: "Smart Orders", icon: ShoppingCart },
  { href: "/alerts", name: "Alerts", icon: Bell },
  { href: "/imports", name: "Import data", icon: Upload },
  { href: "/settings", name: "Store settings", icon: Settings },
];
export function Workspace({ children }: { children: ReactNode }) {
  const router = useRouter(),
    pathname = usePathname();
  const [user, setUser] = useState<User>();
  const [stores, setStores] = useState<Store[]>([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    let active = true;
    Promise.all([api<User>("/auth/me"), api<Store[]>("/stores")])
      .then(([u, s]) => {
        if (active) {
          setUser(u);
          setStores(s);
          setError("");
        }
      })
      .catch((e: Error) => {
        if (active) {
          if (e.message.includes("sign in")) router.replace("/login");
          else setError(e.message);
        }
      });
    return () => {
      active = false;
    };
  }, [revision, router]);
  const store = stores.find((s) => s.id === selected) || stores[0];
  if (error)
    return (
      <ErrorState message={error} retry={() => setRevision((r) => r + 1)} />
    );
  if (!user) return <Loading />;
  return (
    <div className="workspace">
      <button
        className="mobile-menu"
        aria-label="Toggle navigation"
        onClick={() => setMobile(!mobile)}
      >
        <Menu />
      </button>
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <Link href="/dashboard" className="brand">
          <Logo />
        </Link>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          {nav.map(({ href, name, icon: Icon }) => (
            <Link
              onClick={() => setMobile(false)}
              key={href}
              href={href}
              className={pathname.startsWith(href) ? "active" : ""}
            >
              <Icon size={18} />
              {name}
              {href === "/smart-orders" && <span className="nav-new">NEW</span>}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="side-note">
            <span className="live-dot" />A clearer view of your shelves.
            <p>Better orders. Healthier cash flow.</p>
          </div>
          <button
            className="profile"
            onClick={async () => {
              await api("/auth/logout", { method: "POST" });
              router.push("/");
            }}
          >
            <span className="avatar">
              {user.name
                .split(" ")
                .map((n) => n[0])
                .slice(0, 2)
                .join("")}
            </span>
            <span>
              <strong>{user.name}</strong>
              <small>{user.demo ? "Demo workspace" : user.role}</small>
            </span>
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      <div className="workspace-main">
        <header className="topbar">
          <div className="store-switch">
            <StoreIcon size={18} />
            <select
              aria-label="Current store"
              value={store?.id || ""}
              onChange={(e) => setSelected(e.target.value)}
            >
              {stores.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div className="topbar-right">
            {user.demo && (
              <span className="demo-pill">
                <span />
                SYNTHETIC DEMO DATA
              </span>
            )}
            <Link href="/imports" className="text-link">
              Update data <ArrowUpRight size={15} />
            </Link>
          </div>
        </header>
        <main className="main-content">
          {!store ? (
            <CreateStore onCreated={() => setRevision((r) => r + 1)} />
          ) : (
            <Context.Provider
              value={{
                store,
                user,
                stores,
                refresh: () => setRevision((r) => r + 1),
              }}
            >
              <div key={store.id}>{children}</div>
            </Context.Provider>
          )}
        </main>
        <footer className="app-footer">
          <span>BottleIQ · Inventory, with intention.</span>
          <span>Recommendations are estimates. Review before purchasing.</span>
        </footer>
      </div>
    </div>
  );
}
export function CreateStore({ onCreated }: { onCreated: () => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const data = new FormData(e.currentTarget);
    try {
      await api("/stores", {
        method: "POST",
        body: JSON.stringify({
          name: data.get("name"),
          timezone: data.get("timezone"),
        }),
      });
      onCreated();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel onboarding">
      <div className="eyebrow">LET’S GET YOUR STORE READY</div>
      <h1>A smarter order starts here.</h1>
      <p>Create your store, then import inventory, sales, and purchases.</p>
      <form onSubmit={submit}>
        <label>
          Store name
          <input
            name="name"
            required
            maxLength={160}
            placeholder="e.g. Cedar & Cask Downtown"
          />
        </label>
        <label>
          Store timezone
          <input name="timezone" required defaultValue="America/Los_Angeles" />
        </label>
        {error && <ErrorState message={error} />}
        <button className="button" disabled={busy}>
          {busy ? "Creating…" : "Create store"}
        </button>
      </form>
    </section>
  );
}
