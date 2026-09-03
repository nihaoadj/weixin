"""Generate deterministic synthetic response fixtures from Pydantic models (no DB or network)."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bootstrap.seed import SAFETY_NOTICE, showcase_case_payload
from app.modules.training.api.schemas import CaseDraftGenerateResponse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = showcase_case_payload()
    draft = CaseDraftGenerateResponse.model_validate(
        {
            **{
                key: payload[key]
                for key in (
                    "title",
                    "description",
                    "specialty",
                    "difficulty",
                    "estimated_minutes",
                    "case_definition",
                    "rubric",
                )
            },
            "generation_mode": "fallback",
            "safety_notice": SAFETY_NOTICE,
        }
    )
    target = args.output or Path(__file__).resolve().parents[2] / "src/test/fixtures/case-draft.json"
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(draft.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
