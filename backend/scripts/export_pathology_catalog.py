"""Export only public pathology metadata; --check never rewrites the snapshot."""

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.modules.content.domain.knowledge_catalog import tree_view  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    target = args.output or BACKEND.parent / "src/features/content/infrastructure/pathologyCatalog.generated.json"
    content = json.dumps(tree_view(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not target.exists() or json.loads(target.read_text(encoding="utf-8")) != tree_view():
            raise SystemExit("Pathology public catalog snapshot differs")
        print("Pathology catalog snapshot PASS")
    else:
        target.write_text(content, encoding="utf-8")
        print("Public pathology metadata exported; no answers or credentials")


if __name__ == "__main__":
    main()
