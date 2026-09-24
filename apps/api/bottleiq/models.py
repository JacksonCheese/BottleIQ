from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from bottleiq.db import Base


def uid() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(UTC)


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Tenant:
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)


class User(Identity, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))


class Organization(Identity, Base):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(160))


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(12), default="owner")
    __table_args__ = (CheckConstraint("role IN ('owner','admin','viewer')"),)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Store(Identity, Tenant, Base):
    __tablename__ = "stores"
    name: Mapped[str] = mapped_column(String(160))
    timezone: Mapped[str] = mapped_column(String(80), default="America/Los_Angeles")
    address: Mapped[str | None] = mapped_column(String(255))
    __table_args__ = (UniqueConstraint("id", "organization_id"),)


class Vendor(Identity, Tenant, Base):
    __tablename__ = "vendors"
    name: Mapped[str] = mapped_column(String(160))
    vendor_code: Mapped[str | None] = mapped_column(String(60))
    default_lead_time_days: Mapped[int] = mapped_column(default=4)
    minimum_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    __table_args__ = (
        UniqueConstraint("id", "organization_id"),
        UniqueConstraint("organization_id", "name"),
        CheckConstraint("default_lead_time_days >= 0"),
    )


class Product(Identity, Tenant, Base):
    __tablename__ = "products"
    sku: Mapped[str] = mapped_column(String(80))
    upc: Mapped[str | None] = mapped_column(String(32))
    product_name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str] = mapped_column(String(120), default="")
    category: Mapped[str] = mapped_column(String(80), default="Uncategorized")
    subcategory: Mapped[str | None] = mapped_column(String(80))
    size: Mapped[str] = mapped_column(String(40), default="750 ml")
    units_per_case: Mapped[int] = mapped_column(default=12)
    default_vendor_id: Mapped[str | None] = mapped_column(String(36))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        UniqueConstraint("id", "organization_id"),
        UniqueConstraint("organization_id", "sku"),
        ForeignKeyConstraint(
            ["default_vendor_id", "organization_id"], ["vendors.id", "vendors.organization_id"]
        ),
        CheckConstraint("units_per_case > 0"),
    )


def fact_constraints(table: str) -> tuple:
    return (
        ForeignKeyConstraint(
            ["store_id", "organization_id"], ["stores.id", "stores.organization_id"]
        ),
        ForeignKeyConstraint(
            ["product_id", "organization_id"], ["products.id", "products.organization_id"]
        ),
        UniqueConstraint("store_id", "source_key"),
        Index(f"ix_{table}_store_product", "store_id", "product_id"),
    )


class Fact(Identity, Tenant):
    store_id: Mapped[str] = mapped_column(String(36))
    product_id: Mapped[str] = mapped_column(String(36))
    source_key: Mapped[str] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64))


class Sale(Fact, Base):
    __tablename__ = "sales"
    sold_at: Mapped[date] = mapped_column(Date, index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    gross_revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    transaction_id: Mapped[str | None] = mapped_column(String(100))
    __table_args__ = (
        *fact_constraints("sales"),
        CheckConstraint("quantity >= 0 AND gross_revenue >= 0"),
    )


class InventorySnapshot(Fact, Base):
    __tablename__ = "inventory_snapshots"
    snapshot_at: Mapped[date] = mapped_column(Date, index=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    retail_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    __table_args__ = (
        *fact_constraints("inventory"),
        CheckConstraint("quantity_on_hand >= 0 AND retail_price >= 0"),
        CheckConstraint("unit_cost IS NULL OR unit_cost >= 0"),
    )


class Purchase(Fact, Base):
    __tablename__ = "purchases"
    vendor_id: Mapped[str] = mapped_column(String(36))
    purchase_date: Mapped[date] = mapped_column(Date)
    quantity_units: Mapped[int] = mapped_column(Integer)
    quantity_cases: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    __table_args__ = (
        *fact_constraints("purchases"),
        ForeignKeyConstraint(
            ["vendor_id", "organization_id"], ["vendors.id", "vendors.organization_id"]
        ),
        CheckConstraint("quantity_units > 0 AND unit_cost >= 0"),
    )


class IncomingStock(Identity, Tenant, Base):
    __tablename__ = "incoming_stock"
    store_id: Mapped[str] = mapped_column(String(36))
    product_id: Mapped[str] = mapped_column(String(36))
    quantity_units: Mapped[int] = mapped_column(Integer)
    expected_at: Mapped[date] = mapped_column(Date)
    reference: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(12), default="open")
    __table_args__ = (
        ForeignKeyConstraint(
            ["store_id", "organization_id"], ["stores.id", "stores.organization_id"]
        ),
        ForeignKeyConstraint(
            ["product_id", "organization_id"], ["products.id", "products.organization_id"]
        ),
        CheckConstraint("quantity_units > 0"),
        CheckConstraint("status IN ('open', 'resolved')"),
        Index("ix_incoming_stock_store_product", "store_id", "product_id"),
    )


class StockReceipt(Identity, Tenant, Base):
    __tablename__ = "stock_receipts"
    store_id: Mapped[str] = mapped_column(String(36))
    product_id: Mapped[str] = mapped_column(String(36))
    incoming_stock_id: Mapped[str] = mapped_column(ForeignKey("incoming_stock.id"))
    recorded_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    quantity_units: Mapped[int] = mapped_column(Integer)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["store_id", "organization_id"], ["stores.id", "stores.organization_id"]
        ),
        ForeignKeyConstraint(
            ["product_id", "organization_id"], ["products.id", "products.organization_id"]
        ),
        CheckConstraint("quantity_units > 0"),
        Index("ix_stock_receipts_store_product", "store_id", "product_id"),
    )


