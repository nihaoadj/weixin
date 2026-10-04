from sqlalchemy.orm import Session

from app.modules.classroom.wiring import classroom_scope_port
from app.modules.content.wiring import (
    knowledge_catalog_port,
)
from app.modules.learning.application.evidence import LearningEvidenceApplication
from app.modules.learning.application.knowledge_review import KnowledgeReviewApplication
from app.modules.learning.application.ports import CaseAttemptPort
from app.modules.learning.application.use_cases import LearningApplication
from app.modules.learning.infrastructure.evidence_repository import SqlAlchemyEvidenceRepository
from app.modules.learning.infrastructure.knowledge_review_repository import SqlAlchemyReviewRepository
from app.modules.learning.infrastructure.practice_generator import PracticeDefinitionGenerator
from app.modules.learning.infrastructure.repositories import SqlAlchemyLearningRepository
from app.modules.pbl.public import PblStudentInsightReadPort
from app.platform.transactions import SqlAlchemyUnitOfWork


def learning_application(
    session: Session, *, case_attempts: CaseAttemptPort, learning_evidence=None
) -> LearningApplication:
    return LearningApplication(
        repository=SqlAlchemyLearningRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
        practice_generator=PracticeDefinitionGenerator(),
        case_attempts=case_attempts,
        learning_evidence=learning_evidence,
    )


def knowledge_review_application(session: Session) -> KnowledgeReviewApplication:
    return KnowledgeReviewApplication(
        SqlAlchemyReviewRepository(session),
        knowledge_catalog_port(session),
    )


def learning_evidence_application(session: Session) -> LearningEvidenceApplication:
    from app.modules.learning.infrastructure.route_repository import SqlLearningRouteStore

    return LearningEvidenceApplication(
        SqlAlchemyEvidenceRepository(session),
        SqlAlchemyUnitOfWork(session),
        knowledge_catalog_port(session),
        SqlLearningRouteStore(session),
    )


def learning_evidence_port(session: Session):
    return learning_evidence_application(session)


def learning_route_application(session: Session, *, inference=None):
    from app.core.config import get_settings
    from app.modules.learning.application.learning_routes import LearningRouteApplication
    from app.modules.learning.infrastructure.route_repository import SqlLearningRouteStore

    return LearningRouteApplication(
        SqlLearningRouteStore(session, get_settings().pbl_ai_timeout_seconds),
        SqlAlchemyUnitOfWork(session),
        knowledge_catalog_port(session),
        classroom_scope_port(session),
        inference,
        learning_evidence_port(session),
    )


class LearningRouteGenerationDispatch:
    def __init__(self, session_factory, application_builder):
        self.session_factory = session_factory
        self.application_builder = application_builder

    def generate(self, route_id: str, component="route", token=None):
        # Only immutable locators cross the response boundary; never retain a request Session.
        with self.session_factory() as session:
            self.application_builder(session).generate(route_id, component, token)

    def grade(self, test_id: str):
        with self.session_factory() as session:
            self.application_builder(session).grade(test_id)


def learning_route_generation_dispatch(session: Session, application_builder):
    from sqlalchemy.orm import sessionmaker

    return LearningRouteGenerationDispatch(
        sessionmaker(bind=session.get_bind(), expire_on_commit=False), application_builder
    )


def learning_route_result_read_port(session: Session):
    from app.modules.learning.infrastructure.route_repository import SqlLearningRouteStore

    return SqlLearningRouteStore(session)


def student_learning_insights_application(
    session: Session, pbl_insight_read_port: PblStudentInsightReadPort
):
    from app.modules.learning.application.student_insights import StudentLearningInsightsApplication
    from app.modules.learning.infrastructure.route_repository import SqlLearningRouteStore

    return StudentLearningInsightsApplication(
        SqlLearningRouteStore(session),
        pbl_insight_read_port,
        knowledge_catalog_port(session),
    )
