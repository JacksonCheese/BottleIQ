"""Fail closed before and after a staging release; never print credentials."""

import json
import sys
from urllib.parse import urlparse
from urllib.request import urlopen

from sqlalchemy.engine import make_url

from bottleiq.config import settings
from bottleiq.migrations import check_migrations


def main() -> int:
    config = settings()
    errors = []
    if config.environment != "production":
        errors.append("ENVIRONMENT must be production for staging safeguards")
    if config.demo_enabled or not config.cookie_secure:
        errors.append("Disable demo mode and enable secure cookies")
    if urlparse(config.web_origin).scheme != "https":
        errors.append("WEB_ORIGIN must use HTTPS")
    database = make_url(config.database_url)
    if database.get_backend_name() != "postgresql":
        errors.append("Staging requires PostgreSQL")
    if database.host in ("localhost", "127.0.0.1", None):
        errors.append("DATABASE_URL must point to the managed PostgreSQL host")
    if database.query.get("sslmode") not in ("require", "verify-ca", "verify-full"):
        errors.append("DATABASE_URL must require PostgreSQL TLS (sslmode=require or stronger)")
    if not config.smtp_host or not config.smtp_from:
        errors.append("Configure SMTP_HOST and SMTP_FROM")
    if errors:
        for error in errors:
            print(f"Staging check failed: {error}", file=sys.stderr)
        return 1
    try:
        check_migrations()
    except RuntimeError as error:
        print(f"Staging check failed: {error}", file=sys.stderr)
        return 1
    try:
        with urlopen(f"{config.web_origin.rstrip('/')}/api/health", timeout=10) as response:
            health = json.load(response)
        if health.get("status") != "ok" or health.get("database") != "connected":
            raise ValueError("API health response did not report a connected database")
    except (OSError, ValueError) as error:
        print(f"Staging check failed: HTTPS health probe: {error}", file=sys.stderr)
        return 1
    print("Staging configuration, migrations, and HTTPS health probe passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
