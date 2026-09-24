# BottleIQ

**Turn liquor-store sales, inventory, and purchase data into a smarter weekly purchase order.**

BottleIQ is an inventory intelligence MVP for independent liquor stores and small chains. Upload CSV exports, see what to reorder and stop buying, find cash tied up on shelves, and build an explainable purchasing draft for each distributor. It complements your POS; it does not replace it.

## Features

- Account signup, password login, session logout, organization isolation, owner/admin/viewer enforcement.
- Store creation and switching; per-store IANA timezones.
- Inventory, sales, and invoice CSV imports with column mapping, validation, duplicate/conflict handling, import history, and rejected-row reports.
- Dashboard with inventory/slow/dead values, stockout risks, next actions, category chart, gross-profit leaders, and cash tied up.
- Searchable, filterable, sortable inventory, ABC classification, product detail and 90-day sales charts.
- Explainable demand, safety stock, reorder points, days supply, margin, turnover, GMROI, and stock alerts.
- Distributor Smart Orders with configurable demand window, target supply, service level, case rounding, editable/excluded lines, minimum-order warnings, and CSV export.
- Confirmed incoming-stock tracking by product and store, with expected dates, order references, and overdue-delivery holds.
- Product/distributor configuration, including case packs and lead times.
- Seeded synthetic demo, migrations, PostgreSQL development service, unit/integration/browser tests, and CI.

No automatic ordering, payments, live POS integrations, chatbot, or fabricated customer claims.

## Screenshots

Actual screenshots from the running seeded app:

![BottleIQ dashboard](docs/screenshots/dashboard.png)

![Editable distributor Smart Order](docs/screenshots/smart-order.png)

## Architecture

```mermaid
flowchart LR
  CSV[CSV / POS export] --> Import[Validated import layer]
  Import --> PG[(PostgreSQL)]
  PG --> Engine[Polars / NumPy analytics]
  Engine --> Recommendations[Explainable recommendations]
  Recommendations --> API[FastAPI]
  API --> Web[Next.js dashboard]
  Web --> Draft[Reviewed distributor draft]
  Draft --> Export[CSV export]
```

Next.js 16 App Router / React 19 / TypeScript / Tailwind 4 / Recharts; Python 3.12+ / FastAPI / Pydantic / SQLAlchemy 2 / Alembic / PostgreSQL. Dependencies are pinned by `package-lock.json` and `uv.lock`. Current Next.js requires modern Node; this repository targets Node 22+ and npm 10+.

See [architecture](docs/architecture.md), [data model](docs/data-model.md), and [security](docs/security.md).

## Quick Start

