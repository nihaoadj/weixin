"""Teacher question bank commands are committed as one content transaction."""

from typing import Protocol

from app.modules.learning.public import RouteTestQuestionSourcePort
from app.shared.uow import UnitOfWork


class TeacherQuestionBankRepository(Protocol):
    def import_item(
        self,
        teacher_id: int,
        source_type: str,
        source_id: str,
        source_digest: str,
        client_request_id: str,
        deidentified: bool,
        content: dict[str, object],
    ) -> dict[str, object]: ...

    def get(self, teacher_id: int, bank_item_id: int) -> dict[str, object]: ...
    def list(
        self,
        teacher_id: int,
        status: str,
        point_code: str | None,
        task_type: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, object]: ...
    def update(
        self, teacher_id: int, bank_item_id: int, version: int, content: dict[str, object]
    ) -> dict[str, object]: ...
    def archive(
        self, teacher_id: int, bank_item_id: int, version: int, client_request_id: str
    ) -> dict[str, object]: ...


class TeacherQuestionBankApplication:
    def __init__(
        self,
        repository: TeacherQuestionBankRepository,
        uow: UnitOfWork,
        sources: RouteTestQuestionSourcePort,
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._sources = sources

    def source(self, teacher_id: int, question_id: str) -> dict[str, object]:
        source = self._sources.bank_source(teacher_id, question_id)
        fields = (
            "source_type",
            "source_id",
            "source_digest",
            "task_type",
            "title",
            "prompt",
            "options",
            "answer",
            "explanation",
            "point_codes",
            "dimension_ids",
        )
        return {field: source[field] for field in fields}

    def import_item(self, *args, **kwargs) -> dict[str, object]:
        result = self._repository.import_item(*args, **kwargs)
        self._uow.commit()
        return result

    def get(self, teacher_id: int, bank_item_id: int) -> dict[str, object]:
        return self._repository.get(teacher_id, bank_item_id)

    def list(self, *args, **kwargs) -> dict[str, object]:
        return self._repository.list(*args, **kwargs)

    def update(self, *args, **kwargs) -> dict[str, object]:
        result = self._repository.update(*args, **kwargs)
        self._uow.commit()
        return result

    def archive(self, *args, **kwargs) -> dict[str, object]:
        result = self._repository.archive(*args, **kwargs)
        self._uow.commit()
        return result


__all__ = ["TeacherQuestionBankApplication"]
