"""The sole application-wide ORM registration assembly.

Alembic and ``Base.metadata.create_all`` import this registry so every module
model is loaded without making domain/application code depend on the registry.
"""

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom, MedicalReview
from app.modules.content.infrastructure.models import (
    KnowledgeCardContribution,
    KnowledgeCatalog,
    KnowledgeDependency,
    KnowledgeDependencySource,
    KnowledgeModule,
    KnowledgePoint,
    KnowledgePointSource,
    KnowledgeSource,
    KnowledgeStudyMaterial,
    Problem,
    ProblemKnowledgeLink,
    ProblemOrigin,
)
from app.modules.content.infrastructure.question_bank_models import (
    BankArchiveReceipt,
    BankImportReceipt,
    TeacherQuestionBankItem,
    TeacherQuestionBankRevision,
)
from app.modules.content.infrastructure.question_review_models import ClassroomQuestionReview
from app.modules.identity.infrastructure.models import User
from app.modules.learning.infrastructure.evidence_models import LearningEvidenceEvent, LearningEvidenceMetric
from app.modules.learning.infrastructure.models import (
    LearningPlan,
    LearningPlanEvaluation,
    LearningTask,
    LearningTaskAttempt,
    ReviewAttempt,
    ReviewItem,
    ReviewState,
    StudentNotification,
)
from app.modules.learning.infrastructure.package_models import (
    ClassroomFinalReport,
    ClassroomPackageItem,
    ClassroomTaskPackage,
    T43LegacyPlanMapping,
    TeachingCommandReceipt,
)
from app.modules.learning.infrastructure.route_models import (
    LearningRoute,
    LearningRouteStep,
    RouteCaseMessage,
    RouteCasePhaseDecision,
    RouteCaseSession,
    RouteCommandReceipt,
    RouteFinalTest,
    RouteLearningResult,
    RouteReadingProgress,
    RouteTestAttempt,
    RouteTestQuestion,
    RouteTestReviewEvent,
    RouteTestTutorMessage,
    RouteTestTutorSession,
)
from app.modules.learning.infrastructure.study_models import StudyPath, StudyPracticeAttempt, StudyPracticeGroup
from app.modules.pbl.infrastructure.models import (
    PblDiagnosticSnapshot,
    PblMessage,
    PblParticipation,
    PblPrivateFollowUpResult,
    PblQuestionSuggestion,
    PblSession,
    PblSubmission,
    PblTeacherFeedback,
)
from app.modules.qa.infrastructure.models import (
    Conversation,
    ConversationLearningContext,
    Message,
    QuestionThread,
    QuestionThreadMessage,
)
from app.modules.reports.infrastructure.models import Report, ReportKnowledgeLink
from app.modules.training.infrastructure.models import (
    AICallLog,
    CaseAssessment,
    CaseAttempt,
    CaseAttemptMessage,
    StageSubmission,
)
from app.platform.database import Base

# Keep the legacy ORM classes importable while preventing ordinary runtime
# metadata.create_all() from recreating tables retired by 0034.  The classes
# remain mapped to their Table objects for compatibility; active models have
# no foreign keys into this retired set.
_RETIRED_RUNTIME_TABLES = (
    "study_practice_attempts",
    "study_practice_groups",
    "study_paths",
    "classroom_question_reviews",
    "t43_legacy_plan_mappings",
    "classroom_final_reports",
    "classroom_package_items",
    "classroom_task_packages",
    "teaching_command_receipts",
    "pbl_question_suggestions",
    "pbl_submissions",
    "pbl_teacher_feedbacks",
)

for _table_name in _RETIRED_RUNTIME_TABLES:
    _table = Base.metadata.tables.get(_table_name)
    if _table is not None:
        Base.metadata.remove(_table)

__all__ = [
    "LearningRoute",
    "LearningRouteStep",
    "RouteReadingProgress",
    "RouteCaseSession",
    "RouteCaseMessage",
    "RouteCasePhaseDecision",
    "RouteFinalTest",
    "RouteTestQuestion",
    "RouteTestAttempt",
    "RouteLearningResult",
    "RouteTestReviewEvent",
    "RouteTestTutorMessage",
    "RouteTestTutorSession",
    "RouteCommandReceipt",
    "AICallLog",
    "CaseAssessment",
    "CaseAttempt",
    "CaseAttemptMessage",
    "BankImportReceipt",
    "BankArchiveReceipt",
    "ClassMember",
    "ClassRoom",
    "ClassroomFinalReport",
    "ClassroomPackageItem",
    "ClassroomQuestionReview",
    "ClassroomTaskPackage",
    "Conversation",
    "ConversationLearningContext",
    "LearningPlan",
    "LearningPlanEvaluation",
    "LearningEvidenceEvent",
    "LearningEvidenceMetric",
    "LearningTask",
    "LearningTaskAttempt",
    "KnowledgeCardContribution",
    "KnowledgeCatalog",
    "KnowledgeDependency",
    "KnowledgeDependencySource",
    "KnowledgeModule",
    "KnowledgePoint",
    "KnowledgePointSource",
    "KnowledgeSource",
    "KnowledgeStudyMaterial",
    "MedicalReview",
    "Message",
    "Problem",
    "ProblemKnowledgeLink",
    "ProblemOrigin",
    "PblDiagnosticSnapshot",
    "PblMessage",
    "PblParticipation",
    "PblPrivateFollowUpResult",
    "PblQuestionSuggestion",
    "PblSession",
    "PblSubmission",
    "PblTeacherFeedback",
    "QuestionThread",
    "QuestionThreadMessage",
    "Report",
    "ReportKnowledgeLink",
    "ReviewAttempt",
    "ReviewItem",
    "ReviewState",
    "StageSubmission",
    "StudentNotification",
    "T43LegacyPlanMapping",
    "TeacherQuestionBankItem",
    "TeacherQuestionBankRevision",
    "TeachingCommandReceipt",
    "StudyPath",
    "StudyPracticeAttempt",
    "StudyPracticeGroup",
    "User",
]
