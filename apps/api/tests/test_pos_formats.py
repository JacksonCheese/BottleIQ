"""Published POS column examples, not merchant export certification."""

from pathlib import Path

import pytest
from sqlalchemy import select

from bottleiq.models import InventorySnapshot, Product
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
