from __future__ import annotations

import hashlib
import json
from typing import Protocol


class DigestSource(Protocol):
    @property
    def title(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def specialty(self) -> str: ...

    @property
    def difficulty(self) -> str: ...

    @property
    def estimated_minutes(self) -> int: ...

    @property
    def target(self) -> str: ...

    @property
    def target_ids(self) -> str | tuple[str, ...] | list[str] | None: ...

    @property
    def case_definition(self) -> dict[str, object] | None: ...

    @property
    def rubric(self) -> dict[str, object] | None: ...

    @property
    def capability_tags(self) -> tuple[str, ...] | list[str] | None: ...

    @property
    def knowledge_point_codes(self) -> tuple[str, ...] | list[str] | None: ...


def case_digest(problem: DigestSource) -> str:
    target_ids = (
        [item for item in (problem.target_ids or "").split(",") if item]
        if isinstance(problem.target_ids, str)
        else list(problem.target_ids or [])
    )
    return hashlib.sha256(
        json.dumps(
            {
                "title": problem.title,
                "description": problem.description,
                "specialty": problem.specialty,
                "difficulty": problem.difficulty,
                "estimated_minutes": problem.estimated_minutes,
                "target": problem.target,
                "target_ids": target_ids,
                "case_definition": problem.case_definition,
                "rubric": problem.rubric,
                "capability_tags": problem.capability_tags or [],
                "knowledge_point_codes": sorted(getattr(problem, "knowledge_point_codes", ()) or ()),
                "schema_version": (problem.case_definition or {}).get("schema_version"),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
