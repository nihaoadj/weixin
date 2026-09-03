"""Compatibility exports for content and QA question HTTP schemas."""

from app.modules.content.api.schemas import *  # noqa: F401,F403
from app.modules.qa.api.question_schemas import (  # noqa: F401
    QuestionThreadRead,
    QuestionThreadUpsert,
    StudentQuestionPage,
    StudentQuestionRead,
)
