"""Published POS column examples, not merchant export certification."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from bottleiq.models import InventorySnapshot, Product, Sale
from bottleiq.services.imports import GenericCSVImporter, import_csv

FIXTURES = Path(__file__).resolve().parents[3] / "data" / "pos-schemas"


@pytest.mark.parametrize(
    ("filename", "mapping", "sku", "quantity"),
    [
        (
            "square-item-library.csv",
            {
                "sku": "SKU",
                "product_name": "Item Name",
                "quantity_on_hand": "Current quantity [Downtown]",
                "unit_cost": "Default Unit Cost",
                "retail_price": "Price",
                "vendor": "Default Vendor Name",
                "category": "Category",
            },
            "000001",
            8,
        ),
        (
            "lightspeed-r-inventory.csv",
            {
                "sku": "Custom SKU",
                "product_name": "Item",
                "quantity_on_hand": "QOH",
                "unit_cost": "Default Cost",
                "retail_price": "Default - Price",
                "vendor": "Vendor",
                "brand": "Brand",
            },
            "000002",
            5,
        ),
    ],
)
def test_published_inventory_layouts_map_safely(db, store, filename, mapping, sku, quantity):
    job = import_csv(db, store, "inventory", (FIXTURES / filename).read_bytes(), filename, mapping)
    assert (job.rows_imported, job.rows_rejected) == (1, 0)
    product = db.scalar(select(Product).where(Product.sku == sku))
    snapshot = db.scalar(
        select(InventorySnapshot).where(InventorySnapshot.product_id == product.id)
    )
    assert snapshot.quantity_on_hand == quantity
    assert product.default_vendor_id is not None


def test_shopify_orders_require_line_aware_conversion_before_import():
    with pytest.raises(ValueError, match="Map these required columns"):
        GenericCSVImporter().parse((FIXTURES / "shopify-pos-orders.csv").read_bytes(), "sales", {})


def test_square_items_detail_lines_reconcile_to_export_totals(db, store):
    filename = "square-items-detail.csv"
    job = import_csv(
        db,
        store,
        "sales",
        (FIXTURES / filename).read_bytes(),
        filename,
        {
            "date": "Date",
            "sku": "SKU",
            "product_name": "Item",
            "units_sold": "Qty",
            "revenue": "Gross Sales",
            "transaction_id": "Transaction ID",
        },
        coverage_start=date(2025, 9, 18),
        coverage_end=date(2025, 9, 18),
        expected_rows=2,
        expected_units=3,
        expected_revenue=Decimal("87.00"),
    )
    assert (job.rows_imported, job.rows_rejected) == (2, 0)
    assert job.reconciliation["status"] == "matched"
    sale = db.scalar(select(Sale))
    assert sale.quantity == 3
    assert sale.gross_revenue == Decimal("87.00")


def test_square_refund_event_holds_even_with_positive_quantity(db, store):
    original = (FIXTURES / "square-items-detail.csv").read_text()
    returned = original.replace("Payment,Downtown", "Refund,Downtown", 1)
    job = import_csv(
        db,
        store,
        "sales",
        returned.encode(),
        "square-refund.csv",
        {
            "date": "Date",
            "sku": "SKU",
            "product_name": "Item",
            "units_sold": "Qty",
            "revenue": "Gross Sales",
            "transaction_id": "Transaction ID",
        },
    )
    assert job.rows_rejected == 1
    assert job.reconciliation["status"] == "rejected"
    assert "refund or return" in job.error_summary[0]["message"]
