import pytest
from sqlalchemy import func, select

from bottleiq.models import InventorySnapshot, Product, Sale
from bottleiq.services.imports import GenericCSVImporter, import_csv, number

INVENTORY = b"sku,product_name,quantity_on_hand,unit_cost,retail_price\n001,Test whiskey,8,18,29\n"


def test_import_is_idempotent(db, store):
    one = import_csv(db, store, "inventory", INVENTORY, "inventory.csv")
    two = import_csv(db, store, "inventory", INVENTORY, "inventory.csv")
    assert one.id == two.id
    assert db.scalar(select(func.count()).select_from(InventorySnapshot)) == 1


def test_overlapping_files_skip_rows(db, store):
    import_csv(db, store, "inventory", INVENTORY, "a.csv")
    another = INVENTORY + b"002,Test gin,4,10,18\n"
    job = import_csv(db, store, "inventory", another, "b.csv")
    assert (job.rows_imported, job.rows_duplicate, job.rows_rejected) == (1, 1, 0)


def test_conflicting_duplicates_do_not_overwrite(db, store):
    import_csv(db, store, "inventory", INVENTORY, "a.csv")
    job = import_csv(db, store, "inventory", INVENTORY.replace(b",8,", b",80,"), "b.csv")
    assert job.rows_rejected == 1
    assert db.scalar(select(InventorySnapshot)).quantity_on_hand == 8


def test_invalid_rows_are_rejected_with_line_number(db, store):
    job = import_csv(db, store, "inventory", INVENTORY + b"002,Bad,NaN,10,12\n", "a.csv")
    assert (job.rows_imported, job.rows_rejected) == (1, 1)
    assert job.error_summary[0]["row"] == 3
    assert db.scalar(select(func.count()).select_from(Product)) == 1


def test_column_mapping_preserves_leading_zero_sku(db, store):
    data = b"code,title,stock,cost,price\n000001,Test wine,4,5,9\n"
    mapping = dict(
        zip(
            ["sku", "product_name", "quantity_on_hand", "unit_cost", "retail_price"],
            ["code", "title", "stock", "cost", "price"],
            strict=True,
        )
    )
    job = import_csv(db, store, "inventory", data, "mapped.csv", mapping)
    assert job.rows_imported == 1
    assert db.scalar(select(Product)).sku == "000001"


def test_missing_cost_is_nullable(db, store):
    job = import_csv(db, store, "inventory", INVENTORY.replace(b",18,", b",,"), "a.csv")
    assert job.rows_imported == 1
    assert db.scalar(select(InventorySnapshot)).unit_cost is None


@pytest.mark.parametrize(
    "content",
    [
        b"sku,sku\na,b\n",
        b"hello\nx\n",
        b"\x00notcsv",
        b"sku,product_name,quantity_on_hand,unit_cost,retail_price\n",
        b"sku,product_name,quantity_on_hand,unit_cost,retail_price\na,b,1,2\n",
    ],
)
def test_malformed_csv_rejected(content):
    with pytest.raises(ValueError):
        GenericCSVImporter().parse(content, "inventory", {})


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "10000001", "hello", "1.001"])
def test_unsafe_numbers_rejected(value):
    with pytest.raises(ValueError):
        number(value, "cost")


def test_money_currency_and_thousands():
    assert float(number("$1,200.25", "cost")) == 1200.25


def test_separate_transactions_survive_same_day(db, store):
    content = b"date,sku,product_name,units_sold,revenue,unit_price,transaction_id\n2026-01-01,001,Test,2,20,10,t1\n2026-01-01,001,Test,2,20,10,t2\n"
    job = import_csv(db, store, "sales", content, "s.csv")
    assert job.rows_imported == 2
    assert db.scalar(select(func.sum(Sale.quantity))) == 4


def test_future_date_rejected(db, store):
    content = b"date,sku,product_name,units_sold,revenue,unit_price\n2099-01-01,001,Test,2,20,10\n"
    assert import_csv(db, store, "sales", content, "s.csv").rows_rejected == 1


def test_inventory_enriches_product_imported_from_sales(db, store):
    sales = b"date,sku,product_name,units_sold,revenue,unit_price\n2026-01-01,001,Test,2,20,10\n"
    import_csv(db, store, "sales", sales, "sales.csv")
    inventory = b"sku,product_name,quantity_on_hand,unit_cost,retail_price,category,units_per_case,vendor\n001,Test Whiskey,8,18,29,Whiskey,6,Pacific\n"
    assert import_csv(db, store, "inventory", inventory, "inventory.csv").rows_imported == 1
    product = db.scalar(select(Product))
    assert product.category == "Whiskey" and product.units_per_case == 6
    assert product.default_vendor_id is not None