class ImportJob(Identity, Tenant, Base):
    __tablename__ = "import_jobs"
    store_id: Mapped[str] = mapped_column(String(36))
    import_type: Mapped[str] = mapped_column(String(20))
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(24), default="processing")
    file_hash: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int] = mapped_column(default=0)
    rows_imported: Mapped[int] = mapped_column(default=0)
    rows_rejected: Mapped[int] = mapped_column(default=0)
    rows_duplicate: Mapped[int] = mapped_column(default=0)
    error_summary: Mapped[list[dict]] = mapped_column(JSON, default=list)
    __table_args__ = (
        ForeignKeyConstraint(
            ["store_id", "organization_id"], ["stores.id", "stores.organization_id"]
        ),
        UniqueConstraint("store_id", "import_type", "file_hash"),
    )


class ReorderRecommendation(Identity, Tenant, Base):
    __tablename__ = "reorder_recommendations"
    store_id: Mapped[str] = mapped_column(String(36))
    product_id: Mapped[str] = mapped_column(String(36))
    vendor_id: Mapped[str | None] = mapped_column(String(36))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    current_quantity: Mapped[int] = mapped_column()
    average_daily_demand: Mapped[float] = mapped_column()
    lead_time_days: Mapped[int] = mapped_column()
    safety_stock: Mapped[float] = mapped_column()
    reorder_point: Mapped[float] = mapped_column()
    target_stock: Mapped[float] = mapped_column()
    recommended_units: Mapped[int] = mapped_column()
    recommended_cases: Mapped[int] = mapped_column()
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(40))
    explanation: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(
            ["store_id", "organization_id"], ["stores.id", "stores.organization_id"]
        ),
        ForeignKeyConstraint(
            ["product_id", "organization_id"], ["products.id", "products.organization_id"]
        ),
        ForeignKeyConstraint(
            ["vendor_id", "organization_id"], ["vendors.id", "vendors.organization_id"]
        ),
    )


class SmartOrder(Identity, Tenant, Base):
    __tablename__ = "smart_orders"
    store_id: Mapped[str] = mapped_column(String(36))
    vendor_id: Mapped[str] = mapped_column(String(36))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    estimated_total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    version: Mapped[int] = mapped_column(default=1)
    __table_args__ = (
        UniqueConstraint("id", "organization_id"),
        ForeignKeyConstraint(
            ["store_id", "organization_id"], ["stores.id", "stores.organization_id"]
        ),
        ForeignKeyConstraint(
            ["vendor_id", "organization_id"], ["vendors.id", "vendors.organization_id"]
        ),
        CheckConstraint("estimated_total_cost >= 0"),
    )


class SmartOrderLine(Identity, Tenant, Base):
    __tablename__ = "smart_order_lines"
    smart_order_id: Mapped[str] = mapped_column(String(36))
    product_id: Mapped[str] = mapped_column(String(36))
    recommended_units: Mapped[int] = mapped_column()
    recommended_cases: Mapped[int] = mapped_column()
    units_per_case: Mapped[int] = mapped_column()
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    explanation: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("smart_order_id", "product_id"),
        ForeignKeyConstraint(
            ["smart_order_id", "organization_id"],
            ["smart_orders.id", "smart_orders.organization_id"],
        ),
        ForeignKeyConstraint(
            ["product_id", "organization_id"], ["products.id", "products.organization_id"]
        ),
        CheckConstraint("recommended_units >= 0 AND recommended_cases >= 0"),
    )


class SmartOrderAudit(Identity, Tenant, Base):
    __tablename__ = "smart_order_audit"
    smart_order_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    version_before: Mapped[int] = mapped_column(Integer)
    version_after: Mapped[int] = mapped_column(Integer)
    changes: Mapped[list[dict]] = mapped_column(JSON)
    __table_args__ = (
        ForeignKeyConstraint(
            ["smart_order_id", "organization_id"],
            ["smart_orders.id", "smart_orders.organization_id"],
        ),
        Index("ix_smart_order_audit_order_created", "smart_order_id", "created_at"),
    )
