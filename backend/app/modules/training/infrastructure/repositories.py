from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

from sqlalchemy import false, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.content.infrastructure.models import Problem
from app.modules.identity.infrastructure.models import User
from app.modules.training.application.ports import TrainingRepository
from app.modules.training.application.records import (
    AssessmentDraft,
    AssessmentRecord,
    AttemptRecord,
    AttemptSummaryRecord,
    MessageRecord,
    PatientReplyResult,
    StageSubmissionRecord,
    TrainingProblemRecord,
)
from app.modules.training.infrastructure.models import (
    AICallLog,
    CaseAssessment,
    CaseAttempt,
    CaseAttemptMessage,
    StageSubmission,
)
from app.shared.actor import Actor
from app.shared.errors import PersistenceConflict


class SqlAlchemyTrainingRepository(TrainingRepository):
    """Persistence adapter; it never owns commit or rollback."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _problem_record(problem: Problem) -> TrainingProblemRecord:
        return TrainingProblemRecord(
            id=problem.id,
            slug=problem.slug,
            difficulty=problem.difficulty,
            version=problem.version,
            status=problem.status,
            content_type=problem.content_type,
            author_id=problem.author_id,
            target=problem.target,
            target_ids=tuple(item for item in (problem.target_ids or "").split(",") if item),
            case_definition=deepcopy(problem.case_definition or {}),
            rubric=deepcopy(problem.rubric or {}),
        )

    @staticmethod
    def _message_record(message: CaseAttemptMessage) -> MessageRecord:
        return MessageRecord(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            revealed_fact_ids=tuple(message.revealed_fact_ids or []),
        )

    @staticmethod
    def _submission_record(submission: StageSubmission) -> StageSubmissionRecord:
        return StageSubmissionRecord(
            id=submission.id,
            stage_id=submission.stage_id,
            answer=deepcopy(submission.answer or {}),
            feedback=submission.feedback,
            inherited_from_id=submission.inherited_from_id,
            created_at=submission.created_at,
        )

    @staticmethod
    def _assessment_record(assessment: CaseAssessment) -> AssessmentRecord:
        return AssessmentRecord(
            id=assessment.id,
            attempt_id=assessment.attempt_id,
            total_score=assessment.total_score,
            dimensions=tuple(deepcopy(assessment.dimensions or [])),
            strengths=tuple(assessment.strengths or []),
            weaknesses=tuple(assessment.weaknesses or []),
            next_steps=tuple(assessment.next_steps or []),
            summary=assessment.summary,
            focus_stage=assessment.focus_stage,
            model_name=assessment.model_name,
            prompt_version=assessment.prompt_version,
            fallback_used=assessment.fallback_used,
            failure_reason=assessment.failure_reason,
            latency_ms=assessment.latency_ms,
            created_at=assessment.created_at,
        )

    @classmethod
    def _attempt_record(cls, attempt: CaseAttempt) -> AttemptRecord:
        return AttemptRecord(
            id=attempt.id,
            problem_id=attempt.problem_id,
            problem_version=attempt.problem_version,
            status=attempt.status,
            current_stage=attempt.current_stage,
            retry_of_id=attempt.retry_of_id,
            focus_stage=attempt.focus_stage,
            learning_task_id=attempt.learning_task_id,
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
            assessed_at=attempt.assessed_at,
            problem=cls._problem_record(attempt.problem),
            messages=tuple(cls._message_record(item) for item in attempt.messages),
            submissions=tuple(cls._submission_record(item) for item in attempt.submissions),
            assessment=cls._assessment_record(attempt.assessment) if attempt.assessment is not None else None,
        )

    def class_codes(self, student_id: int) -> set[str]:
        student = self._session.get(User, student_id)
        legacy = set(student.class_ids or []) if student is not None else set()
        linked = set(
            self._session.scalars(
                select(ClassRoom.code)
                .join(ClassMember, ClassMember.class_id == ClassRoom.id)
                .where(ClassMember.student_id == student_id, ClassRoom.status == "active")
            ).all()
        )
        return legacy | linked

    def list_attempts(self, student_id: int, problem_id: int | None) -> tuple[AttemptSummaryRecord, ...]:
        statement = (
            select(CaseAttempt)
            .where(CaseAttempt.student_id == student_id)
            .options(joinedload(CaseAttempt.assessment))
            .order_by(CaseAttempt.started_at.desc(), CaseAttempt.id.desc())
        )
        if problem_id is not None:
            statement = statement.where(CaseAttempt.problem_id == problem_id)
        return tuple(
            AttemptSummaryRecord(
                id=item.id,
                problem_id=item.problem_id,
                status=item.status,
                current_stage=item.current_stage,
                focus_stage=item.focus_stage,
                total_score=item.assessment.total_score if item.assessment is not None else None,
                started_at=item.started_at,
            )
            for item in self._session.scalars(statement).all()
        )

    def find_visible_problem(
        self, student: Actor, class_codes: set[str], problem_id: int
    ) -> TrainingProblemRecord | None:
        target_ids = "," + Problem.target_ids + ","
        class_matches = (
            or_(*[target_ids.contains(f",{code},", autoescape=True) for code in class_codes])
            if class_codes
            else false()
        )
        statement = select(Problem).where(
            Problem.id == problem_id,
            Problem.content_type == "guided_case",
            Problem.status == "published",
            or_(
                Problem.target == "all",
                (Problem.target == "individual") & target_ids.contains(f",{student.external_id},", autoescape=True),
                (Problem.target == "class") & class_matches,
            ),
        )
        problem = self._session.scalar(statement)
        return self._problem_record(problem) if problem is not None else None

    def find_attempt(self, student_id: int, attempt_id: int) -> AttemptRecord | None:
        attempt = self._session.scalar(
            select(CaseAttempt)
            .where(CaseAttempt.id == attempt_id, CaseAttempt.student_id == student_id)
            .options(
                selectinload(CaseAttempt.problem),
                selectinload(CaseAttempt.messages),
                selectinload(CaseAttempt.submissions),
                selectinload(CaseAttempt.assessment),
            )
        )
        return self._attempt_record(attempt) if attempt is not None else None

    def find_assessment(self, student_id: int, attempt_id: int) -> AssessmentRecord | None:
        assessment = self._session.scalar(
            select(CaseAssessment)
            .join(CaseAttempt, CaseAttempt.id == CaseAssessment.attempt_id)
            .where(CaseAssessment.attempt_id == attempt_id, CaseAttempt.student_id == student_id)
        )
        return self._assessment_record(assessment) if assessment is not None else None

    def create_attempt(
        self,
        problem: TrainingProblemRecord,
        student_id: int,
        retry_of_id: int | None,
        focus_stage: str | None,
        learning_task_id: int | None,
        inherited_submissions: tuple[StageSubmissionRecord, ...],
    ) -> AttemptRecord:
        attempt = CaseAttempt(
            problem_id=problem.id,
            student_id=student_id,
            problem_version=problem.version,
            status="in_progress",
            current_stage=focus_stage or "history",
            retry_of_id=retry_of_id,
            focus_stage=focus_stage,
            learning_task_id=learning_task_id,
        )
        self._session.add(attempt)
        try:
            self._session.flush()
            for submission in inherited_submissions:
                self._session.add(
                    StageSubmission(
                        attempt_id=attempt.id,
                        stage_id=submission.stage_id,
                        answer=deepcopy(submission.answer),
                        feedback="已从上次训练沿用",
                        inherited_from_id=submission.id,
                    )
                )
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        created = self.find_attempt(student_id, attempt.id)
        if created is None:
            raise PersistenceConflict
        return created

    def append_exchange(
        self,
        student_id: int,
        attempt_id: int,
        question: str,
        reply: PatientReplyResult,
    ) -> MessageRecord:
        attempt = self._session.scalar(
            select(CaseAttempt).where(CaseAttempt.id == attempt_id, CaseAttempt.student_id == student_id)
        )
        if attempt is None:
            raise PersistenceConflict
        self._session.add(CaseAttemptMessage(attempt_id=attempt_id, stage_id="history", role="user", content=question))
        assistant = CaseAttemptMessage(
            attempt_id=attempt_id,
            stage_id="history",
            role="assistant",
            content=reply.reply,
            revealed_fact_ids=list(reply.revealed_fact_ids),
        )
        self._session.add(assistant)
        self._session.flush()
        self._session.refresh(assistant)
        return self._message_record(assistant)

    def save_submission(
        self,
        student_id: int,
        attempt_id: int,
        stage_id: str,
        answer: dict[str, object],
        feedback: str,
        next_stage: str | None,
    ) -> StageSubmissionRecord:
        attempt = self._session.scalar(
            select(CaseAttempt).where(CaseAttempt.id == attempt_id, CaseAttempt.student_id == student_id)
        )
        if attempt is None:
            raise PersistenceConflict
        if (
            self._session.scalar(
                select(StageSubmission.id).where(
                    StageSubmission.attempt_id == attempt_id, StageSubmission.stage_id == stage_id
                )
            )
            is not None
        ):
            raise PersistenceConflict
        submission = StageSubmission(
            attempt_id=attempt_id,
            stage_id=stage_id,
            answer=deepcopy(answer),
            feedback=feedback,
        )
        self._session.add(submission)
        if next_stage is None:
            attempt.status = "completed"
            attempt.current_stage = "completed"
            attempt.completed_at = datetime.now(UTC)
        else:
            attempt.current_stage = next_stage
        try:
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        self._session.refresh(submission)
        return self._submission_record(submission)

    def save_assessment(self, student_id: int, attempt_id: int, assessment: AssessmentDraft) -> AssessmentRecord:
        attempt = self._session.scalar(
            select(CaseAttempt).where(CaseAttempt.id == attempt_id, CaseAttempt.student_id == student_id)
        )
        if attempt is None:
            raise PersistenceConflict
        if self._session.scalar(select(CaseAssessment.id).where(CaseAssessment.attempt_id == attempt_id)) is not None:
            raise PersistenceConflict
        value = CaseAssessment(
            attempt_id=attempt_id,
            total_score=assessment.total_score,
            dimensions=deepcopy(list(assessment.dimensions)),
            strengths=list(assessment.strengths),
            weaknesses=list(assessment.weaknesses),
            next_steps=list(assessment.next_steps),
            summary=assessment.summary,
            focus_stage=assessment.focus_stage,
            model_name=assessment.model_name,
            prompt_version=assessment.prompt_version,
            fallback_used=assessment.fallback_used,
            latency_ms=assessment.latency_ms,
            failure_reason=assessment.failure_reason,
        )
        attempt.status = "assessed"
        attempt.current_stage = "completed"
        attempt.assessed_at = datetime.now(UTC)
        self._session.add(value)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        self._session.refresh(value)
        return self._assessment_record(value)

    def record_ai_call(
        self,
        *,
        student_id: int,
        attempt_id: int | None,
        task: str,
        model_name: str,
        prompt_version: str,
        latency_ms: int,
        fallback_used: bool,
        failure_reason: str | None,
    ) -> None:
        self._session.add(
            AICallLog(
                user_id=student_id,
                attempt_id=attempt_id,
                task=task,
                model_name=model_name,
                prompt_version=prompt_version,
                latency_ms=latency_ms,
                fallback_used=fallback_used,
                failure_reason=failure_reason,
            )
        )
