# ruff: noqa: E402, I001

import os
import sys
import threading
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
from app.testing_resources import assert_owned_resource, cleanup_managed_database, create_managed_database

port = int(os.environ.get("E2E_PORT", "8001"))
if not 1 <= port <= 65535:
    raise RuntimeError("E2E_PORT must be between 1 and 65535")
cors_origin = os.environ.get("E2E_CORS_ORIGIN", "http://127.0.0.1:41733")
if not cors_origin.startswith("http://127.0.0.1:"):
    raise RuntimeError("E2E_CORS_ORIGIN must be a loopback HTTP origin")

resource = create_managed_database("e2e")

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = resource.url
os.environ["TEST_RESOURCE_DIR"] = str(resource.root)
os.environ["TEST_RESOURCE_TOKEN"] = resource.token
os.environ["JWT_SECRET"] = "e2e-only-secret-with-at-least-thirty-two-characters"
os.environ["ENABLE_DEMO_AUTH"] = "true"
os.environ["CORS_ORIGINS"] = cors_origin
os.environ["AI_ENABLED"] = "false"
os.environ["AI_BASE_URL"] = ""
os.environ["AI_API_KEY"] = ""
os.environ["AI_MODEL"] = ""
os.environ["WECHAT_APP_ID"] = ""
os.environ["WECHAT_APP_SECRET"] = ""
os.environ["SEED_SHOWCASE_CASE"] = "false"

import uvicorn  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

config = Config(str(BACKEND_ROOT / "alembic.ini"))
config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
try:
    assert_owned_resource(resource)
    command.upgrade(config, "head")
    assert_owned_resource(resource)
    from app.db import SessionLocal  # noqa: E402
    from app.services.test_seed import seed_test_data  # noqa: E402

    with SessionLocal() as session:
        seed_counts = seed_test_data(session)
    print(f"E2E database resource: {resource.root}", flush=True)
    print(f"E2E API URL: http://127.0.0.1:{port}", flush=True)
    print(f"E2E seeded resources: {seed_counts}", flush=True)
    server = uvicorn.Server(uvicorn.Config("app.main:app", host="127.0.0.1", port=port, log_level="warning"))
    shutdown_file = os.environ.get("E2E_SHUTDOWN_FILE")
    if shutdown_file:
        shutdown_path = Path(shutdown_file).absolute()

        def stop_when_requested() -> None:
            while not shutdown_path.exists():
                time.sleep(0.05)
            server.should_exit = True

        threading.Thread(target=stop_when_requested, daemon=True).start()
    server.run()
finally:
    try:
        from app.db import engine  # noqa: E402

        engine.dispose()
    except ImportError:
        pass
    cleanup_managed_database(resource)
