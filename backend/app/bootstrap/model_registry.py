"""The sole application-wide ORM registration assembly.

Alembic and ``Base.metadata.create_all`` import this registry so every module
model is loaded without making domain/application code depend on the registry.
"""

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom, MedicalReview
from app.modules.content.infrastructure.models import (
    KnowledgeCardContribution,
    Problem,
    ProblemKnowledgeLink,
    ProblemOrigin,
)
from app.modules.identity.infrastructure.models import User
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
from app.modules.learning.infrastructure.study_models import StudyPath, StudyPracticeAttempt, StudyPracticeGroup
from app.modules.pbl.infrastructure.models import (
    PblDiagnosticSnapshot,
    PblMessage,
    PblParticipation,
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

__all__ = [
    "AICallLog",
    "CaseAssessment",
    "CaseAttempt",
    "CaseAttemptMessage",
    "ClassMember",
    "ClassRoom",
    "Conversation",
    "ConversationLearningContext",
    "LearningPlan",
    "LearningPlanEvaluation",
    "LearningTask",
    "LearningTaskAttempt",
    "KnowledgeCardContribution",
    "MedicalReview",
    "Message",
    "Problem",
    "ProblemKnowledgeLink",
    "ProblemOrigin",
    "PblDiagnosticSnapshot",
    "PblMessage",
    "PblParticipation",
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
    "StudyPath",
    "StudyPracticeAttempt",
    "StudyPracticeGroup",
    "User",
]
