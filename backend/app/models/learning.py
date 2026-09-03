"""Legacy import paths for QA conversations and reports."""

from app.modules.qa.infrastructure.models import Conversation, Message
from app.modules.reports.infrastructure.models import Report

__all__ = ["Conversation", "Message", "Report"]
