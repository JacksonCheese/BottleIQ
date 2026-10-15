"""Pilot import reconciliation and account recovery."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f39d6b18a4c2"
down_revision: str | None = "d81e4b6c2f90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("import_jobs", sa.Column("coverage_start", sa.Date(), nullable=True))
    op.add_column("import_jobs", sa.Column("coverage_end", sa.Date(), nullable=True))
    op.add_column(
        "import_jobs",
        sa.Column("reconciliation", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "import_jobs", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "import_jobs",
        sa.Column("resolved_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column("import_jobs", sa.Column("resolution_note", sa.String(500), nullable=True))
    op.create_table(
        "password_resets",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"])
    op.create_table(
        "auth_rate_limits",
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False),
    )
    op.create_table(
        "organization_invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("role", sa.String(12), nullable=False),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invited_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.CheckConstraint("role IN ('admin','viewer')"),
    )
    op.create_index(
        "ix_organization_invitations_organization_id",
        "organization_invitations",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_invitations_organization_id", table_name="organization_invitations"
    )
    op.drop_table("organization_invitations")
    op.drop_table("auth_rate_limits")
    op.drop_index("ix_password_resets_user_id", table_name="password_resets")
    op.drop_table("password_resets")
    op.drop_column("import_jobs", "reconciliation")
    op.drop_column("import_jobs", "resolution_note")
    op.drop_column("import_jobs", "resolved_by_user_id")
    op.drop_column("import_jobs", "resolved_at")
    op.drop_column("import_jobs", "coverage_end")
    op.drop_column("import_jobs", "coverage_start")
