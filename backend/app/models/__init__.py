"""Compatibility registry for Alembic, legacy seeds, and historical imports.

Concrete ORM ownership lives in each module's infrastructure.models file. This
package is only the application-wide metadata registration point; it contains
no table definitions or business behavior.
"""

from app.bootstrap.model_registry import (
    AICallLog,
    CaseAssessment,
    CaseAttempt,
    CaseAttemptMessage,
    ClassMember,
    ClassRoom,
    Conversation,
    LearningPlan,
    LearningTask,
    LearningTaskAttempt,
    MedicalReview,
    Message,
    Problem,
    QuestionThread,
    QuestionThreadMessage,
    Report,
    StageSubmission,
    StudentNotification,
    User,
)

__all__ = [
    "Conversation",
    "Message",
    "Problem",
    "QuestionThread",
    "QuestionThreadMessage",
    "Report",
    "User",
    "AICallLog",
    "CaseAssessment",
    "CaseAttempt",
    "CaseAttemptMessage",
    "StageSubmission",
    "ClassRoom",
    "ClassMember",
    "MedicalReview",
    "LearningPlan",
    "LearningTask",
    "LearningTaskAttempt",
    "StudentNotification",
]