Prerequisites: Node **22+**, npm **10+**, Python **3.12+**, [uv](https://docs.astral.sh/uv/), Docker with Compose v2, and GNU Make (included on macOS/Linux). On Windows, use WSL2.

After cloning your repository, run from its root:

```bash
make setup                    # copies .env.example only if .env is absent; installs locked dependencies
make db                       # starts local PostgreSQL and waits for readiness
make seed                     # migrates and seeds the synthetic store
make dev                      # API + web; Ctrl-C stops both
```

Open **http://localhost:3000** and select **Try the Demo**. API docs: http://127.0.0.1:8000/docs. Health: http://127.0.0.1:8000/health.

To use an existing PostgreSQL instead of Docker, set `DATABASE_URL` in `.env`, skip `make db`, and run `make seed`. The API loads root `.env` independently of its working directory. The web defaults to `http://127.0.0.1:8000`; export `API_URL` when overriding it (`API_URL=https://private-api.example npm run dev`). Next does not automatically read the repository-root `.env`.

Separate terminals are also supported:

```bash
make api
# In another terminal:
make web
```

For actual onboarding: create an account → create a store → import inventory → import at least 90 days of sales → import purchases → verify vendor case packs/lead times → record confirmed incoming stock → review alerts → create an order draft. Inventory can also enrich SKUs imported through sales first.

## Demo Data

`make seed` generates 96 fictional products, eight categories, four distributors, 210 days / 20,160 daily sales rows, 96 inventory snapshots, and 608 invoice lines. Includes fast movers, seasonal demand, slow/dead stock, overstocks, missing cost/vendor examples, and a recent demand spike.

No demo password is required. **Try the Demo** works only when `DEMO_ENABLED=true`, and accesses the synthetic organization. Seeded account email is `demo@bottleiq.local`; its unknown random password is not a login credential. Do not upload customer data to the demo workspace.

The seed is idempotent and resumes partial imports at the original fixture date. Existing demo history is not shifted forward over time. To refresh an old disposable demo database, use `make reset-db CONFIRM=yes` (deletes **all** data in the configured database). Never run that command against a live store database. `make samples` regenerates only the checked-in CSV examples using today's date.

## CSV Formats

| Import | Required canonical columns |
| --- | --- |
| Sales | `date, sku, product_name, units_sold, revenue, unit_price` |
| Inventory | `sku, product_name, quantity_on_hand, unit_cost, retail_price` |
| Purchases | `purchase_date, vendor, sku, quantity, unit_cost, invoice_number` |

Map different headers in the UI. Use UTF-8, ISO dates, whole nonnegative units, USD prices with ≤2 decimals. Inventory cost can be blank (blocks ordering). File maximum: 10 MB / 100,000 rows. Default case pack: 12; newly discovered vendor lead time: 4 days. Review both before purchasing.

Daily sales exports need one row per date/SKU; transaction exports need stable `transaction_id` / `line_id`. Exact duplicates are skipped; conflicting identities are rejected. Purchase quantities are **units, not cases**. Uploads are processed in memory and are not retained as files. [Full import contract and correction limitations](docs/csv-imports.md).

## Analytics Definitions

- **Daily demand:** total units / complete calendar days in a trailing 30/60/90-day window, including zero days. Default 60 days.
- **Days of supply:** on hand / daily demand; null for zero demand.
- **Safety stock:** `Z × population daily demand σ × sqrt(lead days)`, default 95% service level.
- **Reorder point:** lead-time demand + safety stock.
- **Target stock:** daily demand × (lead days + target days) + safety stock; default target 21 days after lead time.
- **Order:** positive target deficit minus confirmed incoming units due within the planning window, rounded up to full cases. Weekly fill-to-target policy; the reorder point remains an on-hand risk signal.
- **Dead stock:** positive on hand, no sales for 90 days, sufficient store history.
- **Slow stock:** >90 days supply or no demand. Dashboard slow value excludes dead stock to avoid double counting.
- **GMROI:** 90-day estimated gross profit / estimated average inventory cost; explicitly an estimate using available snapshots and latest unit cost.
- **ABC:** descending 90-day revenue with cumulative 80% / 95% thresholds. Boundary-crossing product stays in the earlier class.

Missing cost/vendor, stale inventory/sales (>7 days), insufficient sales history (<14 days), or an overdue incoming delivery hold recommendations. Invoice history is stored but does not currently replace the snapshot cost basis. Incoming stock must be entered manually; drafts do not create incoming records, and promotions are not forecast. [All definitions and assumptions](docs/analytics-engine.md).

## Testing

```bash
make test          # backend pytest (SQLite by default) + Vitest/React Testing Library
make lint          # Ruff + formatting; ESLint + Prettier
make typecheck     # mypy + TypeScript
make build         # production Next.js build
make verify        # independent SQL-based check of three demo recommendations
```

To exercise PostgreSQL, create a dedicated disposable database whose name ends in `_test`:

```bash
docker compose exec db createdb -U bottleiq bottleiq_test
TEST_DATABASE_URL=postgresql+psycopg://bottleiq:bottleiq@localhost:5432/bottleiq_test make test-api
```

Tests create/drop tables only in the dedicated test database. Never supply a real customer database as `TEST_DATABASE_URL`.

With the seeded API and web running:

```bash
cd apps/web
npx playwright install chromium
npm run test:e2e
```

Browser tests cover demo → dashboard → inventory → product → order editing/export, mobile navigation, and signup → store creation → mapped CSV ingestion. They save actual screenshots to `docs/screenshots/`. CI runs PostgreSQL backend checks, frontend checks/build, and the browser flow. See [engineering report](docs/engineering-report.md) for final counts/results.

## Environment Variables

| Variable | Default / purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL SQLAlchemy URL; `.env.example` uses local Compose credentials |
| `WEB_ORIGIN` | `http://localhost:3000`; exact origin allowed for cookie mutations |
| `API_URL` | Web proxy target, `http://127.0.0.1:8000`; export in the web process for overrides |
| `ENVIRONMENT` | `development`; production enforces Secure cookies and disables demo |
| `DEMO_ENABLED` | application default false; `.env.example` opts in for local demo |
| `COOKIE_SECURE` | false locally; must be true with HTTPS in production |
| `MAX_UPLOAD_BYTES` | 10485760; keep ingress and Next proxy limits aligned |
| `TEST_DATABASE_URL` | optional dedicated PostgreSQL test database; otherwise in-memory SQLite |
| `PLAYWRIGHT_BASE_URL` | `http://localhost:3000` |

Do not commit `.env`. Compose is for local development and uses a local-only database binding. Production requires distinct credentials, HTTPS, private networking, shared rate limits, backup/restore, and recovery procedures.

## Authentication

The MVP implements local password auth rather than requiring a third-party key to clone and run. Argon2 hashes and random opaque server-side sessions are isolated in `auth.py`, making managed OIDC adoption straightforward. Cookies are HttpOnly/SameSite=Lax, sessions expire after 12 hours, and logout revokes them. UI and API enforce read-only viewers, but there is no role invitation/management interface. Password reset, verified email, MFA, and public signup protection beyond a process-local throttle are not shipped. [Deployment requirements](docs/security.md).

## Repository Structure

```text
apps/api/             FastAPI domain, services, route modules, tests, Alembic
apps/web/             Next.js App Router UI, component tests, browser tests
packages/shared/      Shared TypeScript DTOs and exported OpenAPI snapshot
data/samples/         Synthetic sales, inventory, and purchases CSVs
docs/                 Architecture, contracts, security, screenshots, report
scripts/              Dev runner and OpenAPI export
.github/workflows/    Backend, frontend, and browser CI
```

Regenerate the API snapshot with `uv run --project apps/api python scripts/export_openapi.py`. TypeScript DTOs are explicit shared contracts; they are not automatically generated clients.

## Current Limitations

This is a working MVP and pilot-validation foundation, not an unattended production service. Significant limitations include no self-service recovery/verified email; no durable import queue or undo; inferred coverage that cannot distinguish missing days from zero sales; no returns/shrink accounting; snapshot rather than perpetual inventory; estimated COGS/GMROI; no reconciliation of open orders; no deployed HTTPS/backups/monitoring or independent security audit. Inventory filtering is client-side, and analytics/caches are not yet optimized for large chains.

Current deployment and pilot-readiness assessment: [engineering report](docs/engineering-report.md).

## Roadmap

Next: validate real POS exports and corrections, secure hosted onboarding, outstanding-order/receiving state, measure pilot ROI, and validate scale/forecast accuracy. Later: POS and distributor catalog integrations, advanced forecasting, promotional demand detection, automatic purchase-order workflows with review, multi-store transfers, anomaly detection, pricing intelligence, and an AI natural-language analyst. [Prioritized roadmap](docs/roadmap.md).

## GitHub

The repository is initialized locally. If GitHub CLI is available and authenticated:

```bash
gh repo create bottleiq --private --source=. --remote=origin --push
```

Otherwise create an empty **private** `bottleiq` repository on GitHub, then run (replace `YOUR_GITHUB_USERNAME`):

```bash
git remote add origin git@github.com:YOUR_GITHUB_USERNAME/bottleiq.git
git branch -M main
git push -u origin main
```

MIT licensed. Synthetic names/data are generated for demonstration; no third-party transaction dataset is included.
