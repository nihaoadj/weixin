"""Stable, framework-neutral contracts shared by backend modules."""

from app.shared.actor import Actor
from app.shared.errors import AppError, PersistenceConflict, ResourceAmbiguous
from app.shared.uow import UnitOfWork

__all__ = ["Actor", "AppError", "PersistenceConflict", "ResourceAmbiguous", "UnitOfWork"]
