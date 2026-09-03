from sqlalchemy.orm import Session

from app.modules.learning.application.knowledge_review import KnowledgeReviewApplication
from app.modules.learning.application.ports import CaseAttemptPort
from app.modules.learning.application.use_cases import LearningApplication
from app.modules.learning.infrastructure.knowledge_review_repository import SqlAlchemyReviewRepository
from app.modules.learning.infrastructure.practice_generator import PracticeDefinitionGenerator
from app.modules.learning.infrastructure.repositories import SqlAlchemyLearningRepository
from app.platform.transactions import SqlAlchemyUnitOfWork


def learning_application(session: Session, *, case_attempts: CaseAttemptPort) -> LearningApplication:
    return LearningApplication(
        repository=SqlAlchemyLearningRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
        practice_generator=PracticeDefinitionGenerator(),
        case_attempts=case_attempts,
    )


def knowledge_review_application(session: Session) -> KnowledgeReviewApplication:
    return KnowledgeReviewApplication(SqlAlchemyReviewRepository(session), SqlAlchemyUnitOfWork(session))
