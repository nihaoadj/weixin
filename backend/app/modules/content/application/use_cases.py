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
from app.modules.content.domain.digest import case_digest
from app.modules.content.domain.knowledge_catalog import point_view
from app.modules.content.domain.policy import ContentPolicy
from app.shared.actor import Actor
from app.shared.errors import AppError, PersistenceConflict
from app.shared.uow import UnitOfWork


class ContentApplication:
    def __init__(
        self,
        repository: ProblemRepository,
        uow: UnitOfWork,
        policy: ContentPolicy | None = None,
        draft_generator: CaseDraftGenerator | None = None,
        draft_audit: CaseDraftAudit | None = None,
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._policy = policy or ContentPolicy()
        self._draft_generator = draft_generator
        self._draft_audit = draft_audit

    def list(self, actor: Actor) -> tuple[ProblemRecord, ...]:
        if actor.role == "student":
            return self._repository.list_visible_for_student(actor, self._repository.class_codes(actor.id))
        return self._repository.list_all()

    def get(self, actor: Actor, problem_id: int) -> ProblemRecord:
        problem = self._repository.get(problem_id)
        if problem is None:
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
        self._validate_problem_knowledge_links(command)
        problem = self._repository.create(actor.id, self._normalize_command(command))
        self._uow.commit()
        return self._with_counts(problem)

    def update(self, actor: Actor, problem_id: int, command: ProblemCommand) -> ProblemRecord:
        self._policy.require_teacher(actor)
        problem = self._get(problem_id)
        if problem.content_type != command.content_type:
            raise AppError("STATE_CONFLICT", "Content type is immutable", 409)
        self._policy.require_owner(actor, problem.author_id)
        self._validate_problem_knowledge_links(command)
        if problem.content_type == "guided_case" and problem.medical_review_status == "pending":
            raise AppError("STATE_CONFLICT", "内容正在审核中", 409)
        if problem.content_type == "guided_case" and problem.status == "published":
            raise AppError("STATE_CONFLICT", "Published case is immutable; clone a new version", 409)
        if problem.content_type == "guided_case" and problem.medical_review_status == "approved":
            raise AppError("STATE_CONFLICT", "Approved case is immutable; clone a new version", 409)
        updated = self._repository.update(problem_id, actor.id, self._normalize_command(command))
        self._uow.commit()
        return self._with_counts(updated)

    def clone(self, actor: Actor, problem_id: int) -> ProblemRecord:
        self._policy.require_teacher(actor)
        problem = self._get(problem_id)
        if (
            problem.content_type != "guided_case"
            or problem.status != "published"
            or problem.medical_review_status != "approved"
        ):
            raise AppError("RESOURCE_NOT_FOUND", "病例不存在", 404)
        self._policy.require_owner(actor, problem.author_id)
        for attempt in range(2):
            try:
                clone = self._repository.clone(problem, actor.id)
                self._uow.commit()
                return self._with_counts(clone)
            except PersistenceConflict:
                self._uow.rollback()
                if attempt == 1:
                    raise AppError("STATE_CONFLICT", "Unable to allocate a unique case version", 409) from None
        raise AppError("STATE_CONFLICT", "Unable to allocate a unique case version", 409)

    def publish(self, actor: Actor, problem_id: int) -> ProblemRecord:
        self._policy.require_teacher(actor)
        problem = self._get(problem_id)
        self._policy.require_owner(actor, problem.author_id)
        if problem.content_type == "guided_case":
            self._policy.require_publishable_case(problem.case_definition, problem.rubric)
            self._policy.require_review_approved(problem.medical_review_status)
            if self._repository.latest_approved_review_digest(problem.id) != case_digest(problem):
                # This is an intentional persisted invalidation, not a rollback:
                # approval must not survive an edited case.
                self._repository.invalidate_review(problem.id)
                self._uow.commit()
                raise AppError("STATE_CONFLICT", "审核摘要已失效", 409)
        if problem.status == "published":
            return self._with_counts(problem)
        published = self._repository.publish(problem.id)
        self._uow.commit()
        return self._with_counts(published)

    def reject(self, actor: Actor, problem_id: int) -> ProblemRecord:
        self._policy.require_teacher(actor)
        problem = self._get(problem_id)
        self._policy.require_owner(actor, problem.author_id)
        if problem.content_type == "guided_case":
            raise AppError("STATE_CONFLICT", "Use medical review to reject a case", 409)
        rejected = self._repository.reject(problem.id)
        self._uow.commit()
        return self._with_counts(rejected)

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
        return tuple(self._with_counts(item) for item in self._repository.review_queue(status))

    def submit_review(self, actor: Actor, problem_id: int) -> ProblemRecord:
        self._policy.require_teacher(actor)
        problem = self._get(problem_id)
        if problem.author_id != actor.id:
            raise AppError("FORBIDDEN", "没有内容权限", 403)
        if problem.medical_review_status == "approved":
            raise AppError("STATE_CONFLICT", "病例已经审核通过", 409)
        self._policy.require_publishable_case(problem.case_definition, problem.rubric)
        result = self._repository.submit_review(problem.id, actor.id)
        self._uow.commit()
        return self._with_counts(result)

    def decide_review(self, actor: Actor, problem_id: int, decision: str, comment: str) -> ProblemRecord:
        if actor.role != "teacher" or not actor.has_permission("medical_review"):
            raise AppError("FORBIDDEN", "没有审核权限", 403)
        problem = self._get(problem_id)
        if problem.author_id == actor.id:
            raise AppError("STATE_CONFLICT", "Authors cannot review their own case", 409)
        if problem.medical_review_status != "pending":
            raise AppError("STATE_CONFLICT", "病例不在待审核状态", 409)
        result = self._repository.add_review(problem.id, actor.id, decision, comment)
        self._uow.commit()
        return self._with_counts(result)

    def review_view(self, actor: Actor, problem_id: int) -> tuple[ProblemRecord, str | None, tuple[ReviewRecord, ...]]:
        if actor.role != "teacher" or not actor.has_permission("medical_review"):
            raise AppError("FORBIDDEN", "没有审核权限", 403)
        return self._repository.review_view(self._get(problem_id).id)

    def review_history(self, actor: Actor, problem_id: int) -> tuple[ReviewRecord, ...]:
        self._policy.require_teacher(actor)
        problem = self._get(problem_id)
        if problem.author_id != actor.id and not actor.has_permission("medical_review"):
            raise AppError("FORBIDDEN", "没有审核权限", 403)
        return self._repository.review_history(problem.id)

    def list_knowledge_cards(
        self, actor: Actor, point_code: str | None = None
    ) -> tuple[KnowledgeCardContributionRecord, ...]:
        if point_code is not None and point_view(point_code) is None:
            raise AppError("RESOURCE_NOT_FOUND", "知识点不存在", 404)
        if actor.role == "student":
            return self._repository.list_visible_knowledge_cards(
                actor.id, self._repository.class_codes(actor.id), point_code
            )
        self._policy.require_teacher(actor)
        return self._repository.list_knowledge_cards_for_owner(actor.id)

    def create_knowledge_card(
        self, actor: Actor, command: KnowledgeCardContributionCommand
    ) -> KnowledgeCardContributionRecord:
        self._policy.require_teacher(actor)
        self._validate_knowledge_card(command, actor.id)
        result = self._repository.create_knowledge_card(actor.id, command)
        self._uow.commit()
        return result

    def knowledge_card_review_queue(self, actor: Actor) -> tuple[KnowledgeCardContributionRecord, ...]:
        if actor.role != "teacher" or not actor.has_permission("medical_review"):
            raise AppError("FORBIDDEN", "没有医学审核权限", 403)
        return self._repository.list_knowledge_cards_by_status("pending")

    def update_knowledge_card(
        self, actor: Actor, card_id: int, command: KnowledgeCardContributionCommand
    ) -> KnowledgeCardContributionRecord:
        self._policy.require_teacher(actor)
        existing = self._repository.get_knowledge_card(card_id)
        if existing is None or existing.owner_id != actor.id:
            raise AppError("RESOURCE_NOT_FOUND", "补充卡不存在", 404)
        if existing.status == "disabled":
            raise AppError("STATE_CONFLICT", "当前状态不能编辑补充卡", 409)
        self._validate_knowledge_card(command, actor.id)
        result = self._repository.update_knowledge_card(card_id, actor.id, command)
        self._uow.commit()
        return result

    def submit_knowledge_card(self, actor: Actor, card_id: int) -> KnowledgeCardContributionRecord:
        self._policy.require_teacher(actor)
        card = self._repository.get_knowledge_card(card_id)
        if card is None or card.owner_id != actor.id:
            raise AppError("RESOURCE_NOT_FOUND", "补充卡不存在", 404)
        if card.status not in {"draft", "rejected"}:
            raise AppError("STATE_CONFLICT", "补充卡当前不能提交审核", 409)
        result = self._repository.submit_knowledge_card(card_id)
        self._uow.commit()
        return result

    def decide_knowledge_card(
        self, actor: Actor, card_id: int, decision: str, comment: str
    ) -> KnowledgeCardContributionRecord:
        if actor.role != "teacher" or not actor.has_permission("medical_review"):
            raise AppError("FORBIDDEN", "没有医学审核权限", 403)
        card = self._repository.get_knowledge_card(card_id)
        if card is None:
            raise AppError("RESOURCE_NOT_FOUND", "补充卡不存在", 404)
        if card.owner_id == actor.id:
            raise AppError("STATE_CONFLICT", "作者不能审核自己的补充卡", 409)
        if card.status != "pending":
            raise AppError("STATE_CONFLICT", "补充卡不在待审核状态", 409)
        if decision not in {"approved", "rejected"} or len(comment) > 1000:
            raise AppError("VALIDATION_ERROR", "审核决定无效", 422)
        result = self._repository.decide_knowledge_card(card_id, actor.id, decision, comment.strip())
        self._uow.commit()
        return result

    def disable_knowledge_card(self, actor: Actor, card_id: int) -> KnowledgeCardContributionRecord:
        if actor.role != "teacher" or not actor.has_permission("medical_review"):
            raise AppError("FORBIDDEN", "没有医学审核权限", 403)
        card = self._repository.get_knowledge_card(card_id)
        if card is None:
            raise AppError("RESOURCE_NOT_FOUND", "补充卡不存在", 404)
        result = self._repository.disable_knowledge_card(card_id)
        self._uow.commit()
        return result

    def _validate_knowledge_card(self, command: KnowledgeCardContributionCommand, teacher_id: int) -> None:
        if point_view(command.point_code) is None:
            raise AppError("VALIDATION_ERROR", "知识点不存在", 422)
        if command.class_code and not self._repository.teacher_owns_class(teacher_id, command.class_code):
            raise AppError("VALIDATION_ERROR", "班级不存在或不属于当前教师", 422)
        if command.card_type not in {"single_choice", "recall"}:
            raise AppError("VALIDATION_ERROR", "不支持的补充卡类型", 422)
        if not command.prompt.strip() or len(command.prompt) > 1000 or len(command.explanation) > 2000:
            raise AppError("VALIDATION_ERROR", "补充卡内容无效", 422)
        if len(command.reference) > 500:
            raise AppError("VALIDATION_ERROR", "参考来源过长", 422)
        if command.card_type == "single_choice":
            if len(command.options) < 2 or len(command.options) > 6 or command.correct_option is None:
                raise AppError("VALIDATION_ERROR", "单选卡必须包含选项和正确答案", 422)
            if command.correct_option < 0 or command.correct_option >= len(command.options):
                raise AppError("VALIDATION_ERROR", "正确答案无效", 422)
        elif command.options or command.correct_option is not None:
            raise AppError("VALIDATION_ERROR", "回忆卡不能包含客观答案", 422)

    def _get(self, problem_id: int) -> ProblemRecord:
        problem = self._repository.get(problem_id)
        if problem is None:
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

    @staticmethod
    def _validate_problem_knowledge_links(command: ProblemCommand) -> None:
        if len(command.knowledge_point_codes) > 3 or any(
            point_view(code) is None for code in command.knowledge_point_codes
        ):
            raise AppError("VALIDATION_ERROR", "题目知识点绑定无效", 422)
