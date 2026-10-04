import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from alembic import command
from alembic.config import Config
from app.bootstrap.test_seed import seed_test_data
from app.core.config import get_settings
from app.db import SessionLocal


def main() -> None:
    settings = get_settings()
    if settings.app_env.strip().lower() == "production":
        raise RuntimeError("拒绝向 production 环境导入测试数据")

    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(alembic_config, "head")
    db = SessionLocal()
    try:
        counts = seed_test_data(db)
    finally:
        db.close()

    print(f"已导入开发测试数据：{settings.database_url}")
    for name, count in counts.items():
        print(f"{name}: {count}")
    print("演示账号：demo_student / demo_student_b / demo_teacher / demo_reviewer")


if __name__ == "__main__":
    main()
