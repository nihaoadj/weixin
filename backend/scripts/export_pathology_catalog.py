"""Export only public pathology metadata; --check never rewrites the snapshot."""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def _tree_view() -> list[dict[str, object]]:
    """Build the public snapshot from a migrated, isolated database."""

    with tempfile.TemporaryDirectory(prefix="pathology-catalog-export-") as directory:
        database = Path(directory) / "catalog.sqlite3"
        os.environ["DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from alembic import command
        from alembic.config import Config
        from app.bootstrap.seed import seed_showcase_case
        from app.modules.content.infrastructure.knowledge_catalog_repository import (
            SqlAlchemyKnowledgeCatalogRepository,
        )

        config = Config(str(BACKEND / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND / "alembic"))
        command.upgrade(config, "head")
        engine = create_engine(os.environ["DATABASE_URL"])
        try:
            with Session(engine) as session:
                seed_showcase_case(session)
                return list(SqlAlchemyKnowledgeCatalogRepository(session).tree_view())
        finally:
            engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    target = args.output or BACKEND.parent / "src/features/content/infrastructure/pathologyCatalog.generated.json"
    tree = _tree_view()
    content = json.dumps(tree, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not target.exists() or json.loads(target.read_text(encoding="utf-8")) != tree:
            raise SystemExit("Pathology public catalog snapshot differs")
        print("Pathology catalog snapshot PASS")
    else:
        target.write_text(content, encoding="utf-8")
        print("Public pathology metadata exported; no answers or credentials")


if __name__ == "__main__":
    main()
