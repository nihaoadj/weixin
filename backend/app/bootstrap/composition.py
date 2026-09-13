"""HTTP-facing composition root for cross-module application contracts."""

from sqlalchemy.orm import Session

from app.modules.learning.application.knowledge_review import KnowledgeReviewApplication
from app.modules.learning.application.study import StudyApplication
from app.modules.learning.application.use_cases import LearningApplication
from app.modules.learning.infrastructure.case_attempt_adapter import TrainingCaseAttemptAdapter
from app.modules.learning.wiring import knowledge_review_application as build_knowledge_review_application
from app.modules.learning.wiring import learning_application as build_learning_application
from app.modules.training.application.ports import AssessmentGateway, PatientReplyGateway
from app.modules.training.application.use_cases import TrainingApplication
from app.modules.training.public import CaseAttemptContract, TrainingCasePort, attempt_contract
from app.modules.training.wiring import training_application as build_training_application
from app.shared.actor import Actor


class TrainingPublicAdapter(TrainingCasePort):
    """Adapt training's internal application records to its public contract."""

    def __init__(self, application: TrainingApplication) -> None:
        self._application = application

    def start(
        self, actor: Actor, problem_id: int, retry_of_id: int | None, learning_task_id: int
    ) -> CaseAttemptContract:
        return attempt_contract(self._application.start(actor, problem_id, retry_of_id, learning_task_id))

    def get(self, actor: Actor, attempt_id: int) -> CaseAttemptContract:
        return attempt_contract(self._application.get(actor, attempt_id))


def training_application(
    session: Session,
    *,
    patient_gateway: PatientReplyGateway | None = None,
    assessment_gateway: AssessmentGateway | None = None,
) -> TrainingApplication:
    """Compose the training application; optional ports are test seams."""

    return build_training_application(
        session,
        patient_gateway=patient_gateway,
        assessment_gateway=assessment_gateway,
    )


def learning_application(session: Session) -> LearningApplication:
    """Compose learning with the explicit training public port."""

    training = TrainingPublicAdapter(training_application(session))
    return build_learning_application(
        session,
        case_attempts=TrainingCaseAttemptAdapter(training),
    )


def knowledge_review_application(session: Session) -> KnowledgeReviewApplication:
    return build_knowledge_review_application(session)


def study_application(session: Session) -> StudyApplication:
    """Compose the T20 learning path at the single cross-module root."""
    from app.modules.classroom.wiring import classroom_scope_port
    from app.modules.learning.infrastructure.study_practice_generator import StudyPracticeGenerator
    from app.modules.learning.infrastructure.study_repository import SqlStudyRepository
    from app.modules.pbl.infrastructure.repositories import SqlAlchemyPblRepository
    from app.modules.pbl.infrastructure.study_dialogues import StudyDialogues
    from app.modules.pbl.wiring import pbl_application, practice_json_port
    from app.platform.transactions import SqlAlchemyUnitOfWork

    return StudyApplication(
        SqlStudyRepository(session),
        StudyDialogues(pbl_application(session), SqlAlchemyPblRepository(session, classroom_scope_port(session))),
        StudyPracticeGenerator(practice_json_port()),
        SqlAlchemyUnitOfWork(session),
    )
