from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from math import isfinite

from app.modules.content.public import KnowledgeCatalogPort
from app.modules.learning.application.evidence_ports import (
    LearningEvidenceCommand,
    LearningEvidenceMetricCommand,
    LearningEvidenceRepository,
)
from app.modules.learning.application.evidence_records import LearningEvidenceEventRecord
from app.shared.errors import AppError, PersistenceConflict
from app.shared.uow import UnitOfWork

_SOURCE_RULES = {
    "qa_topic_activity": ("personal_unverified", {"student_only"}),
    "self_pbl_completion": ("personal_unverified", {"student_only"}),
    "ai_personal_practice": ("personal_unverified", {"student_only"}),
    "reviewed_question_attempt": ("reviewed_practice", {"student_only", "class_aggregate"}),
    "case_assessment": ("reviewed_practice", {"student_only"}),
    "pbl_task_attempt": ("pbl_formal", {"class_detail"}),
    "pbl_cycle_evaluation": ("pbl_formal", {"class_detail"}),
    "classroom_final_test": ("pbl_formal", {"class_detail"}),
    "private_final_test": ("personal_unverified", {"student_only"}),
}
_RESULTS = {"observed", "correct", "incorrect", "partial", "passed", "failed"}
_METRIC_KINDS = {"knowledge", "dimension", "participation", "goal"}
_DIMENSION_CODES = {
    "information_gathering",
    "problem_representation",
    "differential_diagnosis",
    "evidence_reasoning",
    "test_selection",
    "management_safety",
}


