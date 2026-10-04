from __future__ import annotations

from datetime import UTC, datetime

from app.modules.classroom.public import ClassroomScopePort
from app.modules.learning.public import LearningEvidenceCommand, LearningEvidenceMetricCommand, LearningEvidencePort
from app.modules.training.application.ports import (
    AssessmentGateway,
    PatientReplyGateway,
    TrainingRepository,
)
from app.modules.training.application.records import (
    AssessmentDraft,
    AssessmentRecord,
    AttemptRecord,
    AttemptSummaryRecord,
    PatientMessageResult,
    StageSubmissionRecord,
)
from app.modules.training.domain.state import (
    CASE_STAGES,
    TrainingPolicy,
    apply_ai_candidates,
    deterministic_assessment,
    summarize_dimensions,
)
from app.shared.actor import Actor
from app.shared.errors import AppError, PersistenceConflict
from app.shared.uow import UnitOfWork


class TrainingApplication:
    """Owns case-attempt state transitions; adapters only persist or call AI."""

    def __init__(
        self,
        repository: TrainingRepository,
        uow: UnitOfWork,
        patient_gateway: PatientReplyGateway,
        assessment_gateway: AssessmentGateway,
        learning_evidence: LearningEvidencePort | None = None,
        classroom_scope: ClassroomScopePort | None = None,
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._patient_gateway = patient_gateway
        self._assessment_gateway = assessment_gateway
        self._learning_evidence = learning_evidence
        self._classroom_scope = classroom_scope

    def list_attempts(self, actor: Actor, problem_id: int | None) -> tuple[AttemptSummaryRecord, ...]:
        actor.require_role("student")
        return self._repository.list_attempts(actor.id, problem_id)

    def start(
        self, actor: Actor, problem_id: int, retry_of_id: int | None = None, learning_task_id: int | None = None
    ) -> AttemptRecord:
        actor.require_role("student")
        problem = self._repository.find_visible_problem(actor, self._repository.class_codes(actor.id), problem_id)
        if problem is None or problem.content_type != "guided_case":
            raise AppError("RESOURCE_NOT_FOUND", "Case not found", 404)
        focus_stage = None
        inherited: tuple[StageSubmissionRecord, ...] = ()
        if retry_of_id is not None:
            original = self._repository.find_attempt(actor.id, retry_of_id)
            if (
                original is None
                or original.status != "assessed"
                or original.assessment is None
                or original.problem.slug != problem.slug
            ):
                raise AppError("STATE_CONFLICT", "Retry requires your assessed attempt for this case", 409)
            focus_stage = original.assessment.focus_stage
            try:
                focus_index = CASE_STAGES.index(focus_stage)
            except ValueError as error:
                raise AppError("STATE_CONFLICT", "评估阶段无效", 409) from error
            inherited = tuple(
                submission for submission in original.submissions if submission.stage_id in CASE_STAGES[:focus_index]
            )
        try:
            attempt = self._repository.create_attempt(
                problem,
                actor.id,
                retry_of_id,
                focus_stage,
                learning_task_id,
                inherited,
            )
            self._uow.commit()
        except PersistenceConflict as error:
            self._uow.rollback()
            raise AppError("STATE_CONFLICT", "Unable to create a case attempt", 409) from error
        return self._require_attempt(actor.id, attempt.id)

    def get(self, actor: Actor, attempt_id: int) -> AttemptRecord:
        actor.require_role("student")
        return self._require_attempt(actor.id, attempt_id)

    def send_patient_message(self, actor: Actor, attempt_id: int, content: str) -> PatientMessageResult:
        actor.require_role("student")
        attempt = self._require_attempt(actor.id, attempt_id)
        normalized = content.strip()
        if not normalized:
            raise AppError("VALIDATION_ERROR", "问题不能为空", 422)
        if attempt.status != "in_progress" or attempt.current_stage != "history":
            raise AppError("STATE_CONFLICT", "History conversation is locked", 409)
        if sum(message.role == "user" for message in attempt.messages) >= 30:
            raise AppError("STATE_CONFLICT", "Maximum history questions reached; submit your summary", 409)
        reply = self._patient_gateway.reply(attempt, normalized)
        try:
            message = self._repository.append_exchange(actor.id, attempt.id, normalized, reply)
            self._repository.record_ai_call(
                student_id=actor.id,
                attempt_id=attempt.id,
                task="patient_reply",
                model_name=reply.model_name,
                prompt_version=reply.prompt_version,
                latency_ms=reply.latency_ms,
                fallback_used=reply.fallback_used,
                failure_reason=reply.failure_reason,
            )
            self._uow.commit()
        except PersistenceConflict as error:
            self._uow.rollback()
            raise AppError("STATE_CONFLICT", "Case attempt is no longer writable", 409) from error
        except Exception as error:
            self._uow.rollback()
            raise AppError("SERVICE_ERROR", "AI audit is temporarily unavailable", 503) from error
        return PatientMessageResult(message=message, response_mode=reply.response_mode)

    def submit_stage(
        self, actor: Actor, attempt_id: int, stage_id: str, answer: dict[str, object]
    ) -> StageSubmissionRecord:
        actor.require_role("student")
        attempt = self._require_attempt(actor.id, attempt_id)
        TrainingPolicy.require_in_progress(stage_id, attempt.current_stage)
        TrainingPolicy.require_stage_answer(stage_id, answer)
        next_stage = TrainingPolicy.next_stage(stage_id)
        try:
            submission = self._repository.save_submission(
                actor.id,
                attempt.id,
                stage_id,
                answer,
                "已保存。请继续下一阶段。",
                next_stage,
            )
            self._uow.commit()
        except PersistenceConflict as error:
            self._uow.rollback()
            raise AppError("STATE_CONFLICT", "Stage already submitted", 409) from error
        return submission

    def complete(self, actor: Actor, attempt_id: int) -> AssessmentRecord:
        actor.require_role("student")
        attempt = self._require_attempt(actor.id, attempt_id)
        if attempt.assessment is not None:
            return attempt.assessment
        TrainingPolicy.require_complete(attempt.status)
        dimensions, _focus_stage, _strengths, _weaknesses, _next_steps, _total, safety = deterministic_assessment(
            attempt
        )
        generation = self._assessment_gateway.assess(attempt)
        apply_ai_candidates(attempt, dimensions, generation.candidates)
        focus_stage, strengths, weaknesses, next_steps, total = summarize_dimensions(dimensions)
        draft = AssessmentDraft(
            total_score=total,
            dimensions=tuple(dimensions),
            strengths=tuple(strengths),
            weaknesses=tuple(weaknesses),
            next_steps=tuple(next_steps),
            summary=f"总分 {total}。{safety}",
            focus_stage=focus_stage,
            model_name=generation.model_name,
            prompt_version=generation.prompt_version,
            fallback_used=generation.fallback_used,
            failure_reason=generation.failure_reason,
            latency_ms=generation.latency_ms,
        )
        try:
            self._repository.record_ai_call(
                student_id=actor.id,
                attempt_id=attempt.id,
                task="assessment",
                model_name=draft.model_name,
                prompt_version=draft.prompt_version,
                latency_ms=draft.latency_ms,
                fallback_used=draft.fallback_used,
                failure_reason=draft.failure_reason,
            )
            assessment = self._repository.save_assessment(actor.id, attempt.id, draft)
            self._append_case_evidence(actor.id, attempt, assessment)
            self._uow.commit()
            return assessment
        except PersistenceConflict:
            self._uow.rollback()
            existing = self._repository.find_assessment(actor.id, attempt.id)
            if existing is not None:
                return existing
            raise AppError("STATE_CONFLICT", "Assessment already created", 409) from None
        except Exception as error:
            self._uow.rollback()
            raise AppError("SERVICE_ERROR", "AI audit is temporarily unavailable", 503) from error

    def _append_case_evidence(self, student_id: int, attempt: AttemptRecord, assessment: AssessmentRecord) -> None:
        if self._learning_evidence is None or attempt.problem.medical_review_status != "approved":
            return
        # A linked case is assessed through its published package, never as a second teacher result.
        if attempt.learning_task_id is not None:
            return
        metrics: list[LearningEvidenceMetricCommand] = []
        for item in attempt.problem.knowledge_point_codes:
            metrics.append(LearningEvidenceMetricCommand("knowledge", item, result="observed"))
        for dimension in assessment.dimensions:
            code = str(dimension.get("dimension_id") or "")
            if not code:
                continue
            raw_score = dimension.get("score")
            score = float(raw_score) if isinstance(raw_score, int | float) and not isinstance(raw_score, bool) else None
            metrics.append(LearningEvidenceMetricCommand("dimension", code, score, "observed", score is not None))
        self._learning_evidence.append(
            LearningEvidenceCommand(
                student_id=student_id,
                class_id=None,
                source_type="case_assessment",
                source_id=str(assessment.id),
                source_version=attempt.problem_version,
                authority_level="reviewed_practice",
                visibility_scope="student_only",
                event_kind="assessment",
                occurred_at=assessment.created_at or datetime.now(UTC),
                dedupe_key=f"case-assessment:{assessment.id}:v{attempt.problem_version}:personal",
                metrics=tuple(metrics),
            )
        )

    def assessment(self, actor: Actor, attempt_id: int) -> AssessmentRecord:
        actor.require_role("student")
        assessment = self._repository.find_assessment(actor.id, attempt_id)
        if assessment is None:
            raise AppError("STATE_CONFLICT", "Assessment is not available", 409)
        return assessment

    def assessment_comparison(self, actor: Actor, attempt_id: int) -> tuple[AssessmentRecord, AssessmentRecord | None]:
        attempt = self.get(actor, attempt_id)
        assessment = attempt.assessment
        if assessment is None:
            raise AppError("STATE_CONFLICT", "Assessment is not available", 409)
        previous = (
            self._repository.find_assessment(actor.id, attempt.retry_of_id) if attempt.retry_of_id is not None else None
        )
        return assessment, previous

    def _require_attempt(self, student_id: int, attempt_id: int) -> AttemptRecord:
        attempt = self._repository.find_attempt(student_id, attempt_id)
        if attempt is None:
            raise AppError("RESOURCE_NOT_FOUND", "Case attempt not found", 404)
        return attempt
