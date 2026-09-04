"""Export the FastAPI contract without starting a server."""

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

for env_name in tuple(os.environ):
    normalized_name = env_name.upper()
    if normalized_name.startswith(("AI_", "PBL_", "COZE_", "JWT_", "OPENAI_", "WECHAT_")) or normalized_name.endswith(
        ("_KEY", "_SECRET", "_TOKEN")
    ):
        os.environ.pop(env_name, None)

os.environ.update(
    {
        "APP_ENV": "contract-export",
        "DATABASE_URL": "sqlite:///:memory:",
        "JWT_SECRET": "contract-export",
        "SEED_SHOWCASE_CASE": "false",
        "AI_ENABLED": "false",
        "AI_BASE_URL": "",
        "AI_API_KEY": "",
        "AI_MODEL": "",
        "ENABLE_DEMO_AUTH": "false",
        "WECHAT_APP_ID": "",
        "WECHAT_APP_SECRET": "",
        "WECHAT_API_BASE_URL": "",
        "WECHAT_TEACHER_OPENIDS": "",
    }
)

sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
