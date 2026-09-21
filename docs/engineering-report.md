# BottleIQ MVP — engineering report

Verified September 20, 2026. This is a working repository and locally running application, not a mockup. The verification dataset is synthetic.

## Build status

Implemented end to end:

- Next.js 16.3.5 / React 19.3 App Router frontend, responsive owner-focused dashboard, landing page, signup/login/logout, and protected workspace.
- FastAPI / Pydantic API with documented OpenAPI responses; SQLAlchemy relational schema and explicit Alembic migration.
- PostgreSQL organization isolation, composite tenant foreign keys, roles, password/session authentication, CSRF checks, request limits, structured logging, and health checks.
- Store creation/switching and configurable product case packs, categories, brands, distributors, lead times, and minimums.
- Inventory, sales, and purchase CSV ingestion with preview/mapping, numeric/date validation, row rejection reports, file/row deduplication, and conflict preservation.
- Polars/NumPy inventory analytics, 30/60/90-day demand, safety stock, days supply, dead/slow/stockout flags, ABC, estimated profitability metrics, and alerts.
- Persisted recommendations and distributor drafts with case rounding, explanations, case edits/exclusions, version conflict protection, totals, minimum warnings, and CSV download.
- Deterministic sample generator, repeatable/resumable seeding, local development commands, locked dependencies, tests, CI definition, documentation, screenshots, and Git commits.

No automatic supplier submission, live POS integration, external AI, accounting, or payment processing was implemented or simulated.

## Repository

Local path: `/Users/jacksonjue/Documents/ChatGPT/BottleIQ`.

Git initialized on `main`, with logical commits for scaffolding, schema, backend intelligence, frontend workflows, tests/hardening, and documentation. `.env`, dependencies, databases, and build output are ignored. The GitHub CLI is unavailable on this machine. **No remote repository was created and no push is claimed.**

After installing/authenticating GitHub CLI, from the repository root:

```bash
gh auth login
gh repo create bottleiq --private --source=. --remote=origin --push
```

Or create an empty **private** repository named `bottleiq` on GitHub and run, replacing `YOUR_GITHUB_USERNAME`:

```bash
git remote add origin git@github.com:YOUR_GITHUB_USERNAME/bottleiq.git
git branch -M main
git push -u origin main
```

## How to run

Normal fresh-clone prerequisites: Node 22+, npm 10+, Python 3.12+, uv, Docker Compose v2, and Make.

```bash
cd /path/to/BottleIQ
make setup
make db
make seed
make dev
```

Open http://localhost:3000. API docs: http://127.0.0.1:8000/docs.

On this machine, Docker is unavailable and the system Node is v19. Validation used the bundled Node v24.19 runtime and a separate local PostgreSQL 15.10 cluster on loopback port **55432**. The ignored root `.env` points to that cluster. The API and the production Next server were started successfully on ports 8000 and 3000. No existing PostgreSQL database was changed.

To restart the verified local setup while the local database is still present:

```bash
cd /Users/jacksonjue/Documents/ChatGPT/BottleIQ
export PATH="/Users/jacksonjue/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH"
make dev
```

Stop existing BottleIQ web/API processes first if they still occupy the ports. The temporary local database lives at `/tmp/bottleiq-pg-local`; it is a disposable verification database, not a deployment. If that directory remains after a restart, start it with:

```bash
/usr/local/opt/postgresql@15/bin/pg_ctl \
  -D /tmp/bottleiq-pg-local -l /tmp/bottleiq-postgres.log \
  -o '-p 55432 -h 127.0.0.1' start
```

For persistent development, use the documented Docker volume or your own PostgreSQL and update `.env`. Do not assume `/tmp` survives a reboot. The pre-existing machine npm setup also required an isolated npm installer during initial dependency installation; normal clone instructions assume the documented npm 10+ prerequisite.

## Demo

Click **Try the Demo**; no password is required. The email `demo@bottleiq.local` identifies the seeded user but has a random, undisclosed password. Demo access is gated by `DEMO_ENABLED=true`; it must be false for actual pilot hosting.

Seeded facts: 96 SKUs, eight categories, four vendors, 210 days of history, 20,160 sale rows, 96 inventory snapshots, 608 purchase lines.

