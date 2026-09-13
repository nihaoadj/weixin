from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.learning.infrastructure.models import LearningPlan, ReviewState
from app.modules.learning.infrastructure.study_models import StudyPath, StudyPracticeAttempt, StudyPracticeGroup
from app.shared.errors import AppError, PersistenceConflict


def record(row) -> dict:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


class SqlStudyRepository:
    def __init__(self, session: Session):
        self._db = session

    def paths(self, student_id: int, point_code: str) -> list[dict]:
        return [
            record(p)
            for p in self._db.scalars(
                select(StudyPath)
                .where(StudyPath.student_id == student_id, StudyPath.point_code == point_code)
                .order_by(StudyPath.id.desc())
            ).all()
        ]

    def path(self, student_id: int, path_id: int) -> dict | None:
        row = self._db.scalar(select(StudyPath).where(StudyPath.student_id == student_id, StudyPath.id == path_id))
        return record(row) if row else None

    def save_path(self, student_id: int, point_code: str, session_id: int, client_id: str, version: str) -> dict:
        row = self._db.scalar(
            select(StudyPath).where(StudyPath.student_id == student_id, StudyPath.client_id == client_id)
        )
        if row:
            if row.point_code != point_code or row.session_id != session_id:
                raise AppError("STATE_CONFLICT", "路径标识已使用", 409)
            return record(row)
        row = StudyPath(
            student_id=student_id,
            point_code=point_code,
            session_id=session_id,
            client_id=client_id,
            material_version=version,
        )
        self._db.add(row)
        try:
            self._db.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        return record(row)

    def legacy_access(self, student_id: int, point_code: str) -> bool:
        if self._db.scalar(
            select(ReviewState.id)
            .where(ReviewState.student_id == student_id, ReviewState.point_code == point_code)
            .limit(1)
        ):
            return True
        contexts = self._db.scalars(
            select(LearningPlan.source_context).where(LearningPlan.student_id == student_id)
        ).all()
        return any(point_code in str(context) for context in contexts)

    def groups(self, student_id: int, path_id: int | None = None) -> list[dict]:
        stmt = select(StudyPracticeGroup).where(StudyPracticeGroup.student_id == student_id)
        if path_id is not None:
            stmt = stmt.where(StudyPracticeGroup.path_id == path_id)
        return [record(g) for g in self._db.scalars(stmt.order_by(StudyPracticeGroup.id)).all()]

    def group(self, student_id: int, group_id: int) -> dict | None:
        row = self._db.scalar(
            select(StudyPracticeGroup).where(
                StudyPracticeGroup.student_id == student_id, StudyPracticeGroup.id == group_id
            )
        )
        return record(row) if row else None

    def claim_group(self, path: dict, cycle: int, client_id: str, snapshot_id: int) -> dict:
        row = self._db.scalar(
            select(StudyPracticeGroup).where(
                StudyPracticeGroup.path_id == path["id"], StudyPracticeGroup.cycle == cycle
            )
        )
        now = datetime.now(UTC)
        if row:
            if row.status == "ready":
                return record(row)
            count = self._db.execute(
                update(StudyPracticeGroup)
                .where(
                    StudyPracticeGroup.id == row.id,
                    (StudyPracticeGroup.status == "failed")
                    | (StudyPracticeGroup.updated_at < now - timedelta(minutes=3)),
                )
                .values(status="generating", claim=client_id, updated_at=now, failure=None)
            ).rowcount
            if not count:
                raise AppError("STATE_CONFLICT", "题目生成中，请稍后重新加载", 409)
            self._db.refresh(row)
        else:
            row = StudyPracticeGroup(
                path_id=path["id"],
                student_id=path["student_id"],
                snapshot_id=snapshot_id,
                cycle=cycle,
                claim=client_id,
                questions=[],
                updated_at=now,
            )
            self._db.add(row)
            try:
                self._db.flush()
            except IntegrityError as error:
                raise PersistenceConflict from error
        return record(row)

    def finish_group(self, group_id: int, claim: str, questions: list[dict], failure: str | None) -> bool:
        return bool(
            self._db.execute(
                update(StudyPracticeGroup)
                .where(
                    StudyPracticeGroup.id == group_id,
                    StudyPracticeGroup.claim == claim,
                    StudyPracticeGroup.status == "generating",
                )
                .values(
                    status="failed" if failure else "ready",
                    questions=questions,
                    failure=failure,
                    updated_at=datetime.now(UTC),
                )
            ).rowcount
        )

    def attempts(self, student_id: int, group_id: int) -> list[dict]:
        return [
            record(a)
            for a in self._db.scalars(
                select(StudyPracticeAttempt)
                .where(
                    StudyPracticeAttempt.student_id == student_id,
                    StudyPracticeAttempt.group_id == group_id,
                )
                .order_by(StudyPracticeAttempt.id)
            ).all()
        ]

    def save_attempt(
        self, student_id: int, group_id: int, question_index: int, client_id: str, selected_option: int, correct: bool
    ) -> dict:
        old = self._db.scalar(
            select(StudyPracticeAttempt).where(
                StudyPracticeAttempt.student_id == student_id, StudyPracticeAttempt.client_id == client_id
            )
        )
        if old:
            if (old.group_id, old.question_index, old.selected_option) != (group_id, question_index, selected_option):
                raise AppError("STATE_CONFLICT", "作答标识已用于其他答案", 409)
            return record(old)
        row = StudyPracticeAttempt(
            student_id=student_id,
            group_id=group_id,
            question_index=question_index,
            client_id=client_id,
            selected_option=selected_option,
            correct=correct,
            due_at=datetime.now(UTC) + timedelta(days=3 if correct else 1),
        )
        self._db.add(row)
        try:
            self._db.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        return record(row)
