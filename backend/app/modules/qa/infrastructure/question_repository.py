from __future__ import annotations

from sqlalchemy import false, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.content.infrastructure.models import Problem
from app.modules.qa.application.ports import QuestionRepository, QuestionThreadCommand
from app.modules.qa.application.records import MessageRecord, QuestionThreadRecord, StudentQuestionRecord
from app.modules.qa.infrastructure.models import QuestionThread, QuestionThreadMessage
from app.shared.actor import Actor


class SqlAlchemyQuestionRepository(QuestionRepository):
    """Read content through an explicit student-visibility query and own thread writes."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def class_codes(self, student_id: int) -> set[str]:
        return set(
            self._session.scalars(
                select(ClassRoom.code)
                .join(ClassMember, ClassMember.class_id == ClassRoom.id)
                .where(ClassMember.student_id == student_id, ClassRoom.status == "active")
            ).all()
        )

    def _visible_filter(self, student: Actor, class_codes: set[str]):
        targets = "," + Problem.target_ids + ","
        class_matches = (
            or_(*[targets.contains(f",{code},", autoescape=True) for code in class_codes]) if class_codes else false()
        )
        return (
            Problem.status == "published",
            or_(
                Problem.target == "all",
                (Problem.target == "individual") & targets.contains(f",{student.external_id},", autoescape=True),
                (Problem.target == "class") & class_matches,
            ),
        )

    @staticmethod
    def _message(message: QuestionThreadMessage) -> MessageRecord:
        return MessageRecord(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
        )

    def _thread_record(self, thread: QuestionThread) -> QuestionThreadRecord:
        return QuestionThreadRecord(
            question_id=thread.problem_id,
            messages=tuple(self._message(item) for item in thread.messages),
            updated_at=thread.updated_at,
        )

    def list_student_questions(self, student: Actor, class_codes: set[str]) -> tuple[StudentQuestionRecord, ...]:
        answered = (
            select(QuestionThread.id)
            .where(
                QuestionThread.problem_id == Problem.id,
                QuestionThread.student_id == student.id,
            )
            .exists()
        )
        rows = self._session.execute(
            select(Problem, answered)
            .where(*self._visible_filter(student, class_codes), Problem.content_type == "question")
            .options(selectinload(Problem.knowledge_links))
            .order_by(Problem.published_at.desc(), Problem.id.desc())
        ).all()
        return tuple(
            StudentQuestionRecord(
                id=row[0].id,
                type=row[0].type,
                title=row[0].title,
                description=row[0].description,
                published_at=row[0].published_at or row[0].created_at,
                answered=bool(row[1]),
                topic_codes=tuple(link.point_code for link in row[0].knowledge_links),
            )
            for row in rows
        )

    def find_student_question(
        self, student: Actor, problem_id: int, class_codes: set[str]
    ) -> StudentQuestionRecord | None:
        rows = self._session.execute(
            select(
                Problem,
                select(QuestionThread.id)
                .where(QuestionThread.problem_id == Problem.id, QuestionThread.student_id == student.id)
                .exists(),
            )
            .where(
                *self._visible_filter(student, class_codes),
                Problem.content_type == "question",
                Problem.id == problem_id,
            )
            .options(selectinload(Problem.knowledge_links))
        ).all()
        if not rows:
            return None
        row = rows[0]
        return StudentQuestionRecord(
            id=row[0].id,
            type=row[0].type,
            title=row[0].title,
            description=row[0].description,
            published_at=row[0].published_at or row[0].created_at,
            answered=bool(row[1]),
            topic_codes=tuple(link.point_code for link in row[0].knowledge_links),
        )

    def find_thread(self, problem_id: int, student_id: int) -> QuestionThreadRecord | None:
        thread = self._session.scalar(
            select(QuestionThread)
            .where(QuestionThread.problem_id == problem_id, QuestionThread.student_id == student_id)
            .options(selectinload(QuestionThread.messages))
        )
        return self._thread_record(thread) if thread is not None else None

    def upsert_thread(self, problem_id: int, student_id: int, command: QuestionThreadCommand) -> QuestionThreadRecord:
        thread = self._session.scalar(
            select(QuestionThread)
            .where(QuestionThread.problem_id == problem_id, QuestionThread.student_id == student_id)
            .options(selectinload(QuestionThread.messages))
        )
        if thread is None:
            thread = QuestionThread(problem_id=problem_id, student_id=student_id)
            self._session.add(thread)
            self._session.flush()
        thread.messages.clear()
        self._session.flush()
        for message in command.messages:
            thread.messages.append(QuestionThreadMessage(role=message.role, content=message.content))
        self._session.flush()
        return self._thread_record(thread)
