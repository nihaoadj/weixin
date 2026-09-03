"""SQLAlchemy's declarative base, kept separate from engine/bootstrap wiring."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared metadata base; concrete tables are owned by module adapters."""

