from sqlalchemy.orm import Session

from app.modules.content.wiring import knowledge_catalog_port
from app.modules.qa.application.medical_chat import MedicalChatApplication
from app.modules.qa.application.use_cases import ConversationsApplication, QuestionsApplication
from app.modules.qa.infrastructure.conversation_repository import SqlAlchemyConversationRepository
from app.modules.qa.infrastructure.medical_chat_audit import SqlAlchemyMedicalChatAudit
from app.modules.qa.infrastructure.medical_chat_gateway import MedicalChatHttpGateway
from app.platform.transactions import SqlAlchemyUnitOfWork


def conversations_application(session: Session) -> ConversationsApplication:
    return ConversationsApplication(
        SqlAlchemyConversationRepository(session), SqlAlchemyUnitOfWork(session), knowledge_catalog_port(session)
    )


def questions_application() -> QuestionsApplication:
    return QuestionsApplication()


def medical_chat_application(session: Session) -> MedicalChatApplication:
    return MedicalChatApplication(
        gateway=MedicalChatHttpGateway(),
        audit=SqlAlchemyMedicalChatAudit(session),
        uow=SqlAlchemyUnitOfWork(session),
        knowledge_catalog=knowledge_catalog_port(session),
    )
