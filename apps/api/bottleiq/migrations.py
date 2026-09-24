"""Fail early when the database schema is behind the application."""

import sys
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from bottleiq.db import engine


def check_migrations(database: Engine = engine) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    expected = set(ScriptDirectory.from_config(config).get_heads())
    try:
        with database.connect() as connection:
            current = set(MigrationContext.configure(connection).get_current_heads())
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Cannot check database migrations because the database is unavailable. "
            "Check DATABASE_URL and database connectivity."
        ) from exc
    if current != expected:
        raise RuntimeError(
            "Database migrations are not current "
            f"(installed: {', '.join(sorted(current)) or 'none'}; "
            f"required: {', '.join(sorted(expected))}). "
            "Run 'make migrate' before starting BottleIQ."
        )


if __name__ == "__main__":
    try:
        check_migrations()
    except RuntimeError as exc:
        print(f"BottleIQ startup check failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    print("Database migrations are current.")