Actual dashboard reconciliation:

| Metric | Verified value |
| --- | ---: |
| Total inventory value | $211,847.82 |
| Slow inventory value, excluding dead | $97,716.81 |
| Dead inventory value | $62,876.23 |
| Stockout risks | 16 products |
| Recommended reorders | 17 products |
| Estimated recommended order total | $31,942.74 |
| Products with unknown cost | 1, excluded from value totals and held from ordering |

These are synthetic fixture values, not customer results or claimed savings.

## Tests and build checks

| Check | Final result |
| --- | --- |
| PostgreSQL backend suite | **61 passed**, 87.48 seconds in the final full PostgreSQL run |
| SQLite backend suite (default developer fallback) | **61 passed**, 24.31 seconds |
| Frontend Vitest / React Testing Library | **12 passed** across two test files |
| Playwright Chromium | **3 passed**: demo edit/export; mobile navigation; signup → store → mapped CSV imports |
| Backend lint | Ruff passed |
| Backend formatting | Ruff format check passed |
| Backend types | mypy passed, 16 source files |
| Frontend lint | ESLint passed with no warnings in the final lint run |
| Frontend formatting | Prettier check passed after formatting test files |
| Frontend types | TypeScript passed |
| Frontend production build | Next.js build passed; all planned routes compiled |
| Database migration | PostgreSQL upgrade → drift check → downgrade → upgrade passed in an isolated migration database |
| Health | Live API returned `status=ok`, `database=connected` |
| Dependency audit | npm install reported **0 vulnerabilities** |
| Git hygiene | No tracked `.env`, database, dependencies, or build output; whitespace checks passed |
| GitHub Actions | Configured; not executed remotely because no GitHub repository was pushed |

The 61 backend tests are the same suite run against two database engines, not 122 distinct test cases. Total distinct automated cases: **76** (61 backend + 12 frontend + 3 browser). Tests cover average demand including zero days, standard deviation/safety stock, reorder point, case rounding, zero-demand and overstocks, ABC boundaries, dead/slow/risk flags, missing/zero cost, stale data, query coercion, CSV shape/number/date validation, column mapping, overlapping/conflicting duplicates, sales-first enrichment, resume-safe seeding, tenant scope, DB foreign keys, role checks, cookie flags/logout, CSRF, rate limits, upload limits, formula escaping, stale order versions, loading/error states, and cross-store UI state.

Upstream development-test warnings remain for Starlette's httpx/AnyIO deprecations and Vite's future native-config-loading behavior. They are not suppressed and do not fail the checks. This is not a substitute for an independent security audit or production load test.

## Smart Order verification

Defaults: 60 complete daily observations; 21 target days after replenishment lead time; 95% service level. For these deliberately easy-to-audit examples, daily demand is constant, so population σ=0 and safety stock is zero.

| SKU | On hand | Demand/day | Lead | Case pack | Reorder point | Target | Order |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BTL-0001 · Cedar Ridge Reserve Whiskey | 8 | 4 | 4 days | 12 | 16 | 100 | 8 cases / 96 units / **$1,728** |
| BTL-0021 · Harbor Lantern Small Batch Rum | 70 | 2 | 4 days | 12 | 8 | 50 | **0** |
| BTL-0081 · Cedar Ridge Meadow Whiskey | 150 | 0 | 4 days | 6 | 0 | 0 | **0**, dead stock |

1. **Fast mover:** `ADD=240/60=4`. Safety=`1.644854×0×sqrt(4)=0`. Reorder point=`4×4=16`; on hand 8 is below it. Supply=`8/4=2 days`. Target=`4×(4+21)=100`. Deficit=`100−8=92`. Cases=`ceil(92/12)=8`, units=`8×12=96`, cost=`96×$18=$1,728`. Case rounding deliberately exceeds the unrounded deficit by four units.
2. **Normally stocked:** `ADD=120/60=2`. Supply=`70/2=35 days`. Point=`2×4=8`. Target=`2×25=50`. Positive deficit=`max(0,50−70)=0`; recommendation is zero.
3. **Dead inventory:** no units sold in 90 days and 150 on hand. ADD and target are zero; days supply is undefined/null and no order is generated. Current cash tied up=`150×$24.80=$3,720`. The explanation recommends stopping purchasing and reviewing a markdown or return.

