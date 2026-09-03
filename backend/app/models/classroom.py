"""Legacy import paths; classroom ORM models are classroom-owned."""

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom, MedicalReview

__all__ = ["ClassMember", "ClassRoom", "MedicalReview"]
