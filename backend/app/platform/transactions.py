from __future__ import annotations

from sqlalchemy.orm import Session


class SqlAlchemyUnitOfWork:
    """A request-scoped UoW; repositories never commit or rollback themselves."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def flush(self) -> None:
        self._session.flush()

    def commit(self) -> None:
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def rollback(self) -> None:
        self._session.rollback()