The independent SQL/standard-library verifier recomputes daily totals, σ, target, rounding, and compares them to the service output. Run `make verify`. Machine-readable evidence: [demo-verification.json](demo-verification.json). Variable-demand safety stock is separately covered by deterministic tests.

## Screens and routes implemented

- `/` — public landing page with demo CTA and product explanation.
- `/signup`, `/login` — signup and password login.
- `/dashboard` — six KPIs, attention summary, actions, category inventory chart, profit leaders, cash tied up.
- `/inventory` — search SKU/UPC/name/brand, category/vendor/status/ABC filters, sortable table, client pagination.
- `/products/[id]` — item metrics, 90-day sales chart, recommendation explanation, case pack/vendor settings.
- `/alerts` — severity filters and actionable product links.
- `/imports` — file preview, required/optional column mapping, import results, rejection reports, history.
- `/smart-orders` — demand controls, vendor groups, create/reopen/edit/exclude/save/export drafts.
- `/settings` — vendor lead times/minimums, add distributor, add store.
- `/health`, `/docs`, `/openapi.json` on the API.

Screenshots in `docs/screenshots/` were captured from the actual browser runs. Desktop and 390px-wide mobile were visually inspected.

## Known limitations

- Authentication lacks verified email, self-service recovery, MFA, invitations, and a session-management UI. The throttle is local to one process and sees the proxy IP.
- No hosted deployment, managed secrets, backup/restore drill, monitoring/on-call process, or independent security review has been performed. Docker configuration and PostgreSQL 17 CI are provided; this host's actual database verification used PostgreSQL 15.10.
- Real POS datasets were not available. Missing days are treated as zero-sales days; returns/negative quantities require source reconciliation; conflicts have no self-service undo/correction workflow.
- Snapshots are not perpetual stock, and there is no outstanding-order/receiving state. Operators must check freshness and deliveries to avoid buying twice.
- Demand uses trailing observations without lost-sales estimation, stockout censoring, product launch dates, promotion adjustments, or validated seasonal forecasting.
- COGS, turnover, and GMROI are clearly labeled estimates based on current snapshot cost and available inventory snapshots.
- Imports are synchronous and bounded. Large histories need durable jobs and bounded key caches; large catalogs need server pagination and incremental aggregates.
- Costs exclude freight/taxes/discounts and supplier availability. Minimums produce warnings rather than padding an order.
- No complete mutation audit trail, retention/deletion UI, or measured customer ROI.

## Next five development priorities

1. Validate real pilot exports and reconcile revenue/units; add explicit coverage checks, returns, and safe import corrections.
2. Deploy securely with managed auth/recovery, trusted ingress/shared rate limits, backups/restore, monitoring, and retention/audit procedures.
3. Track outstanding orders and receiving, and validate actual vendor pack sizes, lead times, minimums, and allocations.
4. Measure realized ROI from baseline stockouts, purchasing, cash tied up, and gross profit; capture owner overrides.
5. Backtest recommendations and load-test realistic catalogs; add durable imports, incremental analytics, and server pagination.

## Is this ready for 3–5 pilot liquor stores?

**Ready for supervised demonstrations and export-validation sessions; not yet ready for an unattended live-data purchasing pilot.**

Reliability has automated evidence at the seeded-store scale, including actual PostgreSQL and browser flows. The UX supports the main owner tasks without relying on mock data inside production services. Import protections and explanations are present, but no real POS export has been reconciled, and gaps/returns/corrections remain material. Recommendation math is verified; recommendation business outcomes are not. Application-level data isolation is tested, but operational security and recovery need a real deployment. Signup/import onboarding works, but vendor defaults and source assumptions need a guided checklist. No ROI has yet been demonstrated.

Within this task, the fixable blockers found during verification were resolved: the large-import duplicate lookup bottleneck, interrupted seed recovery, sales-first metadata enrichment, numeric query validation, stale order protection, missing-data purchase holds, and browser accessibility issues. Remaining blockers depend on pilot data, deployment choices and operations, or additional product workflows described above. Do not use an unreviewed Smart Order as an automatic instruction to buy.
