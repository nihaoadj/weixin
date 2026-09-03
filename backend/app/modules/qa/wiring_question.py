"""Compatibility import for callers that used the early question-only wiring path."""

from app.modules.qa.wiring import questions_application

__all__ = ["questions_application"]
