"""CSV adapter boundary. Files live only in bounded memory; rejected values are not stored."""

import csv
import hashlib
import io
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import PurePath
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bottleiq.models import ImportJob, InventorySnapshot, Product, Purchase, Sale, Store, Vendor

FIELDS = {
    "sales": ["date", "sku", "product_name", "units_sold", "revenue", "unit_price"],
    "inventory": ["sku", "product_name", "quantity_on_hand", "unit_cost", "retail_price"],
    "purchases": ["purchase_date", "vendor", "sku", "quantity", "unit_cost", "invoice_number"],
}
OPTIONAL = [
    "snapshot_at",
    "category",
    "brand",
    "size",
    "units_per_case",
    "upc",
    "vendor",
    "transaction_id",
    "line_id",
    "product_name",
]


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def number(value: str, field: str, integer: bool = False, nullable: bool = False) -> Decimal | None:
    if not value.strip() and nullable:
        return None
    try:
        parsed = Decimal(value.strip().replace(",", "").removeprefix("$"))
    except InvalidOperation as exc:
        raise ValueError(f"{field}: expected a nonnegative number") from exc
    if not parsed.is_finite() or parsed < 0 or parsed > 10000000:
        raise ValueError(f"{field}: must be finite and between 0 and 10,000,000")
    if integer and parsed != parsed.to_integral_value():
        raise ValueError(f"{field}: fractional bottles are not supported")
    if not integer and parsed.as_tuple().exponent < -2:  # type: ignore[operator]
        raise ValueError(f"{field}: use at most 2 decimal places")
    return parsed


def parse_date(value: str, field: str, today: date) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}: use YYYY-MM-DD") from exc
    if parsed > today:
        raise ValueError(f"{field}: future dates are not supported")
    return parsed


def required(row: dict[str, str], key: str, limit: int = 200) -> str:
    value = row.get(key, "").strip()
    if not value or len(value) > limit:
        raise ValueError(f"{key}: required, maximum {limit} characters")
    return value


class BaseImporter(ABC):
    @abstractmethod
    def parse(self, content: bytes, kind: str, mapping: dict[str, str]) -> list[dict[str, str]]:
        """Return canonical records; future POS adapters implement this boundary."""


class GenericCSVImporter(BaseImporter):
    def parse(self, content: bytes, kind: str, mapping: dict[str, str]) -> list[dict[str, str]]:
        if kind not in FIELDS:
            raise ValueError("Import type must be sales, inventory, or purchases")
        if b"\x00" in content:
            raise ValueError("Binary files are not CSV files")
        try:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")), strict=True)
            headers = reader.fieldnames
            if not headers or len(set(headers)) != len(headers):
                raise ValueError("CSV must have unique column headers")
            if len(headers) > 80:
                raise ValueError("CSV has too many columns (maximum 80)")
            missing = [key for key in FIELDS[kind] if mapping.get(key, key) not in headers]
            if missing:
                raise ValueError("Map these required columns: " + ", ".join(missing))
            rows = []
            for raw in reader:
                if None in raw or any(v is None for v in raw.values()):
                    raise ValueError(
                        f"Row {reader.line_num}: column count does not match the header"
                    )
                row = {
                    key: raw.get(mapping.get(key, key), "").strip()
                    for key in set(FIELDS[kind] + OPTIONAL)
                }
                if any(len(value) > 2000 for value in row.values()):
                    raise ValueError(f"Row {reader.line_num}: field exceeds 2,000 characters")
                rows.append(row)
                if len(rows) > 100000:
                    raise ValueError("CSV exceeds 100,000 rows; split the export")
            if not rows:
                raise ValueError("CSV contains no data rows")
            return rows
        except (UnicodeDecodeError, csv.Error) as exc:
            raise ValueError("Upload a valid UTF-8 CSV file") from exc


@dataclass
class ImportCache:
    products: dict[str, Product]
    vendors: dict[str, Vendor]
    existing: dict[str, str]


def cache_for(db: Session, store: Store, kind: str) -> ImportCache:
    model = {"sales": Sale, "inventory": InventorySnapshot, "purchases": Purchase}[kind]
    return ImportCache(
        {
            p.sku: p
            for p in db.scalars(
                select(Product).where(Product.organization_id == store.organization_id)
            )
        },
        {
            v.name: v
            for v in db.scalars(
                select(Vendor).where(Vendor.organization_id == store.organization_id)
            )
        },
        dict(
            db.execute(
                select(model.source_key, model.content_hash).where(
                    model.store_id == store.id, model.organization_id == store.organization_id
                )
            ).all()
        ),
    )


