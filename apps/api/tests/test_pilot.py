from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from bottleiq.auth import token_digest
from bottleiq.models import AuthSession, OrganizationMember, PasswordReset, User
from bottleiq.rate_limit import limit_auth
from bottleiq.services.analytics import analyze
from bottleiq.services.imports import import_csv


def sales_csv(today, *, returned=False):
    lines = ["date,sku,product_name,units_sold,revenue,unit_price,transaction_id"]
    for offset in range(15, 0, -1):
        day = today - timedelta(days=offset)
        lines.append(f"{day},001,Whiskey,4,116,29,t{offset}")
    if returned:
        lines.append(f"{today - timedelta(days=1)},001,Whiskey,-1,-29,29,return")
    return ("\n".join(lines) + "\n").encode()


def test_reconciliation_coverage_and_return_holds(db, store):
    today = datetime.now(ZoneInfo(store.timezone)).date()
    inventory = b"sku,product_name,quantity_on_hand,unit_cost,retail_price,vendor,units_per_case\n001,Whiskey,1,18,29,Distributor,12\n"
    import_csv(db, store, "inventory", inventory, "inventory.csv")
    assert (
        "sales coverage unverified for the last 14 completed days" in analyze(db, store)[0].blockers
    )
    data = sales_csv(today)
    matched = import_csv(
        db,
        store,
        "sales",
        data,
        "sales.csv",
        coverage_start=today - timedelta(days=15),
        coverage_end=today - timedelta(days=1),
        expected_rows=15,
        expected_units=60,
        expected_revenue=Decimal("1740"),
    )
    assert matched.reconciliation["status"] == "matched"
    assert analyze(db, store)[0].recommended_cases > 0
    mismatch = import_csv(
        db,
        store,
        "sales",
        data,
        "wrong-total.csv",
        coverage_start=today - timedelta(days=15),
        coverage_end=today - timedelta(days=1),
        expected_rows=15,
        expected_units=61,
        expected_revenue=Decimal("1740"),
    )
    assert mismatch.reconciliation["status"] == "mismatch"
    assert "sales import has unresolved errors" in analyze(db, store)[0].blockers
    returned = import_csv(
        db,
        store,
        "sales",
        sales_csv(today, returned=True),
        "returned.csv",
        coverage_start=today - timedelta(days=15),
        coverage_end=today - timedelta(days=1),
        expected_rows=16,
        expected_units=59,
        expected_revenue=Decimal("1711"),
    )
    assert returned.rows_rejected == 1
    assert returned.reconciliation["status"] == "rejected"
    assert analyze(db, store)[0].recommended_cases == 0


def test_recovery_and_invitation_flow(client, db, monkeypatch):
    import bottleiq.routes.auth as auth_routes

    sent = []
    monkeypatch.setattr(
        auth_routes,
        "settings",
        lambda: type(
            "Config", (), {"smtp_host": "smtp.test", "web_origin": "http://localhost:3000"}
        )(),
    )
    monkeypatch.setattr(
        auth_routes,
        "send_account_email",
        lambda address, subject, body: sent.append((address, subject, body)),
    )
    unknown = client.post("/auth/recovery/request", json={"email": "missing@example.com"})
    known = client.post("/auth/recovery/request", json={"email": "owner@example.com"})
    assert unknown.status_code == known.status_code == 200
    assert unknown.json() == known.json()
    assert len(sent) == 1
    reset_token = parse_qs(urlparse(sent.pop()[2].splitlines()[1]).query)["token"][0]
    reset_row = db.scalar(
        select(PasswordReset).where(PasswordReset.token_hash == token_digest(reset_token))
    )
    assert reset_row is not None
    assert (
        client.post(
            "/auth/recovery/reset", json={"token": reset_token, "password": "changed-password-123"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/auth/recovery/reset", json={"token": reset_token, "password": "another-password-123"}
        ).status_code
        == 400
    )
    assert (
        db.scalar(
            select(AuthSession).where(
                AuthSession.user_id
                == db.scalar(select(User.id).where(User.email == "owner@example.com"))
            )
        )
        is None
    )
    assert (
        client.post(
            "/auth/login", json={"email": "owner@example.com", "password": "test-password-123"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/login", json={"email": "owner@example.com", "password": "changed-password-123"}
        ).status_code
        == 200
    )
    invited = client.post(
        "/auth/invitations", json={"email": "viewer@example.com", "role": "viewer"}
    )
    assert invited.status_code == 201
    assert client.get("/auth/invitations").json()[0]["email"] == "viewer@example.com"
    invite_token = parse_qs(urlparse(sent.pop()[2].splitlines()[1]).query)["token"][0]
    assert (
        client.post(
            "/auth/invitations/accept",
            json={"token": invite_token, "name": "Viewer", "password": "viewer-password-123"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/auth/invitations/accept",
            json={"token": invite_token, "name": "Viewer", "password": "viewer-password-123"},
        ).status_code
        == 400
    )
    viewer = db.scalar(select(User).where(User.email == "viewer@example.com"))
    assert (
        db.scalar(select(OrganizationMember).where(OrganizationMember.user_id == viewer.id)).role
        == "viewer"
    )
    assert client.post("/stores", json={"name": "Forbidden"}).status_code == 403


def test_account_throttle_persists_between_attempts(db):
    limit_auth(db, "test", "MixedCase@example.com", limit=2, seconds=3600)
    db.expire_all()
    limit_auth(db, "test", "mixedcase@example.com", limit=2, seconds=3600)
    db.expire_all()
    with pytest.raises(HTTPException) as error:
        limit_auth(db, "test", "mixedcase@example.com", limit=2, seconds=3600)
    assert error.value.status_code == 429


def test_negative_inventory_warning_holds_recommendations(db, store):
    job = import_csv(
        db, store, "inventory",
        b"sku,product_name,quantity_on_hand,unit_cost,retail_price,vendor\n001,Whiskey,-3,18,29,Distributor\n",
        "negative-stock.csv",
    )
    assert any(entry.get("level") == "warning" for entry in job.error_summary)
    assert "inventory import has unresolved errors" in analyze(db, store)[0].blockers
