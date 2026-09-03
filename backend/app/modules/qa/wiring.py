from sqlalchemy.orm import Session

from app.modules.qa.application.medical_chat import MedicalChatApplication
from app.modules.qa.application.use_cases import ConversationsApplication, QuestionsApplication
from app.modules.qa.infrastructure.conversation_repository import SqlAlchemyConversationRepository
from app.modules.qa.infrastructure.medical_chat_audit import SqlAlchemyMedicalChatAudit
from app.modules.qa.infrastructure.medical_chat_gateway import MedicalChatHttpGateway
from app.modules.qa.infrastructure.question_repository import SqlAlchemyQuestionRepository
from app.platform.transactions import SqlAlchemyUnitOfWork


def conversations_application(session: Session) -> ConversationsApplication:
    return ConversationsApplication(SqlAlchemyConversationRepository(session), SqlAlchemyUnitOfWork(session))


def questions_application(session: Session) -> QuestionsApplication:
    return QuestionsApplication(SqlAlchemyQuestionRepository(session), SqlAlchemyUnitOfWork(session))


def medical_chat_application(session: Session) -> MedicalChatApplication:
    return MedicalChatApplication(
        gateway=MedicalChatHttpGateway(),
        audit=SqlAlchemyMedicalChatAudit(session),
        uow=SqlAlchemyUnitOfWork(session),
    )
