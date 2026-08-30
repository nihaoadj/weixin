# FastAPI Backend

Python FastAPI backend for the medical education QA demo.

## Quick Start

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m alembic upgrade head
python scripts/seed_test_data.py
python -m uvicorn app.main:app --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Run tests:

```bash
python -m ruff check .
python -m pytest --cov=app --cov-report=term-missing -q
```

`ENABLE_DEMO_AUTH` 只用于试点和 E2E。`APP_ENV=production` 时 Demo 登录始终关闭。

`python scripts/seed_test_data.py` 只允许在非生产环境执行，会先应用迁移，再幂等导入开发测试数据，不会清空已有数据库记录。
