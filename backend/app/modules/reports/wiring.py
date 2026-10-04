from sqlalchemy.orm import Session

from app.modules.reports.application.use_cases import ReportsApplication
from app.modules.reports.infrastructure.repositories import SqlAlchemyReportRepository
from app.platform.transactions import SqlAlchemyUnitOfWork


def reports_application(session: Session) -> ReportsApplication:
    return ReportsApplication(
        SqlAlchemyReportRepository(session),
        SqlAlchemyUnitOfWork(session),
    )
