from sqlalchemy.orm import Session

from app.modules.classroom.application.use_cases import ClassroomApplication
from app.modules.classroom.infrastructure.repositories import SqlAlchemyClassroomRepository
from app.modules.classroom.infrastructure.scope import SqlAlchemyClassroomScope
from app.platform.transactions import SqlAlchemyUnitOfWork


def classroom_application(session: Session) -> ClassroomApplication:
    return ClassroomApplication(SqlAlchemyClassroomRepository(session), SqlAlchemyUnitOfWork(session))


def classroom_scope_port(session: Session) -> SqlAlchemyClassroomScope:
    return SqlAlchemyClassroomScope(session)
