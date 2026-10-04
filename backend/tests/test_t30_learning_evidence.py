from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.learning.application.evidence import LearningEvidenceApplication
from app.modules.learning.application.evidence_ports import LearningEvidenceCommand, LearningEvidenceMetricCommand
from app.shared.errors import AppError

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
POINT_CODE = "pathology.cell-injury.adaptation"


class Catalog:
    def point_view(self, code):
        return {"code": code} if code == POINT_CODE else None


class Uow:
    def flush(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class Repository:
    def __init__(self) -> None:
        self.rows = {}

    def find_by_dedupe(self, dedupe_key):
        return self.rows.get(dedupe_key)

    def append(self, command):
        from app.modules.learning.application.evidence_records import (
            LearningEvidenceEventRecord,
            LearningEvidenceMetricRecord,
        )

        row = LearningEvidenceEventRecord(
            id=len(self.rows) + 1,
            student_id=command.student_id,
            class_id=command.class_id,
            source_type=command.source_type,
            source_id=command.source_id,
            source_version=command.source_version,
            authority_level=command.authority_level,
            visibility_scope=command.visibility_scope,
            event_kind=command.event_kind,
            occurred_at=command.occurred_at,
            dedupe_key=command.dedupe_key,
            contract_version=command.contract_version,
            created_at=NOW,
            metrics=tuple(
                LearningEvidenceMetricRecord(
                    id=index + 1,
                    metric_kind=item.metric_kind,
                    metric_code=item.metric_code,
                    normalized_score=item.normalized_score,
                    result=item.result,
                    evidence_present=item.evidence_present,
                )
                for index, item in enumerate(command.metrics)
            ),
        )
        self.rows[command.dedupe_key] = row
        return row

    def list_events(self, *_args, **_kwargs):
        return tuple(self.rows.values())


def command(**overrides):
    value = dict(
        student_id=7,
        class_id=None,
        source_type="ai_personal_practice",
        source_id="attempt-1",
        source_version=1,
        authority_level="personal_unverified",
        visibility_scope="student_only",
        event_kind="assessment",
        occurred_at=NOW,
        dedupe_key="ai-personal-practice:attempt-1",
        metrics=(LearningEvidenceMetricCommand("knowledge", POINT_CODE, 100, "correct"),),
    )
    value.update(overrides)
    return LearningEvidenceCommand(**value)


def test_evidence_is_idempotent_and_collision_safe() -> None:
    repository = Repository()
    application = LearningEvidenceApplication(repository, Uow(), Catalog())
    first = application.append(command())
    assert application.append(command()) == first
    assert len(repository.rows) == 1
    with pytest.raises(AppError) as error:
        application.append(command(metrics=(LearningEvidenceMetricCommand("knowledge", POINT_CODE, 0, "incorrect"),)))
    assert error.value.code == "STATE_CONFLICT" and error.value.status_code == 409


@pytest.mark.parametrize(
    "overrides",
    [
        {"class_id": 3},
        {"source_type": "case_assessment", "authority_level": "formal_instruction", "visibility_scope": "class_detail"},
        {"source_type": "ai_personal_practice", "normalized_score": 101},
    ],
)
def test_invalid_visibility_and_score_are_rejected(overrides) -> None:
    values = dict(overrides)
    if "normalized_score" in values:
        values["metrics"] = (
            LearningEvidenceMetricCommand("knowledge", POINT_CODE, values.pop("normalized_score"), "correct"),
        )
    with pytest.raises(AppError) as error:
        LearningEvidenceApplication(Repository(), Uow(), Catalog()).append(command(**values))
    assert error.value.code == "VALIDATION_ERROR"


def test_engagement_has_no_scoring_metric_and_unknown_codes_are_rejected() -> None:
    with pytest.raises(AppError):
        LearningEvidenceApplication(Repository(), Uow(), Catalog()).append(
            command(event_kind="engagement", metrics=(LearningEvidenceMetricCommand("knowledge", POINT_CODE, 10),))
        )
    with pytest.raises(AppError):
        LearningEvidenceApplication(Repository(), Uow(), Catalog()).append(
            command(metrics=(LearningEvidenceMetricCommand("knowledge", "not-a-real-point", None),))
        )


def test_command_contract_contains_no_sensitive_content() -> None:
    names = {field.name for field in LearningEvidenceCommand.__dataclass_fields__.values()}
    assert not names.intersection({"answer", "content", "prompt", "rubric", "feedback", "nickname"})
