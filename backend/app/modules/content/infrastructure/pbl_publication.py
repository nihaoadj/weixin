from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.content.domain.digest import case_digest
from app.modules.content.domain.templates import DIALOGUE_REASONING_BLUEPRINTS
from app.modules.content.infrastructure.models import (
    KnowledgeCardContribution,
    Problem,
    ProblemKnowledgeLink,
    ProblemOrigin,
)
from app.modules.content.infrastructure.repositories import SqlAlchemyProblemRepository
from app.modules.content.public import PublishedQuestionRecord, PublishQuestionCommand
from app.shared.errors import AppError


class SqlAlchemyQuestionPublication:
    def __init__(self, session: Session) -> None:
        self._session = session

    def adopt_open_question(self, command: PublishQuestionCommand) -> PublishedQuestionRecord:
        existing = self._session.scalar(
            select(ProblemOrigin).where(
                ProblemOrigin.source_type == "pbl_suggestion", ProblemOrigin.source_id == command.source_id
            )
        )
        if existing is not None:
            return PublishedQuestionRecord(problem_id=existing.problem_id)
        problem = Problem(
            type="open_discussion",
            title=command.title,
            description=command.prompt,
            target="individual" if command.target_external_ids else "class",
            target_label=command.class_code,
            target_ids=",".join(command.target_external_ids) if command.target_external_ids else command.class_code,
            status="published",
            content_type="question",
            specialty="pathology",
            difficulty="basic",
            estimated_minutes=10,
            version=1,
            author_id=command.teacher_id,
        )
        problem.knowledge_links = [ProblemKnowledgeLink(point_code=code) for code in command.point_codes]
        self._session.add(problem)
        self._session.flush()
        self._session.add(
            ProblemOrigin(problem_id=problem.id, source_type="pbl_suggestion", source_id=command.source_id)
        )
        self._session.flush()
        return PublishedQuestionRecord(problem_id=problem.id)

    def case_context(self, case_id: int, class_code: str, topic_code: str) -> dict[str, object]:
        repository = SqlAlchemyProblemRepository(self._session)
        case = repository.get(case_id)
        if (
            case is None
            or case.content_type != "guided_case"
            or case.status != "published"
            or case.medical_review_status != "approved"
            or not any(code.startswith(topic_code + ".") for code in case.knowledge_point_codes)
            or not (case.target == "all" or case.target == "class" and class_code in case.target_ids)
        ):
            raise AppError("VALIDATION_ERROR", "请选择本班可使用、已审核发布的病理学病例", 422)
        digest = case_digest(case)
        if repository.latest_approved_review_digest(case.id) != digest:
            raise AppError("STATE_CONFLICT", "病例版本已改变，请重新审核", 409)
        return {
            "case_id": case.id,
            "case_version": case.version,
            "case_digest": digest,
            "case_context": {"title": case.title, "opening": (case.case_definition or {}).get("opening", {})},
        }

    def task_resources(self, case_id: int | None, point_codes: tuple[str, ...], dimensions: tuple[str, ...]):
        # These are internal task definitions; answer keys are stripped from student DTOs by learning.
        resources = []
        for point in point_codes:
            for cycle in (1, 2):
                for kind in ("practice", "retest"):
                    code = f"{point}.{kind}" + (".v2" if cycle == 2 else "")
                    card = self._session.scalar(
                        select(KnowledgeCardContribution).where(
                            KnowledgeCardContribution.catalog_card_code == code,
                            KnowledgeCardContribution.status == "approved",
                        )
                    )
                    if card is None:
                        raise AppError("STATE_CONFLICT", "该知识点的两轮巩固卡或再测卡尚未审核", 409)
                    resources.append(
                        {
                            "task_type": "knowledge_review" if kind == "practice" else "retest",
                            "dimension_id": "knowledge",
                            "cycle_number": cycle,
                            "target_type": "knowledge_gap",
                            "target_code": point,
                            "variant_code": code,
                            "point_code": point,
                            "card_code": card.catalog_card_code,
                            "prompt": card.prompt,
                            "options": list(card.options),
                            "private_rubric": {"correct_option": card.correct_option, "explanation": card.explanation},
                            "reference": card.reference,
                        }
                    )
        case = SqlAlchemyProblemRepository(self._session).get(case_id) if case_id else None
        for dimension in dimensions:
            blueprint = (
                next(
                    (
                        b
                        for b in (case.case_definition or {}).get("practice_blueprints", [])
                        if b["dimension_id"] == dimension
                    ),
                    None,
                )
                if case
                else DIALOGUE_REASONING_BLUEPRINTS.get(dimension)
            )
            if not blueprint or not blueprint.get("reinforcement_prompt") or not blueprint.get(
                "reinforcement_variant_code"
            ):
                raise AppError("STATE_CONFLICT", "该推理目标的两轮微训练尚未审核", 409)
            for cycle, prompt, variant in (
                (1, blueprint["fallback_prompt"], blueprint["id"] + ".v1"),
                (2, blueprint["reinforcement_prompt"], blueprint["reinforcement_variant_code"]),
            ):
                resources.append(
                    {
                        "task_type": "micro_drill",
                        "dimension_id": dimension,
                        "cycle_number": cycle,
                        "target_type": "reasoning_issue",
                        "target_code": dimension,
                        "variant_code": variant,
                        "stage_id": blueprint["stage_id"],
                        "prompt": prompt,
                        "private_rubric": {"criteria": blueprint["criteria"]},
                        "answer_schema": blueprint["answer_schema"],
                    }
                )
        return tuple(resources)
