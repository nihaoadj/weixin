from sqlalchemy.orm import Session

from app.modules.analytics.application.classroom_reports import ClassroomReportAnalytics
from app.modules.analytics.application.teacher_insights import TeacherInsights
from app.modules.analytics.application.use_cases import AnalyticsApplication
from app.modules.analytics.infrastructure.reader import SqlAlchemyAnalyticsReader
from app.modules.content.wiring import knowledge_catalog_port
from app.modules.learning.wiring import learning_evidence_port, learning_route_result_read_port
from app.modules.pbl.wiring import pbl_classroom_participation_port, pbl_teacher_diagnosis_read_port


def analytics_application(session: Session) -> AnalyticsApplication:
    return AnalyticsApplication(
        SqlAlchemyAnalyticsReader(session),
        knowledge_catalog_port(session),
        evidence_reader=learning_evidence_port(session),
    )


def classroom_report_analytics(session: Session) -> ClassroomReportAnalytics:
    return ClassroomReportAnalytics(
        SqlAlchemyAnalyticsReader(session),
        learning_route_result_read_port(session),
        pbl_classroom_participation_port(session),
    )


def teacher_insights_application(session: Session) -> TeacherInsights:
    return TeacherInsights(
        SqlAlchemyAnalyticsReader(session),
        learning_route_result_read_port(session),
        pbl_teacher_diagnosis_read_port(session),
    )
