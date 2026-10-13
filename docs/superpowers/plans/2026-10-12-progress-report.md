# Store Progress Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a printable Progress page that compares a store's frozen Day 1 baseline with its current numbers and shows monthly revenue and estimated gross profit, including year-over-year when history allows.

**Architecture:** A new `progress_baselines` table stores one frozen baseline per store, computed with the existing `analyze(..., as_of=started_on)`. A new `services/progress.py` builds the report (current headline from `analyze`, date-range sales totals for the comparison and monthly rows). A new `routes/progress.py` exposes GET/POST/DELETE. The Next.js workspace gets a `/progress` page and a nav link.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy 2, Alembic, pytest; Next.js App Router, React 19, TypeScript, Vitest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-12-progress-report-design.md`.
- Baseline is frozen at start; never recalculated.
- Headline definitions match the dashboard: slow value excludes dead value; unknown costs excluded and counted.
- Gross profit = revenue − units × latest known unit cost; revenue from products without a cost is excluded from profit and reported separately.
- Comparison windows use complete days only: `[started_on, today)`; minimum 7 days.
- Copy describes change since tracking began; never claims BottleIQ caused a gain.
- Owner/admin (`editor`) can start/restart; any member can read; `get_store` enforces tenancy.
- Commands: `make test`, `make lint`, `make typecheck`, `make format`; regenerate `packages/shared/openapi.json` with `uv run --project apps/api python scripts/export_openapi.py`.

---

### Task 1: Baseline model and migration

**Files:**
- Modify: `apps/api/bottleiq/models.py` (append class)
- Create: `apps/api/alembic/versions/d81e4b6c2f90_progress_baselines.py`
- Test: `apps/api/tests/test_progress.py`

**Interfaces:**
- Produces: `ProgressBaseline(organization_id, store_id, started_on: date, created_by_user_id, metrics: dict)`; table `progress_baselines`, unique on `store_id`.

- [ ] **Step 1: Write the failing test**

```python
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from bottleiq.models import ProgressBaseline, User
from sqlalchemy import select


def owner_id(db) -> str:
    return db.scalar(select(User.id).where(User.email == "owner@example.com"))


def test_one_baseline_per_store(db, store):
    for _ in range(2):
        db.add(
            ProgressBaseline(
                organization_id=store.organization_id,
                store_id=store.id,
                started_on=date(2026, 9, 1),
                created_by_user_id=owner_id(db),
                metrics={},
            )
        )
    with pytest.raises(IntegrityError):
        db.flush()
```

- [ ] **Step 2: Run it** — `cd apps/api && uv run pytest tests/test_progress.py -q` → FAIL (ImportError: ProgressBaseline).

- [ ] **Step 3: Add the model** (end of `models.py`)

```python
class ProgressBaseline(Identity, Tenant, Base):
    """Headline numbers frozen when a store starts tracking progress."""

    __tablename__ = "progress_baselines"
    store_id: Mapped[str] = mapped_column(String(36), unique=True)
    started_on: Mapped[date] = mapped_column(Date)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    metrics: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (
        ForeignKeyConstraint(
            ["store_id", "organization_id"], ["stores.id", "stores.organization_id"]
        ),
    )
