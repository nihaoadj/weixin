from __future__ import annotations

import builtins
from copy import deepcopy
from dataclasses import replace

from app.modules.content.application.ports import CaseDraftAudit, CaseDraftGenerator, ProblemRepository
from app.modules.content.application.records import (
    CaseDraftResult,
    KnowledgeCardContributionCommand,
    KnowledgeCardContributionRecord,
    ProblemCommand,
    ProblemRecord,
    ReviewRecord,
)
from app.modules.content.domain.policy import ContentPolicy
from app.modules.content.public import KnowledgeCatalogPort
from app.modules.training.public import CaseSnapshotPort
from app.shared.actor import Actor
from app.shared.errors import AppError
from app.shared.uow import UnitOfWork


class ContentApplication:
    def __init__(
        self,
        repository: ProblemRepository,
        uow: UnitOfWork,
        knowledge_catalog: KnowledgeCatalogPort,
        policy: ContentPolicy | None = None,
        draft_generator: CaseDraftGenerator | None = None,
        draft_audit: CaseDraftAudit | None = None,
        snapshots: CaseSnapshotPort | None = None,
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._knowledge_catalog = knowledge_catalog
        self._policy = policy or ContentPolicy()
        self._draft_generator = draft_generator
        self._draft_audit = draft_audit
        self._snapshots = snapshots

    def list(self, actor: Actor) -> tuple[ProblemRecord, ...]:
        if actor.role == "student":
            items = self._repository.list_visible_for_student(actor, self._repository.class_codes(actor.id))
        else:
            items = self._repository.list_all()
        return tuple(
            item
            for item in items
            if item.content_type == "guided_case"
            and item.status != "deleted"
            and (actor.role == "student" or item.author_id in (None, actor.id))
        )

    def allowed_actions(self, actor: Actor, problem: ProblemRecord) -> tuple[str, ...]:
        """Current UI hints; every write independently repeats its authorization."""
        if actor.role != "teacher" or problem.author_id != actor.id:
            return ()
        if problem.content_type != "guided_case" or problem.status == "deleted":
            return ()
        return ("edit", "delete")

    def teacher_action_summary(self, actor: Actor) -> dict:
        from datetime import UTC, datetime

        self._policy.require_teacher(actor)
        return {
            **self._repository.teacher_action_counts(actor.id, medical_reviewer=actor.has_permission("medical_review")),
            "as_of": datetime.now(UTC),
        }

    def get(self, actor: Actor, problem_id: int) -> ProblemRecord:
        problem = self._repository.get(problem_id)
        if problem is None or problem.content_type != "guided_case" or problem.status == "deleted":
            raise AppError("RESOURCE_NOT_FOUND", "题目不存在", 404)
        if actor.role == "student" and not self._policy.is_visible_to_student(
            status=problem.status,
            target=problem.target,
            target_ids=problem.target_ids,
            student_external_id=actor.external_id,
            class_codes=self._repository.class_codes(actor.id),
        ):
            raise AppError("RESOURCE_NOT_FOUND", "题目不存在", 404)
        return self._with_counts(problem)

    def authoring(self, actor: Actor, problem_id: int) -> ProblemRecord:
        self._policy.require_teacher(actor)
        problem = self._get(problem_id)
        if problem.content_type != "guided_case" or problem.author_id != actor.id:
            raise AppError("RESOURCE_NOT_FOUND", "内容不存在", 404)
        return self._with_counts(problem)

    def create(self, actor: Actor, command: ProblemCommand) -> ProblemRecord:
        self._policy.require_teacher(actor)
        self._require_case_flow(command.content_type)
        self._validate_problem_knowledge_links(command)
        self._policy.require_publishable_case(command.case_definition, command.rubric)
        problem = self._repository.create(actor.id, self._normalize_command(command))
        self._uow.commit()
        return self._with_counts(problem)

    def update(self, actor: Actor, problem_id: int, command: ProblemCommand) -> ProblemRecord:
        self._policy.require_teacher(actor)
        problem = self._get(problem_id)
        self._policy.require_owner(actor, problem.author_id)
        self._require_case_flow(problem.content_type)
        self._require_case_flow(command.content_type)
        if problem.content_type != command.content_type:
            raise AppError("STATE_CONFLICT", "Content type is immutable", 409)
        if command.preserve_knowledge_point_codes:
            command = replace(command, knowledge_point_codes=problem.knowledge_point_codes)
        self._validate_problem_knowledge_links(command)
        self._policy.require_publishable_case(command.case_definition, command.rubric)
        if self._snapshots is not None:
            self._snapshots.freeze(problem_id)
        updated = self._repository.update(problem_id, actor.id, self._normalize_command(command))
        self._uow.commit()
        return self._with_counts(updated)

    def delete(self, actor: Actor, problem_id: int) -> None:
        self._policy.require_teacher(actor)
        problem = self._repository.get(problem_id)
        if problem is None:
            raise AppError("RESOURCE_NOT_FOUND", "病例不存在", 404)
        self._policy.require_owner(actor, problem.author_id)
        self._require_case_flow(problem.content_type)
        if problem.status != "deleted":
            if self._snapshots is not None:
                self._snapshots.freeze(problem_id)
            self._repository.delete(problem_id)
            self._uow.commit()

    def clone(self, actor: Actor, problem_id: int) -> ProblemRecord:
        self._require_retired_case_owner(actor, problem_id)
        self._retired_case_workflow()

    def publish(self, actor: Actor, problem_id: int) -> ProblemRecord:
        self._require_retired_case_owner(actor, problem_id)
        self._retired_case_workflow()

    def reject(self, actor: Actor, problem_id: int) -> ProblemRecord:
        self._require_retired_case_owner(actor, problem_id)
        self._retired_case_workflow()

    def _require_retired_case_owner(self, actor: Actor, problem_id: int) -> None:
        self._policy.require_teacher(actor)
        problem = self._get(problem_id)
        self._policy.require_owner(actor, problem.author_id)
        self._require_case_flow(problem.content_type)

    @staticmethod
    def _retired_case_workflow() -> None:
        raise AppError("RETIRED_FLOW", "病例已改为教师直接维护，无需审核或发布", 409)

    def generate_draft(
        self, actor: Actor, topic: str, learner_level: str, objectives: builtins.list[str]
    ) -> CaseDraftResult:
        self._policy.require_teacher(actor)
        if self._draft_generator is None or self._draft_audit is None:
            raise AppError("SERVICE_ERROR", "病例草稿生成器不可用", 503)
        try:
            result = self._draft_generator.generate(topic, learner_level, objectives, actor.id)
            self._draft_audit.record_ai_call(
                user_id=actor.id,
                model_name=result.model_name,
                prompt_version=result.prompt_version,
                latency_ms=result.latency_ms,
                fallback_used=result.fallback_used,
                failure_reason=result.failure_reason,
            )
            self._uow.commit()
            return result
        except AppError:
            self._uow.rollback()
            raise
        except Exception as error:
            self._uow.rollback()
            raise AppError("SERVICE_ERROR", "AI audit is temporarily unavailable", 503) from error

    def review_queue(self, actor: Actor, status: str) -> tuple[ProblemRecord, ...]:
        if actor.role != "teacher" or not actor.has_permission("medical_review"):
            raise AppError("FORBIDDEN", "没有审核权限", 403)
        return ()

    def submit_review(self, actor: Actor, problem_id: int) -> ProblemRecord:
        self._require_retired_case_owner(actor, problem_id)
        self._retired_case_workflow()

    def decide_review(self, actor: Actor, problem_id: int, decision: str, comment: str) -> ProblemRecord:
        if actor.role != "teacher" or not actor.has_permission("medical_review"):
            raise AppError("FORBIDDEN", "没有审核权限", 403)
        problem = self._get(problem_id)
        self._require_case_flow(problem.content_type)
        self._retired_case_workflow()

    def review_view(self, actor: Actor, problem_id: int) -> tuple[ProblemRecord, str | None, tuple[ReviewRecord, ...]]:
        if actor.role != "teacher" or not actor.has_permission("medical_review"):
            raise AppError("FORBIDDEN", "没有审核权限", 403)
        problem = self.get(actor, problem_id)
        return self._repository.review_view(problem.id)

    def review_history(self, actor: Actor, problem_id: int) -> tuple[ReviewRecord, ...]:
        self._policy.require_teacher(actor)
        problem = self._repository.get(problem_id)
        if problem is None or problem.content_type != "guided_case":
            raise AppError("RESOURCE_NOT_FOUND", "病例不存在", 404)
        if problem.author_id != actor.id and not actor.has_permission("medical_review"):
            raise AppError("FORBIDDEN", "没有审核权限", 403)
        return self._repository.review_history(problem.id)

    def list_knowledge_cards(
        self, actor: Actor, point_code: str | None = None
    ) -> tuple[KnowledgeCardContributionRecord, ...]:
        if actor.role != "student":
            self._policy.require_teacher(actor)
        if point_code is not None and self._knowledge_catalog.point_view(point_code) is None:
            raise AppError("RESOURCE_NOT_FOUND", "知识点不存在", 404)
        return ()

    def create_knowledge_card(
        self, actor: Actor, command: KnowledgeCardContributionCommand
    ) -> KnowledgeCardContributionRecord:
        self._policy.require_teacher(actor)
        self._retired_knowledge_cards()

    def knowledge_card_review_queue(self, actor: Actor) -> tuple[KnowledgeCardContributionRecord, ...]:
        if actor.role != "teacher" or not actor.has_permission("medical_review"):
            raise AppError("FORBIDDEN", "没有医学审核权限", 403)
        return ()

    def update_knowledge_card(
        self, actor: Actor, card_id: int, command: KnowledgeCardContributionCommand
    ) -> KnowledgeCardContributionRecord:
        self._require_card_owner(actor, card_id)
        self._retired_knowledge_cards()

    def submit_knowledge_card(self, actor: Actor, card_id: int) -> KnowledgeCardContributionRecord:
        self._require_card_owner(actor, card_id)
        self._retired_knowledge_cards()

    def decide_knowledge_card(
        self, actor: Actor, card_id: int, decision: str, comment: str
    ) -> KnowledgeCardContributionRecord:
        self._require_card_reviewer(actor)
        self._retired_knowledge_cards()

    def disable_knowledge_card(self, actor: Actor, card_id: int) -> KnowledgeCardContributionRecord:
        self._require_card_reviewer(actor)
        self._retired_knowledge_cards()

    def _require_card_owner(self, actor: Actor, card_id: int) -> None:
        self._policy.require_teacher(actor)
        card = self._repository.get_knowledge_card(card_id)
        if card is None or card.owner_id != actor.id:
            raise AppError("RESOURCE_NOT_FOUND", "补充卡不存在", 404)

    @staticmethod
    def _require_card_reviewer(actor: Actor) -> None:
        if actor.role != "teacher" or not actor.has_permission("medical_review"):
            raise AppError("FORBIDDEN", "没有医学审核权限", 403)

    @staticmethod
    def _retired_knowledge_cards() -> None:
        raise AppError("RETIRED_FLOW", "教师知识补充卡已退役，请使用病例库或个人题库", 409)

    @staticmethod
    def _require_case_flow(content_type: str) -> None:
        if content_type != "guided_case":
            raise AppError("RETIRED_FLOW", "开放讨论题已退役，请使用病例库", 409)

    def _get(self, problem_id: int) -> ProblemRecord:
        problem = self._repository.get(problem_id)
        if problem is None or problem.status == "deleted":
            raise AppError("RESOURCE_NOT_FOUND", "题目不存在", 404)
        return problem

    def _with_counts(self, problem: ProblemRecord) -> ProblemRecord:
        counts = self._repository.answer_counts([problem.id])
        return replace(problem, answer_count=counts.get(problem.id, problem.answer_count))

    @staticmethod
    def _normalize_command(command: ProblemCommand) -> ProblemCommand:
        case_definition = deepcopy(command.case_definition)
        if case_definition and case_definition.get("schema_version") == 1:
            case_definition["schema_version"] = 2
        return ProblemCommand(
            type=command.type,
            title=command.title,
            description=command.description,
            target=command.target,
            target_label=command.target_label,
            target_ids=command.target_ids,
            content_type=command.content_type,
            slug=command.slug,
            specialty=command.specialty,
            difficulty=command.difficulty,
            estimated_minutes=command.estimated_minutes,
            version=command.version,
            parent_problem_id=command.parent_problem_id,
            case_definition=case_definition,
            rubric=command.rubric,
            capability_tags=command.capability_tags,
            status=command.status,
            knowledge_point_codes=command.knowledge_point_codes,
        )

    def _validate_problem_knowledge_links(self, command: ProblemCommand) -> None:
        if len(command.knowledge_point_codes) > 3 or not self._knowledge_catalog.contains_points(
            command.knowledge_point_codes
        ):
            raise AppError("VALIDATION_ERROR", "题目知识点绑定无效", 422)
