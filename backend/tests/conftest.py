"""Pytest's earliest test-only bootstrap.

Environment variables are intentionally set at import time: this file loads
before pytest imports any test module, and therefore before application settings
can construct an engine from an inherited developer DATABASE_URL.
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.testing_resources import (  # noqa: E402
    ResourceOwnershipError,
    assert_owned_resource,
    cleanup_managed_database,
    create_managed_database,
)

TEST_RESOURCE = create_managed_database("pytest")
os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": TEST_RESOURCE.url,
        "TEST_RESOURCE_DIR": str(TEST_RESOURCE.root),
        "TEST_RESOURCE_TOKEN": TEST_RESOURCE.token,
        "JWT_SECRET": "pytest-only-secret-with-at-least-thirty-two-characters",
        "AI_ENABLED": "false",
        "AI_BASE_URL": "",
        "AI_API_KEY": "",
        "AI_MODEL": "",
        "PBL_AI_ENABLED": "false",
        "PBL_MOCK_ENABLED": "false",
        "PBL_AI_PROVIDER": "openai_compatible",
        "PBL_OPENAI_BASE_URL": "",
        "PBL_OPENAI_API_KEY": "",
        "PBL_OPENAI_MODEL": "",
        "COZE_API_TOKEN": "",
        "COZE_API_BASE": "",
        "COZE_INVOCATION_MODE": "",
        "COZE_BOT_ID": "",
        "COZE_WORKFLOW_ID": "",
        "COZE_APP_ID": "",
        "WECHAT_APP_ID": "",
        "WECHAT_APP_SECRET": "",
        "SEED_SHOWCASE_CASE": "false",
        "ENABLE_DEMO_AUTH": "true",
    }
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "seed_showcase: create the explicit showcase seed for this test")
    config.addinivalue_line("markers", "capture_server_errors: return HTTP 500 responses instead of re-raising")


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app

    return fastapi_app


@pytest.fixture(scope="session")
def db_engine():
    from app.db import engine

    return engine


@pytest.fixture(scope="function")
def db(db_engine, managed_database):
    from app.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(request: pytest.FixtureRequest, managed_database):
    return request.node._t01_test_client


@pytest.fixture(autouse=True)
def block_nonlocal_network(monkeypatch: pytest.MonkeyPatch):
    """Tests may use loopback services, but must never reach real providers."""
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def guarded_connect(sock: socket.socket, address):
        host = address[0] if isinstance(address, tuple) else ""
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise RuntimeError(f"Blocked non-local network access in tests: {host!r}")
        return original_connect(sock, address)

    def guarded_connect_ex(sock: socket.socket, address):
        host = address[0] if isinstance(address, tuple) else ""
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise RuntimeError(f"Blocked non-local network access in tests: {host!r}")
        return original_connect_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)


@pytest.fixture(autouse=True)
def managed_database(request: pytest.FixtureRequest, app, db_engine):
    """Reset only the launcher-owned database and bind legacy module clients."""
    from fastapi.testclient import TestClient

    from app.db import Base, SessionLocal

    # Validate immediately before every schema operation. A matching URL alone
    # is not ownership proof: it cannot detect a replaced directory or junction.
    assert_owned_resource(TEST_RESOURCE)
    if str(db_engine.url) != TEST_RESOURCE.url:
        raise ResourceOwnershipError("Application engine is not bound to the launcher-owned test database")
    db_engine.dispose()
    assert_owned_resource(TEST_RESOURCE)
    Base.metadata.drop_all(bind=db_engine)
    assert_owned_resource(TEST_RESOURCE)
    Base.metadata.create_all(bind=db_engine)
    if request.node.get_closest_marker("seed_showcase"):
        from app.services.case_seed import seed_showcase_case

        with SessionLocal() as session:
            seed_showcase_case(session)

    module = request.module
    has_legacy_client = "client" in module.__dict__
    raise_server_exceptions = request.node.get_closest_marker("capture_server_errors") is None
    with TestClient(app, raise_server_exceptions=raise_server_exceptions) as test_client:
        request.node._t01_test_client = test_client
        if has_legacy_client:
            module.client = test_client
        yield
    if has_legacy_client:
        module.client = None
    db_engine.dispose()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    # Preserve failed/interrupted resources for diagnosis, but never widen the
    # cleanup target. Successful runs remove their exact owned directory.
    if exitstatus == 0:
        cleanup_managed_database(TEST_RESOURCE)
    else:
        print(f"Retaining failed pytest resource for diagnosis: {TEST_RESOURCE.root}")
