from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom, MedicalReview
from app.modules.content.application.ports import ProblemRepository
from app.modules.content.application.records import (
    KnowledgeCardContributionRecord,
    ProblemCommand,
    ProblemRecord,
    ReviewRecord,
)
from app.modules.content.infrastructure.models import KnowledgeCardContribution, Problem, ProblemKnowledgeLink
from app.modules.identity.infrastructure.models import User
from app.modules.qa.infrastructure.models import QuestionThread
from app.modules.training.infrastructure.models import CaseAttempt, CaseAttemptMessage, StageSubmission
from app.shared.actor import Actor


class SqlAlchemyProblemRepository(ProblemRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def teacher_action_counts(self, teacher_id: int, *, medical_reviewer: bool) -> dict[str, int | None]:
        counts: dict[str, int | None] = {
            "cases_draft": 0,
            "cases_rejected": 0,
            "cases_approved": 0,
            "questions_draft": 0,
            "questions_rejected": 0,
            "cards_draft": 0,
            "cards_rejected": 0,
            "medical_cases_pending": None,
            "medical_cards_pending": None,
        }
        if medical_reviewer:
            counts["medical_cases_pending"] = 0
            counts["medical_cards_pending"] = 0
        return counts

    @staticmethod
    def _record(problem: Problem, answer_count: int = 0) -> ProblemRecord:
        return ProblemRecord(
            id=problem.id,
            type=problem.type,
            title=problem.title,
            description=problem.description,
            target=problem.target,
            target_label=problem.target_label,
            target_ids=tuple(item for item in (problem.target_ids or "").split(",") if item),
            status=problem.status,
            created_at=problem.created_at,
            published_at=problem.published_at,
            content_type=problem.content_type or "question",
            slug=problem.slug,
            specialty=problem.specialty or "",
            difficulty=problem.difficulty or "basic",
            estimated_minutes=problem.estimated_minutes or 10,
            version=problem.version or 1,
            parent_problem_id=problem.parent_problem_id,
            author_id=problem.author_id,
            medical_review_status=problem.medical_review_status,
            capability_tags=tuple(problem.capability_tags or []),
            case_definition=deepcopy(problem.case_definition),
            rubric=deepcopy(problem.rubric),
            answer_count=answer_count,
            knowledge_point_codes=tuple(link.point_code for link in problem.knowledge_links),
        )

    @staticmethod
    def _review_record(review: MedicalReview) -> ReviewRecord:
        return ReviewRecord(
            id=review.id,
            problem_id=review.problem_id,
            reviewer_id=review.reviewer_id,
            decision=review.decision,
            comment=review.comment,
            problem_version=review.problem_version,
            case_digest=review.case_digest,
            created_at=review.created_at,
        )

    @staticmethod
    def _knowledge_card_record(card: KnowledgeCardContribution) -> KnowledgeCardContributionRecord:
        return KnowledgeCardContributionRecord(
            id=card.id,
            point_code=card.point_code,
            owner_id=card.owner_id,
            class_code=card.class_code,
            version=card.version,
            card_type=card.card_type,
            prompt=card.prompt,
            options=tuple(card.options or []),
            correct_option=card.correct_option,
            explanation=card.explanation,
            reference=card.reference,
            status=card.status,
            reviewer_id=card.reviewer_id,
            review_comment=card.review_comment,
            reviewed_at=card.reviewed_at,
            created_at=card.created_at,
            updated_at=card.updated_at,
            ai_title=card.ai_title,
            source_type=card.source_type,
            source_snapshot_id=card.source_snapshot_id,
            source_position=card.source_position,
            source_finding_ids=tuple(str(item) for item in (card.source_finding_ids or [])),
            origin_student_id=card.origin_student_id,
            origin_student_name=card.origin_student_name,
            target_student_ids=tuple(int(item) for item in (card.target_student_ids or [])),
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

    def get_knowledge_card(self, card_id: int) -> KnowledgeCardContributionRecord | None:
        card = self._session.get(KnowledgeCardContribution, card_id)
        return self._knowledge_card_record(card) if card else None

    def list_all(self) -> tuple[ProblemRecord, ...]:
        problems = self._session.scalars(
            select(Problem).where(Problem.status != "deleted").order_by(Problem.created_at.desc())
        ).all()
        problems.sort(key=lambda item: (0 if item.slug == "cap-undergraduate-showcase" else 1, -(item.id or 0)))
        counts = self.answer_counts([item.id for item in problems])
        return tuple(self._record(item, counts.get(item.id, 0)) for item in problems)

    def list_visible_for_student(self, student: Actor, class_codes: set[str]) -> tuple[ProblemRecord, ...]:
        targets = "," + Problem.target_ids + ","
        class_matches = (
            or_(*[targets.contains(f",{code},", autoescape=True) for code in class_codes]) if class_codes else False
        )
        statement = (
            select(Problem)
            .where(
                Problem.status == "published",
                or_(
                    Problem.target == "all",
                    (Problem.target == "individual") & targets.contains(f",{student.external_id},", autoescape=True),
                    (Problem.target == "class") & class_matches,
                ),
            )
            .order_by(Problem.created_at.desc())
        )
        problems = self._session.scalars(statement).all()
        problems.sort(key=lambda item: (0 if item.slug == "cap-undergraduate-showcase" else 1, -(item.id or 0)))
        counts = self.answer_counts([item.id for item in problems])
        return tuple(self._record(item, counts.get(item.id, 0)) for item in problems)

    def get(self, problem_id: int) -> ProblemRecord | None:
        problem = self._session.get(Problem, problem_id)
        return self._record(problem) if problem is not None else None

    @staticmethod
    def _apply(problem: Problem, command: ProblemCommand, teacher_id: int, *, new: bool) -> None:
        problem.type = command.type
        problem.title = command.title
        problem.description = command.description
        problem.target = command.target
        problem.target_label = command.target_label
        problem.target_ids = ",".join(command.target_ids)
        problem.status = "published" if command.content_type == "guided_case" else "draft" if new else problem.status
        if command.content_type == "guided_case" and not problem.published_at:
            problem.published_at = datetime.now(UTC)
        problem.content_type = command.content_type
        problem.slug = command.slug
        problem.specialty = command.specialty
        problem.difficulty = command.difficulty
        problem.estimated_minutes = command.estimated_minutes
        problem.version = command.version if new else (problem.version or 1) + 1
        problem.parent_problem_id = command.parent_problem_id
        problem.case_definition = deepcopy(command.case_definition)
        problem.rubric = deepcopy(command.rubric)
        problem.capability_tags = list(command.capability_tags)
        existing_codes = {link.point_code for link in problem.knowledge_links}
        for link in list(problem.knowledge_links):
            if link.point_code not in command.knowledge_point_codes:
                problem.knowledge_links.remove(link)
        problem.knowledge_links.extend(
            ProblemKnowledgeLink(point_code=code)
            for code in command.knowledge_point_codes
            if code not in existing_codes
        )
        problem.author_id = problem.author_id or teacher_id
        if new or command.content_type == "guided_case":
            problem.medical_review_status = "not_required"

    def create(self, teacher_id: int, command: ProblemCommand) -> ProblemRecord:
        problem = Problem()
        self._apply(problem, command, teacher_id, new=True)
        self._session.add(problem)
        self._session.flush()
        return self._record(problem)

    def update(self, problem_id: int, teacher_id: int, command: ProblemCommand) -> ProblemRecord:
        problem = self._session.get(Problem, problem_id)
        if problem is None:
            raise LookupError("problem disappeared")
        self._apply(problem, command, teacher_id, new=False)
        self._session.flush()
        return self._record(problem)

    def delete(self, problem_id: int) -> None:
        problem = self._session.get(Problem, problem_id)
        if problem is None:
            raise LookupError("problem disappeared")
        problem.status = "deleted"
        self._session.flush()

    def answer_counts(self, problem_ids: list[int]) -> dict[int, int]:
        if not problem_ids:
            return {}
        question_rows = self._session.execute(
            select(QuestionThread.problem_id, func.count(QuestionThread.id))
            .where(QuestionThread.problem_id.in_(problem_ids))
            .group_by(QuestionThread.problem_id)
        ).all()
        counts = {problem_id: count for problem_id, count in question_rows}
        guided_rows = self._session.execute(
            select(CaseAttempt.problem_id, func.count(func.distinct(CaseAttempt.id)))
            .where(
                CaseAttempt.problem_id.in_(problem_ids),
                or_(
                    exists().where(CaseAttemptMessage.attempt_id == CaseAttempt.id),
                    exists().where(StageSubmission.attempt_id == CaseAttempt.id),
                ),
            )
            .group_by(CaseAttempt.problem_id)
        ).all()
        counts.update({problem_id: count for problem_id, count in guided_rows})
        return counts

    def review_view(self, problem_id: int) -> tuple[ProblemRecord, str | None, tuple[ReviewRecord, ...]]:
        problem = self._session.get(Problem, problem_id)
        if problem is None:
            raise LookupError("problem disappeared")
        author = self._session.get(User, problem.author_id) if problem.author_id else None
        reviews = tuple(
            self._review_record(item)
            for item in self._session.scalars(
                select(MedicalReview).where(MedicalReview.problem_id == problem.id).order_by(MedicalReview.id)
            ).all()
        )
        return self._record(problem), author.nickname if author else None, reviews

    def review_history(self, problem_id: int) -> tuple[ReviewRecord, ...]:
        return tuple(
            self._review_record(item)
            for item in self._session.scalars(
                select(MedicalReview).where(MedicalReview.problem_id == problem_id).order_by(MedicalReview.id)
            ).all()
        )
