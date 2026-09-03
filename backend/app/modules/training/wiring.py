from sqlalchemy.orm import Session

from app.modules.training.application.ports import AssessmentGateway, PatientReplyGateway
from app.modules.training.application.use_cases import TrainingApplication
from app.modules.training.infrastructure.ai_gateway import CaseAiGateway
from app.modules.training.infrastructure.repositories import SqlAlchemyTrainingRepository
from app.platform.transactions import SqlAlchemyUnitOfWork


def training_application(
    session: Session,
    *,
    patient_gateway: PatientReplyGateway | None = None,
    assessment_gateway: AssessmentGateway | None = None,
) -> TrainingApplication:
    gateway = CaseAiGateway()
    return TrainingApplication(
        repository=SqlAlchemyTrainingRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
        patient_gateway=patient_gateway or gateway,
        assessment_gateway=assessment_gateway or gateway,
    )