```

- [ ] **Step 4: Add the migration** (`down_revision = "c7d43f8a9e21"`)

```python
"""Freeze a per-store baseline for progress reports."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d81e4b6c2f90"
down_revision: str | None = "c7d43f8a9e21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "progress_baselines",
        sa.Column("store_id", sa.String(length=36), nullable=False),
        sa.Column("started_on", sa.Date(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["store_id", "organization_id"], ["stores.id", "stores.organization_id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id"),
    )
    op.create_index(
        "ix_progress_baselines_organization_id", "progress_baselines", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_progress_baselines_organization_id", table_name="progress_baselines")
    op.drop_table("progress_baselines")
```

- [ ] **Step 5: Run tests and migrate a scratch DB** — `uv run pytest tests/test_progress.py -q` → PASS; `DATABASE_URL=sqlite:////tmp/bq-mig.db uv run alembic upgrade head && DATABASE_URL=sqlite:////tmp/bq-mig.db uv run alembic downgrade -1` → no errors.

- [ ] **Step 6: Commit** — `git add` model, migration, test; `git commit -m "feat: store a frozen progress baseline per store"`.

### Task 2: Progress service

**Files:**
- Create: `apps/api/bottleiq/services/progress.py`
- Test: `apps/api/tests/test_progress.py`

**Interfaces:**
- Consumes: `ProgressBaseline` (Task 1); `analyze(db, store, as_of=...) -> list[Metrics]`.
- Produces:
  - `headline(metrics: list[Metrics]) -> dict` with keys `inventory_value, dead_value, slow_value, stockout_risks, product_count, missing_cost_count, revenue_90, gross_profit_90, snapshot_at`.
  - `start_tracking(db, store, user_id: str, started_on: date | None, today: date | None = None) -> ProgressBaseline`; raises `TrackingExists`, `ValueError`.
  - `stop_tracking(db, store) -> None`.
  - `progress_report(db, store, today: date | None = None) -> dict` with keys `today, baseline, current, comparison, months`.

- [ ] **Step 1: Write failing tests** (helpers build sales/snapshots directly)

```python
def seed(db, store, *, days: int, end: date, units: int = 2, price: str = "10", cost="6"):
    product = Product(organization_id=store.organization_id, sku="001", product_name="Test")
    db.add(product)
    db.flush()
    db.add(InventorySnapshot(organization_id=store.organization_id, store_id=store.id,
        product_id=product.id, snapshot_at=end - timedelta(days=days), quantity_on_hand=40,
        unit_cost=None if cost is None else Decimal(cost), retail_price=Decimal(price),
        source_key="s0", content_hash="h"))
    for n in range(days):
        day = end - timedelta(days=days - n)
        db.add(Sale(organization_id=store.organization_id, store_id=store.id,
            product_id=product.id, sold_at=day, quantity=units,
            gross_revenue=Decimal(price) * units, unit_price=Decimal(price),
            source_key=f"k{n}", content_hash="h"))
    db.commit()
    return product
```

Tests: baseline frozen as of a past date; future date and missing count rejected; duplicate start raises `TrackingExists`; too-early comparison under 7 days; before/after per-30-day basis with seasonality; year-over-year when history reaches a year back; month rows include month-to-date and last-year values; revenue without cost excluded from profit.

- [ ] **Step 2: Run** — FAIL (module missing).

- [ ] **Step 3: Implement `services/progress.py`** — see final file in this commit; key rules:
  - `totals(db, store, start, end, costs, scale=1.0)` sums `Sale` by product for `[start, end)`; profit only where cost known.
  - `latest_costs` = latest non-null `unit_cost` per product from snapshots on or before `today`.
  - Comparison: `days = (today - started_on).days`; `< 7` → `too_early`; if first sale ≤ `started_on` minus one year → `year_over_year` (totals); else up to 90 days before start → `before_after` scaled per 30 days; no prior days → `no_history`.
  - Months: 12 calendar months ending with the current month; current month covers complete days only and is skipped on the 1st; `last_year` only when history reaches that month's start one year earlier.

- [ ] **Step 4: Run** — PASS.

- [ ] **Step 5: Commit** — `feat: build store progress report service`.

### Task 3: API routes and schemas

**Files:**
- Create: `apps/api/bottleiq/routes/progress.py`
- Modify: `apps/api/bottleiq/schemas.py`, `apps/api/bottleiq/main.py`, `packages/shared/openapi.json`, `packages/shared/types.ts`
- Test: `apps/api/tests/test_progress.py`

**Interfaces:**
- `GET /progress?store_id=` → `ProgressView`; `POST /progress` `{store_id, started_on?}` → 201 `ProgressView`; `DELETE /progress?store_id=` → 204.
- Errors: 409 duplicate, 422 validation, 403 viewer mutation, 404 other tenant.

- [ ] **Step 1: Failing route tests** — owner start/read/restart; viewer 403 on POST/DELETE but 200 on GET; 409 on second POST; 404 for another organization's store.
- [ ] **Step 2: Run** — FAIL (404 route missing).
- [ ] **Step 3: Implement** schemas (`ProgressHeadline`, `ProgressPeriod`, `ProgressComparison`, `ProgressMonth`, `ProgressBaselineView`, `ProgressView`, `ProgressStart`), router, register router, regenerate OpenAPI, add TS types.
- [ ] **Step 4: Run** `make test-api` — PASS.
- [ ] **Step 5: Commit** — `feat: expose progress report API`.

### Task 4: Progress page

**Files:**
- Create: `apps/web/src/app/(workspace)/progress/page.tsx`, `apps/web/src/lib/progress.ts`, `apps/web/tests/progress.test.ts`
- Modify: `apps/web/src/components/workspace.tsx` (nav), `apps/web/src/app/globals.css` (cards, print)

**Interfaces:**
- `change(before: number, now: number, lowerIsBetter: boolean | null) -> {delta: number; percent: number | null; tone: "good" | "bad" | "neutral"}`
- `periodLabel(start: string, end: string) -> string`

- [ ] **Step 1: Failing Vitest** for `change` (tones, zero baseline → null percent) and `periodLabel`.
- [ ] **Step 2: Run** `npm test` — FAIL.
- [ ] **Step 3: Implement** helpers, page (not-started form, report with cards, comparison panel, monthly table, footnotes, print/restart), nav link, CSS including `@media print`.
- [ ] **Step 4: Run** `make test-web && make typecheck && make lint` — PASS.
- [ ] **Step 5: Commit** — `feat: add printable progress page`.

### Task 5: Docs and verification

**Files:** `README.md` (features), `docs/analytics-engine.md` (progress definitions).

- [ ] Document definitions and caveats; run `make format lint typecheck test`.
- [ ] Migrate the local database, start tracking for the practice store, view and print-preview the page in the running app.
- [ ] Commit — `docs: describe progress report`.
