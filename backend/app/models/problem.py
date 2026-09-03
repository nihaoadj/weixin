"""Legacy import paths for content and QA ORM models."""

from app.modules.content.infrastructure.models import Problem
from app.modules.qa.infrastructure.models import QuestionThread, QuestionThreadMessage

__all__ = ["Problem", "QuestionThread", "QuestionThreadMessage"]
