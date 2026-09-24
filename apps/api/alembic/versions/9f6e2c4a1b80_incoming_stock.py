"""Track confirmed incoming stock separately from received inventory."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9f6e2c4a1b80"
down_revision: str | None = "8939170ed5ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "incoming_stock",
        sa.Column("store_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("quantity_units", sa.Integer(), nullable=False),
        sa.Column("expected_at", sa.Date(), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.CheckConstraint("quantity_units > 0"),
        sa.CheckConstraint("status IN ('open', 'resolved')"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["product_id", "organization_id"], ["products.id", "products.organization_id"]
        ),
        sa.ForeignKeyConstraint(
            ["store_id", "organization_id"], ["stores.id", "stores.organization_id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incoming_stock_organization_id", "incoming_stock", ["organization_id"])
    op.create_index("ix_incoming_stock_store_product", "incoming_stock", ["store_id", "product_id"])


def downgrade() -> None:
    op.drop_index("ix_incoming_stock_store_product", table_name="incoming_stock")
    op.drop_index("ix_incoming_stock_organization_id", table_name="incoming_stock")
    op.drop_table("incoming_stock")
