from sqlalchemy.orm import Session

from app.modules.content.application.teacher_question_bank import TeacherQuestionBankApplication
from app.modules.content.application.use_cases import ContentApplication
from app.modules.content.domain.policy import ContentPolicy
from app.modules.content.infrastructure.audit import SqlAlchemyCaseDraftAudit
from app.modules.content.infrastructure.draft_generator import CaseDraftAiGateway
from app.modules.content.infrastructure.knowledge_catalog_repository import SqlAlchemyKnowledgeCatalogRepository
from app.modules.content.infrastructure.pbl_publication import SqlAlchemyQuestionPublication
from app.modules.content.infrastructure.repositories import SqlAlchemyProblemRepository
from app.modules.content.infrastructure.teacher_question_bank import SqlTeacherQuestionBank
from app.modules.learning.public import RouteTestQuestionSourcePort
from app.modules.training.public import CaseSnapshotPort
from app.platform.transactions import SqlAlchemyUnitOfWork


def content_application(session: Session, *, snapshots: CaseSnapshotPort | None = None) -> ContentApplication:
    return ContentApplication(
        repository=SqlAlchemyProblemRepository(session),
        knowledge_catalog=knowledge_catalog_port(session),
        uow=SqlAlchemyUnitOfWork(session),
        policy=ContentPolicy(),
        draft_generator=CaseDraftAiGateway(),
        draft_audit=SqlAlchemyCaseDraftAudit(session),
        snapshots=snapshots,
    )


def question_publication_port(session: Session) -> SqlAlchemyQuestionPublication:
    return SqlAlchemyQuestionPublication(session)


def teacher_question_bank_application(
    session: Session, sources: RouteTestQuestionSourcePort
) -> TeacherQuestionBankApplication:
    return TeacherQuestionBankApplication(
        SqlTeacherQuestionBank(session, sources, knowledge_catalog_port(session)),
        SqlAlchemyUnitOfWork(session),
        sources,
    )


def knowledge_catalog_port(session: Session) -> SqlAlchemyKnowledgeCatalogRepository:
    return SqlAlchemyKnowledgeCatalogRepository(session)
