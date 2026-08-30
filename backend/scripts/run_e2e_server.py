# ruff: noqa: E402, I001

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
DATABASE_PATH = (BACKEND_ROOT / "data" / "e2e.db").resolve()
EXPECTED_PARENT = (BACKEND_ROOT / "data").resolve()

if DATABASE_PATH.parent != EXPECTED_PARENT or DATABASE_PATH.name != "e2e.db":
    raise RuntimeError("Refusing to reset an unexpected E2E database path")

EXPECTED_PARENT.mkdir(parents=True, exist_ok=True)
if DATABASE_PATH.exists():
    DATABASE_PATH.unlink()

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{DATABASE_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "e2e-only-secret"
os.environ["ENABLE_DEMO_AUTH"] = "true"
os.environ["CORS_ORIGINS"] = "http://127.0.0.1:41733"

import uvicorn  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

config = Config(str(BACKEND_ROOT / "alembic.ini"))
config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
command.upgrade(config, "head")

uvicorn.run("app.main:app", host="127.0.0.1", port=8001, log_level="warning")
