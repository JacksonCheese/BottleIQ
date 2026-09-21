import os
from collections.abc import Generator
from datetime import date

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ["DEMO_ENABLED"] = "true"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from bottleiq.auth import passwords
from bottleiq.db import Base, get_db
from bottleiq.main import app, attempts
from bottleiq.models import Organization, OrganizationMember, Store, User


@pytest.fixture(scope="session")
def engine():
    url = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    if "postgres" in url and not url.rsplit("/", 1)[-1].endswith("_test"):
        raise RuntimeError("TEST_DATABASE_URL must name a dedicated database ending in _test")
    kwargs = (
        {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
        if url == "sqlite://"
        else {}
    )
    engine = create_engine(url, **kwargs)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.isolation_level = None
            connection.execute("PRAGMA foreign_keys=ON")

        @event.listens_for(engine, "begin")
        def begin(connection):
            connection.exec_driver_sql("BEGIN")

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(engine) -> Generator[Session]:
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        ) as session:
            yield session
        transaction.rollback()


@pytest.fixture
def store(db):
    org = Organization(name="Test shop")
    user = User(
        email="owner@example.com", name="Owner", password_hash=passwords.hash("test-password-123")
    )
    db.add_all([org, user])
    db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="owner"))
    store = Store(organization_id=org.id, name="Test store")
    db.add(store)
    db.commit()
    return store


@pytest.fixture
def client(db, store):
    app.dependency_overrides[get_db] = lambda: db
    attempts.clear()
    with TestClient(app) as client:
        response = client.post(
            "/auth/login", json={"email": "owner@example.com", "password": "test-password-123"}
        )
        assert response.status_code == 200
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def today():
    return date(2026, 9, 20)