class LearningEvidenceApplication:
    """Owns the minimal, append-only learning evidence ledger."""

    def __init__(
        self, repository: LearningEvidenceRepository, uow: UnitOfWork, knowledge_catalog: KnowledgeCatalogPort,
        final_test_sources=None,
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._knowledge_catalog = knowledge_catalog
        self._final_test_sources = final_test_sources

    def append(self, command: LearningEvidenceCommand) -> LearningEvidenceEventRecord:
        self._validate(command)
        command = replace(
            command,
            source_id=command.source_id.strip(),
            dedupe_key=command.dedupe_key.strip(),
            metrics=tuple(replace(metric, metric_code=metric.metric_code.strip()) for metric in command.metrics),
        )
        dedupe_key = command.dedupe_key
        existing = self._repository.find_by_dedupe(dedupe_key)
        if existing is not None:
            if self._same_payload(existing, command):
                return existing
            raise AppError("STATE_CONFLICT", "学习证据幂等键已用于不同内容", 409)
        try:
            result = self._repository.append(command)
            self._uow.flush()
            return result
        except PersistenceConflict:
            # A concurrent identical append is safe to replay; the repository is
            # queried after the failed insert while the caller owns rollback.
            self._uow.rollback()
            current = self._repository.find_by_dedupe(dedupe_key)
            if current is not None and self._same_payload(current, command):
                return current
            raise AppError("STATE_CONFLICT", "学习证据写入发生冲突", 409) from None

    def append_and_commit(self, command: LearningEvidenceCommand) -> LearningEvidenceEventRecord:
        result = self.append(command)
        self._uow.commit()
        return result

    def list_events(
        self,
        student_ids: tuple[int, ...],
        start,
        end,
        *,
        include_student_only: bool = True,
    ) -> tuple[LearningEvidenceEventRecord, ...]:
        return self._repository.list_events(
            student_ids, _timestamp(start), _timestamp(end), include_student_only=include_student_only
        )

    @staticmethod
    def _same_payload(existing: LearningEvidenceEventRecord, command: LearningEvidenceCommand) -> bool:
        return (
            existing.student_id,
            existing.class_id,
            existing.source_type,
            existing.source_id.strip(),
            existing.source_version,
            existing.authority_level,
            existing.visibility_scope,
            existing.event_kind,
            _timestamp(existing.occurred_at),
            existing.contract_version,
            tuple(
                (
                    metric.metric_kind,
                    metric.metric_code,
                    metric.normalized_score,
                    metric.result,
                    metric.evidence_present,
                )
                for metric in existing.metrics
            ),
        ) == (
            command.student_id,
            command.class_id,
            command.source_type,
            command.source_id.strip(),
            command.source_version,
            command.authority_level,
            command.visibility_scope,
            command.event_kind,
            _timestamp(command.occurred_at),
            command.contract_version,
            tuple(
                (
                    metric.metric_kind,
                    metric.metric_code,
                    metric.normalized_score,
                    metric.result,
                    metric.evidence_present,
                )
                for metric in command.metrics
            ),
        )

    def _validate(self, command: LearningEvidenceCommand) -> None:
        if command.student_id <= 0 or not command.source_id.strip() or len(command.source_id) > 100:
            raise AppError("VALIDATION_ERROR", "学习证据来源无效", 422)
        if not 1 <= command.source_version <= 2**31 - 1 or not 1 <= command.contract_version <= 100:
            raise AppError("VALIDATION_ERROR", "学习证据版本无效", 422)
        if not command.dedupe_key.strip() or len(command.dedupe_key) > 180:
            raise AppError("VALIDATION_ERROR", "学习证据幂等键无效", 422)
        occurred_at = _timestamp(command.occurred_at)
        if occurred_at == datetime.min.replace(tzinfo=UTC):
            raise AppError("VALIDATION_ERROR", "学习证据时间无效", 422)
        rule = _SOURCE_RULES.get(command.source_type)
        if rule is None or command.authority_level != rule[0] or command.visibility_scope not in rule[1]:
            raise AppError("VALIDATION_ERROR", "学习证据来源权限组合无效", 422)
        if command.visibility_scope == "student_only" and command.class_id is not None:
            raise AppError("VALIDATION_ERROR", "个人学习证据不能带班级", 422)
        if command.visibility_scope != "student_only" and command.class_id is None:
            raise AppError("VALIDATION_ERROR", "班级学习证据必须带班级", 422)
        if command.event_kind not in {"engagement", "assessment", "outcome"}:
            raise AppError("VALIDATION_ERROR", "学习证据事件类型无效", 422)
        seen: set[tuple[str, str]] = set()
        frozen_points = None
        if command.source_type in {"classroom_final_test", "private_final_test"}:
            if self._final_test_sources is None:
                raise AppError("VALIDATION_ERROR", "最终测试证据来源未注册", 422)
            frozen_points = self._final_test_sources.evidence_points(command)
        for metric in command.metrics:
            self._validate_metric(metric, command.event_kind, frozen_points)
            key = (metric.metric_kind, metric.metric_code)
            if key in seen:
                raise AppError("VALIDATION_ERROR", "同一证据事件不能重复指标", 422)
            seen.add(key)

    def _validate_metric(self, metric: LearningEvidenceMetricCommand, event_kind: str, frozen_points=None) -> None:
        if metric.metric_kind not in _METRIC_KINDS or not metric.metric_code.strip() or len(metric.metric_code) > 120:
            raise AppError("VALIDATION_ERROR", "学习证据指标编码无效", 422)
        if metric.result not in _RESULTS:
            raise AppError("VALIDATION_ERROR", "学习证据结果无效", 422)
        score = metric.normalized_score
        if score is not None and (isinstance(score, bool) or not isinstance(score, int | float) or not isfinite(score)):
            raise AppError("VALIDATION_ERROR", "学习证据分数无效", 422)
        if score is not None and not 0 <= float(score) <= 100:
            raise AppError("VALIDATION_ERROR", "学习证据分数必须在 0 到 100 之间", 422)
        if event_kind == "engagement" and score is not None:
            raise AppError("VALIDATION_ERROR", "活跃事件不能带分数", 422)
        if metric.metric_kind == "knowledge" and (
            metric.metric_code not in frozen_points if frozen_points is not None
            else self._knowledge_catalog.point_view(metric.metric_code) is None
        ):
            raise AppError("VALIDATION_ERROR", "知识点编码不存在", 422)
        if metric.metric_kind == "dimension" and metric.metric_code not in _DIMENSION_CODES:
            raise AppError("VALIDATION_ERROR", "能力维度编码不存在", 422)


def _timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = ["LearningEvidenceApplication"]
