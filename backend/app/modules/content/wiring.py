from sqlalchemy.orm import Session

from app.modules.content.application.use_cases import ContentApplication
from app.modules.content.domain.policy import ContentPolicy
from app.modules.content.infrastructure.audit import SqlAlchemyCaseDraftAudit
from app.modules.content.infrastructure.draft_generator import CaseDraftAiGateway
from app.modules.content.infrastructure.repositories import SqlAlchemyProblemRepository
from app.platform.transactions import SqlAlchemyUnitOfWork


def content_application(session: Session) -> ContentApplication:
    return ContentApplication(
        repository=SqlAlchemyProblemRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
        policy=ContentPolicy(),
        draft_generator=CaseDraftAiGateway(),
        draft_audit=SqlAlchemyCaseDraftAudit(session),
    )
