from sqlalchemy.orm import Session

from app.modules.analytics.application.use_cases import AnalyticsApplication
from app.modules.analytics.infrastructure.reader import SqlAlchemyAnalyticsReader


def analytics_application(session: Session) -> AnalyticsApplication:
    return AnalyticsApplication(SqlAlchemyAnalyticsReader(session))
