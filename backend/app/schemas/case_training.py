"""Compatibility exports for training HTTP and provider schemas."""

from app.modules.training.api.schemas import *  # noqa: F401,F403
from app.modules.training.infrastructure.ai_schemas import (  # noqa: F401
    AIAssessmentDimension,
    AIAssessmentResponse,
    PatientReplyModel,
)
