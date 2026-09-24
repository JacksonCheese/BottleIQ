"""Record actual deliveries separately from inventory snapshots."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6ad3f0c9e217"
down_revision: str | None = "9f6e2c4a1b80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_receipts",
        sa.Column("store_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("incoming_stock_id", sa.String(length=36), nullable=False),
        sa.Column("recorded_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("quantity_units", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.CheckConstraint("quantity_units > 0"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["incoming_stock_id"], ["incoming_stock.id"]),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["product_id", "organization_id"], ["products.id", "products.organization_id"]
        ),
        sa.ForeignKeyConstraint(
            ["store_id", "organization_id"], ["stores.id", "stores.organization_id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_receipts_organization_id", "stock_receipts", ["organization_id"])
    op.create_index("ix_stock_receipts_store_product", "stock_receipts", ["store_id", "product_id"])


def downgrade() -> None:
    op.drop_index("ix_stock_receipts_store_product", table_name="stock_receipts")
    op.drop_index("ix_stock_receipts_organization_id", table_name="stock_receipts")
    op.drop_table("stock_receipts")
