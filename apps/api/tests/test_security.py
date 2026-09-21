import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from bottleiq.models import (
    InventorySnapshot,
    Organization,
    OrganizationMember,
    Product,
    Store,
    Vendor,
)
from bottleiq.services.orders import safe_csv


def test_anonymous_endpoints_require_auth(client):
    client.cookies.clear()
    for route in (
        "/stores",
        "/vendors",
        "/inventory?store_id=x",
        "/dashboard?store_id=x",
        "/smart-orders/x",
        "/imports?store_id=x",
    ):
        assert client.get(route).status_code == 401


def test_other_tenant_store_is_hidden(client, db):
    org = Organization(name="Other")
    db.add(org)
    db.flush()
    store = Store(organization_id=org.id, name="Other shop")
    db.add(store)
    db.commit()
    for route in ("/inventory", "/dashboard", "/alerts", "/imports", "/smart-orders"):
        assert client.get(route, params={"store_id": store.id}).status_code == 404


def test_other_tenant_vendor_cannot_be_attached(client, db, store):
    org = Organization(name="Other")
    db.add(org)
    db.flush()
    vendor = Vendor(organization_id=org.id, name="Hidden")
    db.add(vendor)
    product = Product(organization_id=store.organization_id, sku="x", product_name="Test")
    db.add(product)
    db.commit()
    response = client.patch(
        f"/products/{product.id}",
        json={
            "default_vendor_id": vendor.id,
            "units_per_case": 12,
            "category": "Wine",
            "brand": "Test",
        },
    )
    assert response.status_code == 422
    assert (
        client.post(
            "/smart-orders", json={"store_id": store.id, "vendor_id": vendor.id}
        ).status_code
        == 404
    )


def test_cross_tenant_foreign_key_is_enforced(db, store):
    org = Organization(name="Other")
    db.add(org)
    db.flush()
    product = Product(organization_id=org.id, sku="foreign", product_name="Other")
    db.add(product)
    db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            InventorySnapshot(
                organization_id=store.organization_id,
                store_id=store.id,
                product_id=product.id,
                source_key="x",
                content_hash="x",
                snapshot_at=__import__("datetime").date.today(),
                quantity_on_hand=1,
                unit_cost=10,
                retail_price=20,
            )
        )
        db.flush()


def test_viewer_cannot_mutate(client, db, store):
    member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == store.organization_id
        )
    )
    member.role = "viewer"
    db.commit()
    assert client.post("/stores", json={"name": "No"}).status_code == 403
    assert client.post("/recommendations/generate", json={"store_id": store.id}).status_code == 403
    assert client.get("/stores").status_code == 200


def test_csrf_origin_rejected(client):
    assert (
        client.post(
            "/stores", json={"name": "No"}, headers={"origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/stores", json={"name": "No"}, headers={"sec-fetch-site": "cross-site"}
        ).status_code
        == 403
    )


def test_logout_revokes_session(client):
    cookie = client.cookies.get("bottleiq_session")
    assert client.post("/auth/logout").status_code == 200
    client.cookies.set("bottleiq_session", cookie)
    assert client.get("/auth/me").status_code == 401


def test_cookie_is_httponly_and_samesite(client):
    r = client.post(
        "/auth/login", json={"email": "owner@example.com", "password": "test-password-123"}
    )
    assert "HttpOnly" in r.headers["set-cookie"]
    assert "SameSite=lax" in r.headers["set-cookie"]


def test_bad_login_and_rate_limit(client):
    for _ in range(19):
        assert (
            client.post(
                "/auth/login", json={"email": "owner@example.com", "password": "incorrect-password"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/auth/login", json={"email": "owner@example.com", "password": "incorrect-password"}
        ).status_code
        == 429
    )


def test_upload_size_limited(client, store):
    response = client.post(
        "/imports/inventory",
        data={"store_id": store.id},
        files={"file": ("huge.csv", b"x" * (10 * 1024 * 1024 + 1), "text/csv")},
    )
    assert response.status_code == 413


def test_signup_and_create_store(client):
    client.cookies.clear()
    response = client.post(
        "/auth/signup",
        json={
            "name": "New Owner",
            "email": "new@example.com",
            "password": "new-password-1234",
            "organization_name": "New store business",
        },
    )
    assert response.status_code == 201
    assert client.post("/stores", json={"name": "Downtown"}).status_code == 201
    assert len(client.get("/stores").json()) == 1


@pytest.mark.parametrize("text", ["=1+1", "+SUM(A1:A2)", "@danger", "  =formula", "-cmd"])
def test_csv_formula_escaped(text):
    assert safe_csv(text) == "'" + text


def test_missing_product_order_and_job_are_hidden(client):
    assert client.get("/smart-orders/not-a-real-id").status_code == 404
    assert client.get("/imports/not-a-real-id/errors").status_code == 404


def test_production_config_rejects_public_demo():
    from unittest.mock import patch

    from bottleiq.config import settings

    settings.cache_clear()
    with patch.dict(
        "os.environ", {"ENVIRONMENT": "production", "DEMO_ENABLED": "true", "COOKIE_SECURE": "true"}
    ):
        with pytest.raises(ValueError, match="Production requires"):
            settings()
    settings.cache_clear()


def test_query_options_coerce_numeric_strings(client, store):
    response = client.get(
        "/recommendations",
        params={"store_id": store.id, "window": "60", "target_days": "21", "service_level": ".95"},
    )
    assert response.status_code == 200
    assert (
        client.get("/recommendations", params={"store_id": store.id, "window": "45"}).status_code
        == 422
    )
