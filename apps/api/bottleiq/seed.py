"""Repeatable synthetic fixture generator and idempotent demo loader."""

import argparse
import csv
import io
import math
import random
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bottleiq.auth import passwords
from bottleiq.db import SessionLocal
from bottleiq.models import (
    InventorySnapshot,
    Organization,
    OrganizationMember,
    Product,
    Store,
    User,
    Vendor,
)
from bottleiq.services.imports import import_csv

VENDORS = [
    "Pacific Coast Distributing",
    "Heritage Wine & Spirits",
    "Northstar Beverage",
    "Valley Craft Collective",
]
CATEGORIES = ["Whiskey", "Tequila", "Vodka", "Gin", "Rum", "Wine", "Beer", "Liqueur"]
BRANDS = [
    "Cedar Ridge",
    "Mesa Sol",
    "North Current",
    "Juniper & Field",
    "Harbor Lantern",
    "Valley Loom",
    "Trailhead",
    "Orchard Vale",
]
STYLES = [
    "Reserve",
    "Classic",
    "Small Batch",
    "Estate",
    "Golden",
    "Highland",
    "Coastal",
    "Founders",
    "Silver",
    "Oak",
    "Meadow",
    "Evening",
]


def sample_files(as_of: date, product_count: int = 96) -> dict[str, bytes]:
    rng = random.Random(42)
    data: dict[str, list[list]] = {"inventory": [], "sales": [], "purchases": []}
    for i in range(product_count):
        sku = f"BTL-{i + 1:04d}"
        category = CATEGORIES[i % 8]
        brand = BRANDS[i % 8]
        name = f"{brand} {STYLES[i // 8]} {category}"
        vendor = VENDORS[i % 4]
        pack = 6 if category in ("Whiskey", "Tequila", "Wine") else 12
        cost = round(8 + (i * 7 % 32) + rng.random(), 2)
        price = round(cost * 1.48, 2)
        base = 4.0 if i < 16 else 1.6 if i < 56 else 0.25 if i < 80 else 0.0
        stock = 3 + i % 5 if i < 16 else int(base * 32) if i < 56 else 150 + i % 40
        if i == 0:
            base, stock, cost, price, pack = 4.0, 8, 18.0, 29.0, 12
        if i == 20:
            base, stock, cost, price, pack = 2.0, 70, 14.0, 23.0, 12
        for offset in range(210, 0, -1):
            day = as_of - timedelta(days=offset)
            season = 1 + 0.3 * math.sin(day.timetuple().tm_yday / 365 * 2 * math.pi)
            weekend = 1.4 if day.weekday() in (4, 5) else 0.85
            qty = (
                max(0, round(rng.gauss(base * season * weekend, max(0.4, base * 0.45))))
                if base
                else 0
            )
            if i == 0:
                qty = 4
            if i == 20:
                qty = 2
            if i == 30 and offset <= 7:
                qty = 9
            if i >= 80:
                qty = 1 if offset > 110 and offset % 17 == 0 else 0
            # Include explicit zero days to establish continuous coverage.
            data["sales"].append([day, sku, name, qty, f"{qty * price:.2f}", f"{price:.2f}"])
        data["inventory"].append(
            [
                sku,
                name,
                stock,
                "" if i == 79 else f"{cost:.2f}",
                f"{price:.2f}",
                as_of,
                category,
                brand,
                "750 ml" if category != "Beer" else "6 × 355 ml",
                pack,
                vendor,
                f"000001{i:06d}",
            ]
        )
        for offset in (190, 160, 130, 100, 70, 40, 10):
            if i >= 80 and offset < 110:
                continue
            day = as_of - timedelta(days=offset)
            qty = pack * (10 if i < 56 else 2)
            data["purchases"].append(
                [day, vendor, sku, qty, f"{cost:.2f}", f"INV-{offset}-{i // 4}", name]
            )
    headers = {
        "sales": ["date", "sku", "product_name", "units_sold", "revenue", "unit_price"],
        "inventory": [
            "sku",
            "product_name",
            "quantity_on_hand",
            "unit_cost",
            "retail_price",
            "snapshot_at",
            "category",
            "brand",
            "size",
            "units_per_case",
            "vendor",
            "upc",
        ],
        "purchases": [
            "purchase_date",
            "vendor",
            "sku",
            "quantity",
            "unit_cost",
            "invoice_number",
            "product_name",
        ],
    }
    result = {}
    for kind, rows in data.items():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers[kind])
        writer.writerows(rows)
        result[kind] = output.getvalue().encode()
    return result


def seed_demo(db: Session, as_of: date | None = None, product_count: int = 96) -> Store:
    existing = db.scalar(select(User).where(User.email == "demo@bottleiq.local"))
    if existing:
        member = db.scalar(
            select(OrganizationMember).where(OrganizationMember.user_id == existing.id)
        )
        store = (
            db.scalar(select(Store).where(Store.organization_id == member.organization_id))
            if member
            else None
        )
        if not store:
            raise ValueError("Demo account is incomplete")
        # Resume partial seeds at their original date; repeated seeds never rewrite history.
        as_of = as_of or db.scalar(
            select(func.max(InventorySnapshot.snapshot_at)).where(
                InventorySnapshot.store_id == store.id
            )
        )
    else:
        org = Organization(name="BottleIQ Demo · Cedar & Cask")
        user = User(
            email="demo@bottleiq.local",
            name="Alex Morgan",
            password_hash=passwords.hash(secrets.token_urlsafe(32)),
        )
        db.add_all([org, user])
        db.flush()
        db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="owner"))
        store = Store(organization_id=org.id, name="Cedar & Cask · Downtown")
        db.add(store)
        db.flush()
        for i, name in enumerate(VENDORS):
            db.add(
                Vendor(
                    organization_id=org.id,
                    name=name,
                    default_lead_time_days=[4, 5, 3, 2][i],
                    minimum_order_amount=[500, 400, 250, 150][i],
                )
            )
        db.commit()
    seed_date = as_of or datetime.now(ZoneInfo(store.timezone)).date()
    for kind, content in sample_files(seed_date, product_count).items():
        job = import_csv(db, store, kind, content, f"demo-{kind}.csv")
        if job.rows_rejected:
            raise ValueError(f"Demo {kind} rejected rows: {job.error_summary[:3]}")
    # A missing-vendor example that owners can resolve in product settings.
    product = db.scalar(
        select(Product).where(
            Product.organization_id == store.organization_id, Product.sku == "BTL-0079"
        )
    )
    if product:
        product.default_vendor_id = None
        db.commit()
    return store


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=Path)
    args = parser.parse_args()
    if args.samples:
        args.samples.mkdir(parents=True, exist_ok=True)
        for name, content in sample_files(date.today()).items():
            (args.samples / f"{name}.csv").write_bytes(content)
        print(f"Synthetic CSV files written to {args.samples}")
    else:
        with SessionLocal() as db:
            store = seed_demo(db)
            print(f"Demo ready: {store.name}. Open the app and select Try the Demo.")


if __name__ == "__main__":
    main()
