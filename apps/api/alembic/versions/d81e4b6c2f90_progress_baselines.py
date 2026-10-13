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
