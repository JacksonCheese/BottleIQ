"""Record who changed draft order quantities."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c7d43f8a9e21"
down_revision: str | None = "6ad3f0c9e217"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "smart_order_audit",
        sa.Column("smart_order_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("version_before", sa.Integer(), nullable=False),
        sa.Column("version_after", sa.Integer(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["smart_order_id", "organization_id"],
            ["smart_orders.id", "smart_orders.organization_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_smart_order_audit_organization_id", "smart_order_audit", ["organization_id"]
    )
    op.create_index(
        "ix_smart_order_audit_order_created", "smart_order_audit", ["smart_order_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_smart_order_audit_order_created", table_name="smart_order_audit")
    op.drop_index("ix_smart_order_audit_organization_id", table_name="smart_order_audit")
    op.drop_table("smart_order_audit")
