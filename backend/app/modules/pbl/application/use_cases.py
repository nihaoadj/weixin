from dataclasses import replace

from app.modules.classroom.public import ClassroomScopePort
from app.modules.content.public import PublishQuestionCommand, QuestionPublicationPort, knowledge_point_view
from app.modules.learning.public import PblLearningPort
from app.modules.pbl.application.ports import PblInferenceGateway, PblRepository
from app.modules.pbl.application.records import (
    InferenceRequest,
    PblDiagnosticRecord,
    PblParticipationRecord,
    PblSessionRecord,
    PblSnapshotRecord,
    PblSuggestionRecord,
)
from app.modules.pbl.application.reporting import build_report, build_report_page
from app.modules.pbl.domain.catalog import PATHOLOGY_POINTS
from app.shared.errors import AppError, PersistenceConflict
from app.shared.uow import UnitOfWork


class PblApplication:
    """PBL orchestration over explicit ports; no ORM or provider DTO escapes here."""

    def __init__(
        self,
        repository: PblRepository,
        uow: UnitOfWork,
        gateway: PblInferenceGateway,
        classroom_scope: ClassroomScopePort,
        publication: QuestionPublicationPort,
        provider: str,
        mode: str | None,
        learning: PblLearningPort,
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._gateway = gateway
        self._classroom_scope = classroom_scope
        self._publication = publication
        self._provider = provider
        self._mode = mode
        self._learning = learning

    def create_session(
        self, teacher_id: int, class_id: int, topic_code: str, case_id: int, goals: tuple[str, ...]
    ) -> PblSessionRecord:
        classroom = self._classroom_scope.owned_active(teacher_id, class_id)
        if classroom is None:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        if topic_code not in PATHOLOGY_POINTS or not 1 <= len(set(goals)) <= 3 or len(set(goals)) != len(goals):
            raise AppError("VALIDATION_ERROR", "请选择主题及 1～3 个不同目标知识点", 422)
        if any(knowledge_point_view(code) is None or not code.startswith(topic_code + ".") for code in goals):
            raise AppError("VALIDATION_ERROR", "目标知识点不属于课堂主题", 422)
        context = self._publication.case_context(case_id, classroom.code, topic_code)
        value = self._repository.create_session(
            class_id, teacher_id, topic_code, self._provider, self._mode, context, goals
        )
        self._uow.commit()
        return value

    def phase(self, teacher_id: int, class_id: int, session_id: int, phase: str, version: int):
        self._require_owned_session(teacher_id, class_id, session_id)
        raise AppError("STATE_CONFLICT", "学生阶段已由系统自动推进，教师不能手工修改", 409)

    def close_session(self, teacher_id: int, class_id: int, session_id: int) -> PblSessionRecord:
        value = self._require_owned_session(teacher_id, class_id, session_id)
        if value.status != "closed":
            value = self._repository.close_session(session_id)
            self._uow.commit()
        return value

    def active_for_student(self, student_id: int) -> tuple[PblSessionRecord, ...]:
        return self._repository.list_active_sessions(
            self._classroom_scope.active_class_ids_for_student(student_id), student_id
        )

    def classes_for_student(self, student_id: int):
        return self._classroom_scope.active_classes_for_student(student_id)

    @staticmethod
    def _interaction_style(value: str) -> str:
        if value not in {"guided", "direct"}:
            raise AppError("VALIDATION_ERROR", "沟通方式无效", 422)
        return value

    def create_student_dialogue(
        self,
        student_id: int,
        client_session_id: str,
        class_id: int,
        interaction_style: str,
        goals: tuple[str, ...],
    ) -> tuple[PblSessionRecord, PblParticipationRecord]:
        client_id = client_session_id.strip()
        style = self._interaction_style(interaction_style)
        if not client_id or len(client_id) > 100:
            raise AppError("VALIDATION_ERROR", "会话标识无效", 422)
        classroom = next(
            (item for item in self._classroom_scope.active_classes_for_student(student_id) if item.id == class_id),
            None,
        )
        if classroom is None:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        unique_goals = tuple(dict.fromkeys(goals))
        views = tuple(knowledge_point_view(code) for code in unique_goals)
        if len(unique_goals) != len(goals) or not 1 <= len(unique_goals) <= 3 or any(view is None for view in views):
            raise AppError("VALIDATION_ERROR", "请选择 1～3 个不同的病理知识点", 422)
        topics = {str(view["system_code"]) for view in views if view is not None}
        if len(topics) != 1 or next(iter(topics)) not in PATHOLOGY_POINTS:
            raise AppError("VALIDATION_ERROR", "知识点必须属于同一病理主题", 422)
        topic_code = next(iter(topics))
        existing = self._repository.find_student_session_by_client_id(student_id, client_id)
        if existing is not None:
            participation = self._repository.find_participation(existing.id, student_id)
            if (
                existing.class_id != class_id
                or existing.goal_point_codes != unique_goals
                or participation is None
                or participation.interaction_style != style
            ):
                raise AppError("STATE_CONFLICT", "会话标识已用于其他设置", 409)
            return existing, participation
        try:
            session = self._repository.create_session(
                class_id,
                classroom.teacher_id,
                topic_code,
                self._provider,
                self._mode,
                {
                    "case_id": None,
                    "case_version": None,
                    "case_digest": None,
                    "case_context": {"title": f"{PATHOLOGY_POINTS[topic_code]}主动研讨"},
                },
                unique_goals,
                session_kind="student_initiated",
                created_by_student_id=student_id,
                client_session_id=client_id,
            )
        except PersistenceConflict as error:
            self._uow.rollback()
            concurrent = self._repository.find_student_session_by_client_id(student_id, client_id)
            concurrent_participation = (
                self._repository.find_participation(concurrent.id, student_id) if concurrent is not None else None
            )
            if (
                concurrent is None
                or concurrent.class_id != class_id
                or concurrent.goal_point_codes != unique_goals
                or concurrent_participation is None
                or concurrent_participation.interaction_style != style
            ):
                raise AppError("STATE_CONFLICT", "会话创建发生冲突", 409) from error
            return concurrent, concurrent_participation
        participation = self._repository.get_or_create_participation(session.id, student_id, style)
        self._uow.commit()
        return session, participation

    def start_dialogue(
        self, student_id: int, session_id: int, interaction_style: str
    ) -> tuple[PblSessionRecord, PblParticipationRecord, PblSnapshotRecord | None]:
        style = self._interaction_style(interaction_style)
        session = self._require_student_session(student_id, session_id)
        existing = self._repository.find_participation(session_id, student_id)
        if existing is not None:
            if existing.interaction_style != style:
                raise AppError("STATE_CONFLICT", "本次研讨的沟通方式已经确定", 409)
            return session, existing, self._repository.latest_snapshot(existing.id)
        participation = self._repository.get_or_create_participation(session_id, student_id, style)
        self._uow.commit()
        return session, participation, self._repository.latest_snapshot(participation.id)

    def dialogue(
        self, student_id: int, session_id: int
    ) -> tuple[PblSessionRecord, PblParticipationRecord | None, PblSnapshotRecord | None]:
        session = self._require_visible_student_session(student_id, session_id)
        participation = self._repository.find_participation(session_id, student_id)
        snapshot = self._repository.latest_snapshot(participation.id) if participation else None
        return session, participation, snapshot

    def sessions_for_teacher(self, teacher_id: int, class_id: int) -> tuple[PblSessionRecord, ...]:
        if self._classroom_scope.owned_active(teacher_id, class_id) is None:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        return self._repository.list_sessions_for_teacher(teacher_id, class_id)

    def phase_counts(self, teacher_id: int, class_id: int, session_id: int) -> dict[str, int]:
        self._require_owned_session(teacher_id, class_id, session_id)
        return dict(self._repository.session_counts(session_id).get("phase_counts", {}))

    def participation(
        self, student_id: int, session_id: int
    ) -> tuple[PblParticipationRecord, PblSnapshotRecord | None]:
        existing = self._repository.find_participation(session_id, student_id)
        if existing:
            return existing, self._repository.latest_snapshot(existing.id)
        self._require_student_session(student_id, session_id)
        participation = self._repository.get_or_create_participation(session_id, student_id)
        self._uow.commit()
        return participation, self._repository.latest_snapshot(participation.id)

    def message(
        self,
        student_id: int,
        session_id: int,
        client_message_id: str,
        content: str,
        *,
        allow_implicit_guided_start: bool = False,
    ) -> tuple[PblParticipationRecord, PblSnapshotRecord]:
        normalized = content.strip()
        if not normalized or len(normalized) > 2000:
            raise AppError("VALIDATION_ERROR", "消息长度无效", 422)

        # A completed duplicate remains readable after closure; new writes require an active classroom.
        participation = self._repository.find_participation(session_id, student_id)
        if participation is None:
            if not allow_implicit_guided_start:
                raise AppError("STATE_CONFLICT", "请先选择本次研讨的沟通方式", 409)
            self._require_student_session(student_id, session_id)
            participation = self._repository.get_or_create_participation(
                session_id, student_id, interaction_style="guided"
            )
            self._uow.commit()
        duplicate = self._repository.message_result(participation.id, client_message_id)
        if duplicate:
            original = next(
                (m for m in participation.messages if m.get("client_message_id") == client_message_id), None
            )
            if not original or original["content"] != normalized:
                raise AppError("STATE_CONFLICT", "消息标识已用于其他内容", 409)
            self._uow.commit()
            return self._repository.participation(participation.id), duplicate
        if participation.phase_status == "completed":
            raise AppError("STATE_CONFLICT", "四阶段讨论已完成，不能继续发送新消息", 409)
        self._require_student_session(student_id, session_id)
        updated = self._repository.append_student_message(participation.id, client_message_id, normalized)
        if updated is None:
            raise AppError("STATE_CONFLICT", "消息正在处理", 409)

        # Persist the idempotency key before the external call. The result write
        # checks the same revision, so a concurrent outcome cannot overwrite it.
        self._uow.commit()
        session = self._repository.get_session(session_id)
        if session is None:
            raise AppError("RESOURCE_NOT_FOUND", "课堂不存在", 404)
        result = self._gateway.infer(
            InferenceRequest(
                session_id=session.id,
                topic_code=session.topic_code,
                question=normalized,
                history=updated.messages[:-1][-20:],
                anonymous_user_ref=updated.coze_user_ref,
                conversation_ref=updated.coze_conversation_ref,
                message_id=updated.messages[-1]["id"],
                case_context=session.case_context,
                goal_point_codes=session.goal_point_codes,
                current_phase=updated.current_phase,
                phase_started_revision=updated.phase_started_revision,
                current_revision=updated.revision,
                interaction_style=updated.interaction_style,
            )
        )
        snapshot = self._repository.save_result(updated.id, updated.revision, result)
        if snapshot is None:
            self._uow.rollback()
            raise AppError("STATE_CONFLICT", "对话已更新，请重试", 409)
        self._uow.commit()
        current = self._repository.participation(updated.id)
        if current is None:
            raise AppError("STATE_CONFLICT", "对话已更新，请重试", 409)
        return current, snapshot

    def _source_labels(self, teacher_id: int, value: PblDiagnosticRecord):
        classroom = self._classroom_scope.owned_active(teacher_id, value.class_id)
        members = self._classroom_scope.students(teacher_id, value.class_id)
        member = next((item for item in members if item.id == value.student_id), None)
        return replace(
            value,
            class_name=classroom.name if classroom else "已归档班级",
            student_name=member.nickname if member else f"历史参与学生 {value.student_id}",
        )

    def diagnostics(self, teacher_id: int, limit: int, offset: int, filters: dict):
        values, total = self._repository.diagnostics_for_teacher(teacher_id, limit, offset, filters)
        return tuple(self._source_labels(teacher_id, value) for value in values), total

    def diagnostic(self, teacher_id: int, snapshot_id: int) -> PblDiagnosticRecord:
        value = self._repository.diagnostic_for_teacher(teacher_id, snapshot_id)
        if value is None:
            raise AppError("RESOURCE_NOT_FOUND", "诊断不存在", 404)
        return self._source_labels(teacher_id, value)

    def edit_suggestion(
        self, teacher_id: int, suggestion_id: int, version: int, title: str, prompt: str, reject: bool
    ) -> PblSuggestionRecord:
        suggestion = self._require_suggestion(teacher_id, suggestion_id)
        if suggestion.version != version:
            raise AppError("STATE_CONFLICT", "建议已被更新", 409)
        if suggestion.status in {"published", "superseded"}:
            raise AppError("STATE_CONFLICT", "建议不可编辑", 409)
        value = self._repository.update_suggestion(
            suggestion.id,
            title.strip() or suggestion.title,
            prompt.strip() or suggestion.prompt,
            "rejected" if reject else "edited",
            suggestion.version + 1,
        )
        self._uow.commit()
        return value

    def adopt(
        self,
        teacher_id: int,
        suggestion_id: int,
        version: int,
        title: str,
        prompt: str,
        target_student_ids: tuple[int, ...],
        whole_class: bool,
        include_case_retry: bool,
    ):
        suggestion = self._require_suggestion(teacher_id, suggestion_id)
        if suggestion.problem_id is not None:
            return suggestion
        if suggestion.status not in {"proposed", "edited"} or suggestion.version != version:
            raise AppError("STATE_CONFLICT", "建议版本或状态已更新", 409)
        diagnostic = self.diagnostic(teacher_id, suggestion.snapshot_id)
        if diagnostic.snapshot.schema_version not in {3, 4}:
            raise AppError("STATE_CONFLICT", "旧版诊断仅供查阅，请重新进行诊断", 409)
        session = self._repository.session_for_suggestion(suggestion.id)
        classroom = self._classroom_scope.owned_active(teacher_id, session.class_id) if session else None
        if classroom is None:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        members = self._classroom_scope.students(teacher_id, session.class_id)
        member_map = {member.id: member for member in members}
        if whole_class and target_student_ids:
            raise AppError("VALIDATION_ERROR", "全班与指定学生不能同时选择", 422)
        targets = tuple(member_map) if whole_class else (target_student_ids or (diagnostic.student_id,))
        if not targets or len(set(targets)) != len(targets) or not set(targets).issubset(member_map):
            raise AppError("VALIDATION_ERROR", "目标学生必须属于本班", 422)
        if not title.strip() or not prompt.strip():
            raise AppError("VALIDATION_ERROR", "题目标题和内容不能为空", 422)
        points = tuple(dict.fromkeys(str(g["point_code"]) for g in diagnostic.snapshot.knowledge_gaps))
        dimensions = tuple(dict.fromkeys(str(g["dimension_id"]) for g in diagnostic.snapshot.reasoning_issues))
        # Obtain a write claim before any cross-module creation; all ports share this transaction.
        self._repository.update_suggestion(suggestion.id, title.strip(), prompt.strip(), "edited", version + 1)
        publication = self._publication.adopt_open_question(
            PublishQuestionCommand(
                teacher_id=teacher_id,
                source_id=suggestion.id,
                title=title.strip(),
                prompt=prompt.strip(),
                class_code=classroom.code,
                target_external_ids=tuple(member_map[i].external_id for i in targets),
                point_codes=points,
            )
        )
        resources = (
            {
                "task_type": "discussion",
                "problem_id": publication.problem_id,
                "prompt": prompt.strip(),
                "cycle_number": 1,
                "target_type": "discussion",
                "target_code": "discussion",
                "variant_code": f"suggestion:{suggestion.id}:discussion:v1",
            },
            {
                "task_type": "discussion",
                "problem_id": publication.problem_id,
                "prompt": "第二轮反思：结合首轮反馈，重新说明你的证据链与仍不确定之处。",
                "cycle_number": 2,
                "target_type": "discussion",
                "target_code": "discussion",
                "variant_code": f"suggestion:{suggestion.id}:discussion:v2",
            },
            *self._publication.task_resources(session.case_id, points, dimensions),
        )
        if include_case_retry:
            if session.case_id is None:
                raise AppError("VALIDATION_ERROR", "旧课堂没有绑定病例", 422)
            self._publication.case_context(session.case_id, classroom.code, session.topic_code)
            target_dimensions = dimensions or ("evidence_reasoning",)
            resources = (
                *resources,
                *(
                    {
                        "task_type": "focused_retry",
                        "dimension_id": target_dimensions[0],
                        "stage_id": "history",
                        "problem_id": session.case_id,
                        "prompt": "重新完成课堂病例的五个训练阶段",
                        "cycle_number": cycle,
                        "target_type": "case_retry",
                        "target_code": f"case:{session.case_id}",
                        "variant_code": f"case:{session.case_id}:retry:v{cycle}",
                        "target_dimension_ids": list(target_dimensions),
                    }
                    for cycle in (1, 2)
                ),
            )
        self._learning.create(
            targets,
            suggestion.id,
            {
                "teacher_id": teacher_id,
                "class_id": session.class_id,
                "class_name": classroom.name,
                "session_id": session.id,
                "snapshot_id": diagnostic.snapshot.id,
                "suggestion_id": suggestion.id,
                "point_codes": list(points),
                "dimension_ids": list(dimensions),
                "topic_code": session.topic_code,
            },
            tuple(resources),
        )
        value = self._repository.attach_problem(suggestion.id, publication.problem_id, version + 2)
        self._uow.commit()
        return value

    def learning_plans(self, student_id: int):
        return self._learning.list(student_id=student_id)

    def learning_report_page(self, student_id: int, limit: int, offset: int):
        sources = {item.session.id: item for item in self._repository.report_participations(student_id)}
        plans_by_session: dict[int, list[dict]] = {}
        for plan in self._learning.list(student_id=student_id):
            session_id = int((plan.get("source_context") or {}).get("session_id") or 0)
            if session_id > 0:
                plans_by_session.setdefault(session_id, []).append(plan)
        reports = []
        for session_id in set(sources) | set(plans_by_session):
            session = sources[session_id].session if session_id in sources else self._repository.get_session(session_id)
            if session is not None:
                reports.append(build_report(session, sources.get(session_id), plans_by_session.get(session_id, [])))
        return build_report_page(reports, limit, offset)

    def learning_report(self, student_id: int, session_id: int):
        source = next(
            (item for item in self._repository.report_participations(student_id) if item.session.id == session_id), None
        )
        plans = [
            plan
            for plan in self._learning.list(student_id=student_id)
            if int((plan.get("source_context") or {}).get("session_id") or 0) == session_id
        ]
        session = source.session if source else self._repository.get_session(session_id)
        if session is None or (source is None and not plans):
            raise AppError("RESOURCE_NOT_FOUND", "学情报告不存在", 404)
        return build_report(session, source, plans)

    def submit_task(self, student_id: int, task_id: int, submission_id: str, answer: dict):
        result = self._learning.submit(student_id, task_id, submission_id, answer)
        self._uow.commit()
        return result

    def learning_results(self, teacher_id: int, session_id: int | None = None):
        plans = self._learning.list(teacher_id=teacher_id, session_id=session_id)
        return tuple(
            plan for plan in plans if self._classroom_scope.owned_active(teacher_id, plan["source_context"]["class_id"])
        )

    def verify_learning(self, teacher_id: int, plan_id: int, version: int, decision: str, note: str):
        if not any(plan["id"] == plan_id for plan in self.learning_results(teacher_id)):
            raise AppError("RESOURCE_NOT_FOUND", "学习结果不存在", 404)
        raise AppError("STATE_CONFLICT", "学习结果由系统按数据自动判定，教师仅可查看", 409)

    def summary(self, teacher_id: int, class_id: int, session_id: int):
        self._require_owned_session(teacher_id, class_id, session_id)
        plans = self.learning_results(teacher_id, session_id)
        tasks = [task for plan in plans for task in plan["tasks"]]
        retests = [task["result"]["score"] for task in tasks if task["task_type"] == "retest" and task["result"]]
        return {
            **self._repository.session_counts(session_id),
            "plans": len(plans),
            "tasks": len(tasks),
            "completed_tasks": sum(task["status"] == "completed" for task in tasks),
            "pending_verification": 0,
            "improved": sum(plan["verification_status"] == "improved" for plan in plans),
            "needs_reinforcement": sum(plan["verification_status"] == "needs_reinforcement" for plan in plans),
            "automation_exhausted": sum(bool(plan["automation_exhausted"]) for plan in plans),
            "objective_retest_count": len(retests),
            "objective_retest_average": sum(retests) / len(retests) if retests else None,
        }

    def revisions(self, teacher_id: int, snapshot_id: int):
        self.diagnostic(teacher_id, snapshot_id)
        return tuple(
            self._source_labels(teacher_id, item)
            for item in self._repository.revisions_for_teacher(teacher_id, snapshot_id)
        )

    def _require_owned_session(self, teacher_id: int, class_id: int, session_id: int) -> PblSessionRecord:
        value = self._repository.get_session(session_id)
        if value is None or value.class_id != class_id or value.teacher_id != teacher_id:
            raise AppError("RESOURCE_NOT_FOUND", "课堂不存在", 404)
        return value

    def _require_student_session(self, student_id: int, session_id: int) -> PblSessionRecord:
        value = self._repository.get_session(session_id)
        if (
            value is None
            or value.status != "active"
            or not self._classroom_scope.active_member(student_id, value.class_id)
            or (value.session_kind == "student_initiated" and value.created_by_student_id != student_id)
        ):
            raise AppError("RESOURCE_NOT_FOUND", "课堂不存在", 404)
        return value

    def _require_visible_student_session(self, student_id: int, session_id: int) -> PblSessionRecord:
        value = self._repository.get_session(session_id)
        if (
            value is None
            or not self._classroom_scope.active_member(student_id, value.class_id)
            or (value.session_kind == "student_initiated" and value.created_by_student_id != student_id)
        ):
            raise AppError("RESOURCE_NOT_FOUND", "研讨不存在", 404)
        return value

    def _require_suggestion(self, teacher_id: int, suggestion_id: int) -> PblSuggestionRecord:
        value = self._repository.suggestion_for_teacher(teacher_id, suggestion_id)
        if value is None:
            raise AppError("RESOURCE_NOT_FOUND", "建议不存在", 404)
        return value
