"""Minimum PBL participation facts for authorized classroom progress."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pbl.infrastructure.models import PblParticipation, PblSession


class SqlPblClassroomParticipation:
    def __init__(self, session: Session) -> None:
        self._session = session

    def classroom_participants(self, class_id: int, session_id: int) -> tuple[int, ...] | None:
        existing = self._session.scalar(
            select(PblSession.id).where(
                PblSession.id == session_id,
                PblSession.class_id == class_id,
                PblSession.session_kind == "classroom",
            )
        )
        if existing is None:
            return None
        return tuple(
            self._session.scalars(
                select(PblParticipation.student_id)
                .where(PblParticipation.session_id == session_id)
                .order_by(PblParticipation.student_id)
            ).all()
        )