def import_csv(
    db: Session,
    store: Store,
    kind: str,
    content: bytes,
    filename: str,
    mapping: dict[str, str] | None = None,
) -> ImportJob:
    mapping = mapping or {}
    rows = GenericCSVImporter().parse(content, kind, mapping)
    file_hash = digest([hashlib.sha256(content).hexdigest(), mapping])
    existing = db.scalar(
        select(ImportJob).where(
            ImportJob.store_id == store.id,
            ImportJob.import_type == kind,
            ImportJob.file_hash == file_hash,
        )
    )
    if existing:
        return existing
    job = ImportJob(
        organization_id=store.organization_id,
        store_id=store.id,
        import_type=kind,
        filename=PurePath(filename).name[:255],
        file_hash=file_hash,
        row_count=len(rows),
        rows_imported=0,
        rows_rejected=0,
        rows_duplicate=0,
        error_summary=[],
    )
    db.add(job)
    db.flush()
    errors = []
    cache = cache_for(db, store, kind)
    imported, duplicate, rejected = 0, 0, 0
    today = datetime.now(ZoneInfo(store.timezone)).date()
    for index, row in enumerate(rows, start=2):
        try:
            with db.begin_nested():
                outcome = import_row(db, store, kind, row, today, cache)
            if outcome:
                imported += 1
            else:
                duplicate += 1
        except (ValueError, IntegrityError) as exc:
            rejected += 1
            errors.append(
                {
                    "row": index,
                    "message": str(exc)
                    if isinstance(exc, ValueError)
                    else "Conflicting or invalid record; check identifiers and duplicates",
                }
            )
    job.rows_imported, job.rows_duplicate, job.rows_rejected = imported, duplicate, rejected
    job.error_summary = errors
    job.status = (
        "completed"
        if not errors
        else "partial"
        if job.rows_imported or job.rows_duplicate
        else "rejected"
    )
    db.commit()
    return job


def import_row(
    db: Session, store: Store, kind: str, row: dict[str, str], today: date, cache: ImportCache
) -> bool:
    sku = required(row, "sku", 80)
    org = store.organization_id
    product = cache.products.get(sku)
    if product is None:
        product = Product(
            organization_id=org,
            sku=sku,
            product_name=row.get("product_name") or sku,
            category=row.get("category") or "Uncategorized",
            brand=row.get("brand") or "",
            size=row.get("size") or "750 ml",
            upc=row.get("upc") or None,
            units_per_case=int(
                number(row.get("units_per_case") or "12", "units_per_case", integer=True) or 0
            ),
        )
        if not 1 <= product.units_per_case <= 1000:
            raise ValueError("units_per_case: must be between 1 and 1000")
        db.add(product)
        db.flush()
    vendor = None
    if row.get("vendor"):
        name = required(row, "vendor", 160)
        vendor = cache.vendors.get(name)
        if vendor is None:
            vendor = Vendor(organization_id=org, name=name)
            db.add(vendor)
            db.flush()
        if not product.default_vendor_id:
            product.default_vendor_id = vendor.id
    values: dict = {"organization_id": org, "store_id": store.id, "product_id": product.id}
    model: type[Sale] | type[InventorySnapshot] | type[Purchase]
    if kind == "sales":
        day = parse_date(required(row, "date"), "date", today)
        quantity = number(row["units_sold"], "units_sold", integer=True)
        values.update(
            sold_at=day,
            quantity=int(quantity or 0),
            gross_revenue=number(row["revenue"], "revenue"),
            unit_price=number(row["unit_price"], "unit_price"),
            transaction_id=row.get("transaction_id") or None,
        )
        key = [sku, day, row.get("transaction_id", ""), row.get("line_id", "")]
        model = Sale
    elif kind == "inventory":
        day = parse_date(row.get("snapshot_at") or today.isoformat(), "snapshot_at", today)
        values.update(
            snapshot_at=day,
            quantity_on_hand=int(
                number(row["quantity_on_hand"], "quantity_on_hand", integer=True) or 0
            ),
            unit_cost=number(row["unit_cost"], "unit_cost", nullable=True),
            retail_price=number(row["retail_price"], "retail_price"),
        )
        key = [sku, day]
        model = InventorySnapshot
    else:
        if not vendor:
            raise ValueError("vendor: required")
        day = parse_date(required(row, "purchase_date"), "purchase_date", today)
        quantity = number(row["quantity"], "quantity", integer=True) or Decimal(0)
        if quantity <= 0:
            raise ValueError("quantity: must be positive")
        cost = number(row["unit_cost"], "unit_cost") or Decimal(0)
        invoice = required(row, "invoice_number", 100)
        values.update(
            purchase_date=day,
            vendor_id=vendor.id,
            quantity_units=int(quantity),
            unit_cost=cost,
            total_cost=quantity * cost,
            invoice_number=invoice,
        )
        key = [sku, day, vendor.id, invoice, row.get("line_id", "")]
        model = Purchase
    source_key, content_hash = digest(key), digest(values)
    existing = cache.existing.get(source_key)
    if existing:
        if existing != content_hash:
            raise ValueError(
                "An existing record has the same identity but different values. Correct the source or use distinct transaction/line IDs; existing records were preserved."
            )
        return False
    db.add(model(**values, source_key=source_key, content_hash=content_hash))
    db.flush()
    cache.products[sku] = product
    if vendor:
        cache.vendors[vendor.name] = vendor
    cache.existing[source_key] = content_hash
    return True
