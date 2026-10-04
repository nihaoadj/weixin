from sqlalchemy.orm import Session

from app.modules.content.domain.digest import case_digest
from app.modules.content.infrastructure.repositories import SqlAlchemyProblemRepository
from app.shared.errors import AppError


class SqlAlchemyQuestionPublication:
    def __init__(self, session: Session) -> None:
        self._session = session

    def case_context(self, case_id: int, class_code: str, topic_code: str, teacher_id: int) -> dict[str, object]:
        repository = SqlAlchemyProblemRepository(self._session)
        case = repository.get(case_id)
        if (
            case is None
            or case.content_type != "guided_case"
            or case.status == "deleted"
            or case.author_id not in (None, teacher_id)
            or not case.case_definition
            or not case.rubric
            or not any(code.startswith(topic_code + ".") for code in case.knowledge_point_codes)
            or not (case.target == "all" or case.target == "class" and class_code in case.target_ids)
        ):
            raise AppError("VALIDATION_ERROR", "请选择本班可使用的病理学病例", 422)
        digest = case_digest(case)
        return {
            "case_id": case.id,
            "case_version": case.version,
            "case_digest": digest,
            "case_context": {"title": case.title, "opening": (case.case_definition or {}).get("opening", {})},
        }
