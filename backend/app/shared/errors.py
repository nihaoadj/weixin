from __future__ import annotations


class AppError(Exception):
    """A transport-neutral application failure mapped by the HTTP boundary."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class PersistenceConflict(Exception):
    """A database uniqueness/race conflict that an application maps to 409."""


class ResourceAmbiguous(Exception):
    """A legacy lookup key matched more than one visible resource."""
