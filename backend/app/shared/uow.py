from __future__ import annotations

from typing import Protocol


class UnitOfWork(Protocol):
    """The transaction contract owned by an application use case."""

    def flush(self) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
