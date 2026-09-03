from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom, MedicalReview
from app.modules.content.application.ports import ProblemRepository
from app.modules.content.application.records import (
    KnowledgeCardContributionCommand,
    KnowledgeCardContributionRecord,
    ProblemCommand,
    ProblemRecord,
    ReviewRecord,
)
from app.modules.content.domain.digest import case_digest
from app.modules.content.infrastructure.models import KnowledgeCardContribution, Problem, ProblemKnowledgeLink
from app.modules.identity.infrastructure.models import User
from app.modules.qa.infrastructure.models import QuestionThread
from app.modules.training.infrastructure.models import CaseAttempt, CaseAttemptMessage, StageSubmission
from app.shared.actor import Actor
from app.shared.errors import PersistenceConflict


class SqlAlchemyProblemRepository(ProblemRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

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

    def teacher_owns_class(self, teacher_id: int, class_code: str) -> bool:
        return (
            self._session.scalar(
                select(ClassRoom.id).where(
                    ClassRoom.teacher_id == teacher_id, ClassRoom.code == class_code, ClassRoom.status == "active"
                )
            )
            is not None
        )

    def create_knowledge_card(
        self, owner_id: int, command: KnowledgeCardContributionCommand
    ) -> KnowledgeCardContributionRecord:
        card = KnowledgeCardContribution(owner_id=owner_id)
        self._apply_knowledge_card(card, command)
        self._session.add(card)
        self._session.flush()
        return self._knowledge_card_record(card)

    def update_knowledge_card(
        self, card_id: int, owner_id: int, command: KnowledgeCardContributionCommand
    ) -> KnowledgeCardContributionRecord:
        card = self._session.get(KnowledgeCardContribution, card_id)
        if card is None or card.owner_id != owner_id:
            raise LookupError("knowledge card disappeared")
        self._apply_knowledge_card(card, command)
        card.version += 1
        card.status = "draft"
        card.reviewer_id = None
        card.review_comment = ""
        card.reviewed_at = None
        self._session.flush()
        return self._knowledge_card_record(card)

    @staticmethod
    def _apply_knowledge_card(card: KnowledgeCardContribution, command: KnowledgeCardContributionCommand) -> None:
        card.point_code = command.point_code
        card.class_code = command.class_code
        card.card_type = command.card_type
        card.prompt = command.prompt
        card.options = list(command.options)
        card.correct_option = command.correct_option
        card.explanation = command.explanation
        card.reference = command.reference

    def get_knowledge_card(self, card_id: int) -> KnowledgeCardContributionRecord | None:
        card = self._session.get(KnowledgeCardContribution, card_id)
        return self._knowledge_card_record(card) if card else None

    def list_knowledge_cards_for_owner(self, owner_id: int) -> tuple[KnowledgeCardContributionRecord, ...]:
        cards = self._session.scalars(
            select(KnowledgeCardContribution)
            .where(KnowledgeCardContribution.owner_id == owner_id)
            .order_by(KnowledgeCardContribution.updated_at.desc(), KnowledgeCardContribution.id.desc())
        ).all()
        return tuple(self._knowledge_card_record(card) for card in cards)

    def list_knowledge_cards_by_status(self, status: str) -> tuple[KnowledgeCardContributionRecord, ...]:
        cards = self._session.scalars(
            select(KnowledgeCardContribution)
            .where(KnowledgeCardContribution.status == status)
            .order_by(KnowledgeCardContribution.updated_at.asc(), KnowledgeCardContribution.id.asc())
        ).all()
        return tuple(self._knowledge_card_record(card) for card in cards)

    def list_visible_knowledge_cards(
        self, student_id: int, class_codes: set[str], point_code: str | None
    ) -> tuple[KnowledgeCardContributionRecord, ...]:
        class_scope = [KnowledgeCardContribution.class_code.is_(None)]
        if class_codes:
            class_scope.append(KnowledgeCardContribution.class_code.in_(class_codes))
        statement = select(KnowledgeCardContribution).where(
            KnowledgeCardContribution.status == "approved", or_(*class_scope)
        )
        if point_code:
            statement = statement.where(KnowledgeCardContribution.point_code == point_code)
        cards = self._session.scalars(statement.order_by(KnowledgeCardContribution.id.desc())).all()
        return tuple(self._knowledge_card_record(card) for card in cards)

    def submit_knowledge_card(self, card_id: int) -> KnowledgeCardContributionRecord:
        card = self._session.get(KnowledgeCardContribution, card_id)
        if card is None:
            raise LookupError("knowledge card disappeared")
        card.status = "pending"
        self._session.flush()
        return self._knowledge_card_record(card)

    def decide_knowledge_card(
        self, card_id: int, reviewer_id: int, decision: str, comment: str
    ) -> KnowledgeCardContributionRecord:
        card = self._session.get(KnowledgeCardContribution, card_id)
        if card is None:
            raise LookupError("knowledge card disappeared")
        card.status = "approved" if decision == "approved" else "rejected"
        card.reviewer_id = reviewer_id
        card.review_comment = comment
        card.reviewed_at = datetime.now(UTC)
        self._session.flush()
        return self._knowledge_card_record(card)

    def disable_knowledge_card(self, card_id: int) -> KnowledgeCardContributionRecord:
        card = self._session.get(KnowledgeCardContribution, card_id)
        if card is None:
            raise LookupError("knowledge card disappeared")
        card.status = "disabled"
        self._session.flush()
        return self._knowledge_card_record(card)

    def list_all(self) -> tuple[ProblemRecord, ...]:
        problems = self._session.scalars(select(Problem).order_by(Problem.created_at.desc())).all()
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
        problem.status = (
            "draft"
            if new
            else command.status
            if command.content_type == "question" and command.status
            else problem.status
        )
        problem.content_type = command.content_type
        problem.slug = command.slug
        problem.specialty = command.specialty
        problem.difficulty = command.difficulty
        problem.estimated_minutes = command.estimated_minutes
        problem.version = command.version
        problem.parent_problem_id = command.parent_problem_id
        problem.case_definition = deepcopy(command.case_definition)
        problem.rubric = deepcopy(command.rubric)
        problem.capability_tags = list(command.capability_tags)
        if not new:
            problem.knowledge_links.clear()
        problem.knowledge_links.extend(ProblemKnowledgeLink(point_code=code) for code in command.knowledge_point_codes)
        problem.author_id = problem.author_id or teacher_id
        if new or command.content_type == "guided_case":
            problem.medical_review_status = "not_submitted"

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

    def clone(self, problem: ProblemRecord, teacher_id: int) -> ProblemRecord:
        maximum = self._session.scalar(select(func.max(Problem.version)).where(Problem.slug == problem.slug)) or 0
        clone = Problem(
            type=problem.type,
            title=problem.title,
            description=problem.description,
            target=problem.target,
            target_label=problem.target_label,
            target_ids=",".join(problem.target_ids),
            status="draft",
            slug=problem.slug,
            content_type="guided_case",
            specialty=problem.specialty,
            difficulty=problem.difficulty,
            estimated_minutes=problem.estimated_minutes,
            version=maximum + 1,
            parent_problem_id=problem.id,
            case_definition=deepcopy(problem.case_definition),
            rubric=deepcopy(problem.rubric),
            capability_tags=list(problem.capability_tags),
            knowledge_links=[ProblemKnowledgeLink(point_code=code) for code in problem.knowledge_point_codes],
            author_id=teacher_id,
            medical_review_status="not_submitted",
        )
        self._session.add(clone)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        return self._record(clone)

    def publish(self, problem_id: int) -> ProblemRecord:
        problem = self._session.get(Problem, problem_id)
        if problem is None:
            raise LookupError("problem disappeared")
        problem.status = "published"
        problem.published_at = datetime.now(UTC)
        self._session.flush()
        return self._record(problem)

    def reject(self, problem_id: int) -> ProblemRecord:
        problem = self._session.get(Problem, problem_id)
        if problem is None:
            raise LookupError("problem disappeared")
        problem.status = "rejected"
        self._session.flush()
        return self._record(problem)

    def invalidate_review(self, problem_id: int) -> None:
        problem = self._session.get(Problem, problem_id)
        if problem is not None:
            problem.medical_review_status = "not_submitted"

    def latest_approved_review_digest(self, problem_id: int) -> str | None:
        return self._session.scalar(
            select(MedicalReview.case_digest)
            .where(MedicalReview.problem_id == problem_id, MedicalReview.decision == "approved")
            .order_by(MedicalReview.id.desc())
        )

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

    def review_queue(self, status: str) -> tuple[ProblemRecord, ...]:
        problems = self._session.scalars(
            select(Problem)
            .where(Problem.content_type == "guided_case", Problem.medical_review_status == status)
            .order_by(Problem.created_at)
        ).all()
        counts = self.answer_counts([item.id for item in problems])
        return tuple(self._record(item, counts.get(item.id, 0)) for item in problems)

    def submit_review(self, problem_id: int, teacher_id: int) -> ProblemRecord:
        problem = self._session.get(Problem, problem_id)
        if problem is None:
            raise LookupError("problem disappeared")
        problem.medical_review_status = "pending"
        self._session.flush()
        return self._record(problem)

    def add_review(self, problem_id: int, reviewer_id: int, decision: str, comment: str) -> ProblemRecord:
        problem = self._session.get(Problem, problem_id)
        if problem is None:
            raise LookupError("problem disappeared")
        self._session.add(
            MedicalReview(
                problem_id=problem.id,
                reviewer_id=reviewer_id,
                decision=decision,
                comment=comment,
                problem_version=problem.version,
                case_digest=case_digest(problem),
            )
        )
        problem.medical_review_status = "approved" if decision == "approved" else "rejected"
        self._session.flush()
        return self._record(problem)

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
