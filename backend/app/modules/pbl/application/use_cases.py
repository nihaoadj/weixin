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
from app.modules.pbl.application.reporting import DIMENSION_LABELS, build_report, build_report_page
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

    @staticmethod
    def _task_target_label(resource: dict) -> str:
        target_type = str(resource.get("target_type", ""))
        target_code = str(resource.get("target_code", ""))
        if target_type == "knowledge_gap":
            point = knowledge_point_view(target_code)
            return str(point.get("title")) if point else target_code
        if target_type == "reasoning_issue":
            return DIMENSION_LABELS.get(target_code, target_code)
        if target_type == "case_retry":
            return "完整病例重练"
        return "正式讨论" if target_type == "discussion" else target_code

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
        class_id: int | None,
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
        if class_id is not None and classroom is None:
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
                classroom.teacher_id if classroom else None,
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
        if any(
            item.action_type == "closed" for item in self._repository.feedbacks_for_snapshot(suggestion.snapshot_id)
        ):
            raise AppError("STATE_CONFLICT", "该工作项已关闭", 409)
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
        _commit: bool = True,
    ):
        suggestion = self._require_suggestion(teacher_id, suggestion_id)
        if any(
            item.action_type == "closed" for item in self._repository.feedbacks_for_snapshot(suggestion.snapshot_id)
        ):
            raise AppError("STATE_CONFLICT", "该工作项已关闭", 409)
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
        resources = tuple({**resource, "target_label": self._task_target_label(resource)} for resource in resources)
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
        if _commit:
            self._uow.commit()
        return value

    def _work_status(self, value: PblDiagnosticRecord, feedbacks) -> str:
        return self._work_status_from_suggestion_statuses(
            tuple(item.status for item in value.suggestions), feedbacks
        )

    def _work_status_from_suggestion_statuses(self, suggestion_statuses: tuple[str, ...], feedbacks) -> str:
        if any(status == "published" for status in suggestion_statuses):
            return "task_published"
        closed_suggestions = suggestion_statuses and all(
            status in {"rejected", "superseded"} for status in suggestion_statuses
        )
        if any(item.action_type == "closed" for item in feedbacks) or closed_suggestions:
            return "closed"
        return "responded" if feedbacks else "pending"

    def _work_item_view(self, value: PblDiagnosticRecord, feedbacks) -> dict:
        state = self._work_status(value, feedbacks)
        return {
            "snapshot_id": value.snapshot.id,
            "session_id": value.session_id,
            "source": "student_submission" if value.session_kind == "student_initiated" else "classroom_diagnostic",
            "status": state,
            "student": {"id": value.student_id, "name": value.student_name},
            "class": {"id": value.class_id, "name": value.class_name},
            "topic": value.topic_code,
            "entered_at": value.snapshot.created_at,
            "last_activity_at": feedbacks[-1].created_at if feedbacks else value.snapshot.created_at,
            "knowledge_gap_count": len(value.snapshot.knowledge_gaps),
            "reasoning_issue_count": len(value.snapshot.reasoning_issues),
            "next_action": {
                "pending": "审阅并反馈",
                "responded": "发送补充反馈",
                "task_published": "查看学习进展",
                "closed": "已关闭",
            }[state],
        }

    def work_items(self, teacher_id: int, limit: int, offset: int, filters: dict):
        # Status is derived from append-only feedback and published suggestions, so it must be
        # applied before pagination.  Source/class filtering remains in the repository query.
        diagnostic_filters = {key: value for key, value in filters.items() if key != "work_status"}
        values, _ = self.diagnostics(teacher_id, 10000, 0, diagnostic_filters)
        feedbacks_by_snapshot = self._repository.feedbacks_for_snapshots(
            tuple(value.snapshot.id for value in values)
        )
        all_items = []
        for value in values:
            item = self._work_item_view(value, feedbacks_by_snapshot.get(value.snapshot.id, ()))
            if filters.get("work_status") and item["status"] != filters["work_status"]:
                continue
            all_items.append(item)
        states = ("pending", "responded", "task_published", "closed")
        summary = {key: sum(item["status"] == key for item in all_items) for key in states}
        pending = sorted(
            (item for item in all_items if item["status"] == "pending"),
            key=lambda item: (item["entered_at"].timestamp() if item["entered_at"] else 0, item["snapshot_id"]),
        )
        handled = sorted(
            (item for item in all_items if item["status"] != "pending"),
            key=lambda item: (
                item["last_activity_at"].timestamp() if item["last_activity_at"] else 0,
                item["snapshot_id"],
            ),
            reverse=True,
        )
        matching = pending + handled
        return {
            "items": matching[offset : offset + limit],
            "total": len(matching),
            "limit": limit,
            "offset": offset,
            "summary": summary,
        }

    def work_item(self, teacher_id: int, snapshot_id: int):
        diagnostic = self.diagnostic(teacher_id, snapshot_id)
        feedbacks = self._repository.feedbacks_for_snapshot(snapshot_id)
        return {
            "work_item": self._work_item_view(diagnostic, feedbacks),
            "diagnostic": diagnostic,
            "feedbacks": feedbacks,
        }

    def feedback(
        self,
        teacher_id: int,
        snapshot_id: int,
        client_feedback_id: str,
        body: str,
        action_type: str,
        suggestion_id: int | None = None,
        version: int | None = None,
        title: str = "",
        prompt: str = "",
        target_student_ids: tuple[int, ...] = (),
        whole_class: bool = False,
        include_case_retry: bool = False,
    ):
        body = body.strip()
        if not 1 <= len(body) <= 1000 or not 1 <= len(client_feedback_id.strip()) <= 100:
            raise AppError("VALIDATION_ERROR", "反馈正文或幂等键无效", 422)
        diagnostic = self.diagnostic(teacher_id, snapshot_id)
        existing = self._repository.feedbacks_for_snapshot(snapshot_id)
        retry = next(
            (
                item
                for item in existing
                if item.teacher_id == teacher_id and item.client_feedback_id == client_feedback_id.strip()
            ),
            None,
        )
        if retry is not None:
            if retry.action_type != action_type or retry.body != body or retry.suggestion_id != suggestion_id:
                raise AppError("STATE_CONFLICT", "反馈幂等键已用于不同内容", 409)
            return retry
        if any(item.action_type == "closed" for item in existing):
            raise AppError("STATE_CONFLICT", "该工作项已关闭", 409)
        if any(item.action_type == "task_published" for item in existing):
            raise AppError("STATE_CONFLICT", "正式任务已发布，请在学习跟进中继续反馈", 409)
        if action_type not in {"feedback_only", "task_published", "closed"}:
            raise AppError("VALIDATION_ERROR", "反馈动作无效", 422)
        plan_id = None
        try:
            if action_type == "task_published":
                if suggestion_id is None or version is None:
                    raise AppError("VALIDATION_ERROR", "发布任务需要建议版本", 422)
                # Publication, both-cycle plan resources, feedback and notification share this Session.
                self.adopt(
                    teacher_id,
                    suggestion_id,
                    version,
                    title,
                    prompt,
                    target_student_ids,
                    whole_class,
                    include_case_retry,
                    _commit=False,
                )
                plan_id = next(
                    (
                        plan["id"]
                        for plan in self._learning.list(student_id=diagnostic.student_id)
                        if int((plan.get("source_context") or {}).get("snapshot_id") or 0) == snapshot_id
                    ),
                    None,
                )
            elif action_type == "closed":
                for suggestion in diagnostic.suggestions:
                    if suggestion.status in {"proposed", "edited"}:
                        self._repository.update_suggestion(
                            suggestion.id, suggestion.title, suggestion.prompt, "rejected", suggestion.version + 1
                        )
            row = self._repository.append_feedback(
                snapshot_id=snapshot_id,
                plan_id=plan_id,
                student_id=diagnostic.student_id,
                class_id=diagnostic.class_id,
                teacher_id=teacher_id,
                action_type=action_type,
                suggestion_id=suggestion_id,
                body=body,
                client_feedback_id=client_feedback_id.strip(),
            )
            self._learning.notify(
                diagnostic.student_id, diagnostic.session_id, "教师已回应你的 PBL 研讨", body, f"pbl-feedback:{row.id}"
            )
            self._uow.commit()
            return row
        except Exception:
            self._uow.rollback()
            raise

    def follow_ups(self, teacher_id: int, limit: int, offset: int, filters: dict):
        plans = list(self.learning_results(teacher_id, filters.get("session_id")))
        if filters.get("class_id"):
            plans = [item for item in plans if item["source_context"]["class_id"] == filters["class_id"]]
        if filters.get("student_id"):
            plans = [item for item in plans if item["student_id"] == filters["student_id"]]

        def status(plan):
            if plan["verification_status"] == "improved":
                return "improved"
            if plan["verification_status"] == "needs_reinforcement":
                return "support_needed"
            return "cycle_2" if plan["current_cycle"] == 2 else "in_progress"

        if filters.get("status"):
            plans = [item for item in plans if status(item) == filters["status"]]
        plans.sort(key=lambda item: (item.get("evaluated_at") or item.get("due_at"), item["id"]), reverse=True)
        class_scopes = {
            int(item["source_context"]["class_id"]): self._classroom_scope.owned_active(
                teacher_id, int(item["source_context"]["class_id"])
            )
            for item in plans
        }
        student_names = {
            class_id: {student.id: student.nickname for student in self._classroom_scope.students(teacher_id, class_id)}
            for class_id in class_scopes
        }
        sessions = {
            item["source_context"]["session_id"]: self._repository.get_session(item["source_context"]["session_id"])
            for item in plans
        }
        return {
            "items": [
                {
                    "plan_id": item["id"],
                    "student_id": item["student_id"],
                    "student_name": student_names.get(item["source_context"]["class_id"], {}).get(
                        item["student_id"], "学生"
                    ),
                    "class_id": item["source_context"]["class_id"],
                    "class_name": class_scopes[item["source_context"]["class_id"]].name,
                    "session_id": item["source_context"]["session_id"],
                    "session_topic": (
                        sessions[item["source_context"]["session_id"]].topic_code
                        if sessions[item["source_context"]["session_id"]]
                        else "PBL 课堂"
                    ),
                    "status": status(item),
                    "current_cycle": item["current_cycle"],
                    "verification_status": item["verification_status"],
                    "automation_exhausted": item["automation_exhausted"],
                    "failed_targets": item.get("decision_basis", {}).get("failed_targets", []),
                }
                for item in plans[offset : offset + limit]
            ],
            "total": len(plans),
            "limit": limit,
            "offset": offset,
        }

    def follow_up(self, teacher_id: int, plan_id: int):
        plan = next((item for item in self.learning_results(teacher_id) if item["id"] == plan_id), None)
        if plan is None:
            raise AppError("RESOURCE_NOT_FOUND", "学习跟进不存在", 404)
        return {"plan": plan, "feedbacks": self._repository.feedbacks_for_plan(plan_id)}

    def follow_up_feedback(self, teacher_id: int, plan_id: int, client_feedback_id: str, body: str):
        body = body.strip()
        client_feedback_id = client_feedback_id.strip()
        if not 1 <= len(body) <= 1000 or not 1 <= len(client_feedback_id) <= 100:
            raise AppError("VALIDATION_ERROR", "反馈正文或幂等键无效", 422)
        plan = self.follow_up(teacher_id, plan_id)["plan"]
        if plan["verification_status"] != "needs_reinforcement" or not plan["automation_exhausted"]:
            raise AppError("STATE_CONFLICT", "当前计划不需要补充反馈", 409)
        context = plan["source_context"]
        try:
            row = self._repository.append_feedback(
                snapshot_id=int(context["snapshot_id"]),
                plan_id=plan_id,
                student_id=int(plan["student_id"]),
                class_id=int(context["class_id"]),
                teacher_id=teacher_id,
                action_type="follow_up",
                suggestion_id=None,
                body=body,
                client_feedback_id=client_feedback_id,
            )
            self._learning.notify(
                int(plan["student_id"]),
                int(context["session_id"]),
                "教师补充了 PBL 学习建议",
                body,
                f"pbl-follow-up:{row.id}",
            )
            self._uow.commit()
            return row
        except Exception:
            self._uow.rollback()
            raise

    def teacher_sessions(
        self, teacher_id: int, limit: int, offset: int, class_id: int | None = None, status: str | None = None
    ):
        rows = list(self._repository.list_sessions_owned_by_teacher(teacher_id))
        if class_id:
            rows = [item for item in rows if item.class_id == class_id]
        if status:
            rows = [item for item in rows if item.status == status]
        return {
            "items": [
                {
                    "id": item.id,
                    "class_id": item.class_id,
                    "class_name": self._classroom_scope.owned_active(teacher_id, item.class_id).name,
                    "topic_code": item.topic_code,
                    "status": item.status,
                    "created_at": item.created_at,
                    "closed_at": item.closed_at,
                }
                for item in rows[offset : offset + limit]
            ],
            "total": len(rows),
            "limit": limit,
            "offset": offset,
        }

    def session_dashboard(self, teacher_id: int, class_id: int, session_id: int):
        session = self._require_owned_session(teacher_id, class_id, session_id)
        plans = self.learning_results(teacher_id, session_id)
        plan_by_student = {}
        for plan in plans:
            plan_by_student.setdefault(plan["student_id"], plan)
        students = {item.id: item for item in self._classroom_scope.students(teacher_id, class_id)}
        dashboard_items = self._repository.session_dashboard_rows(session.id)
        snapshot_ids = tuple(item["snapshot_id"] for item in dashboard_items if item["snapshot_id"])
        feedbacks_by_snapshot = self._repository.feedbacks_for_snapshots(snapshot_ids)
        suggestion_statuses_by_snapshot = self._repository.suggestion_statuses_for_snapshots(snapshot_ids)
        rows = []
        for item in dashboard_items:
            student = students.get(item["student_id"])
            if not student:
                continue
            plan = plan_by_student.get(item["student_id"])
            work_item_status = None
            if item["snapshot_id"]:
                work_item_status = self._work_status_from_suggestion_statuses(
                    suggestion_statuses_by_snapshot.get(item["snapshot_id"], ()),
                    feedbacks_by_snapshot.get(item["snapshot_id"], ()),
                )
            rows.append(
                {
                    **item,
                    "student_name": student.nickname,
                    "work_item_status": work_item_status,
                    "task_progress": {
                        "completed": sum(task["status"] == "completed" for task in plan["tasks"]) if plan else 0,
                        "total": len(plan["tasks"]) if plan else 0,
                    },
                    "current_cycle": plan["current_cycle"] if plan else None,
                    "verification_status": plan["verification_status"] if plan else None,
                }
            )
        return {
            "session": {"id": session.id, "class_id": session.class_id, "status": session.status},
            "summary": self.summary(teacher_id, class_id, session_id),
            "students": rows,
        }

    def learning_plans(self, student_id: int):
        return self._learning.list(student_id=student_id)

    def learning_report_page(self, student_id: int, limit: int, offset: int):
        sources = {item.session.id: item for item in self._repository.report_participations(student_id)}
        snapshot_ids = tuple(snapshot.id for source in sources.values() for snapshot in source.snapshots)
        feedbacks_by_snapshot = self._repository.feedbacks_for_snapshots(snapshot_ids)
        submissions = {
            session_id: self._repository.submission(session_id)
            for session_id, source in sources.items()
            if source.session.session_kind == "student_initiated"
        }
        plans_by_session: dict[int, list[dict]] = {}
        for plan in self._learning.list(student_id=student_id):
            session_id = int((plan.get("source_context") or {}).get("session_id") or 0)
            if session_id > 0:
                plans_by_session.setdefault(session_id, []).append(plan)
        reports = []
        for session_id in set(sources) | set(plans_by_session):
            session = sources[session_id].session if session_id in sources else self._repository.get_session(session_id)
            if session is not None:
                source = sources.get(session_id)
                feedbacks = tuple(
                    feedback
                    for snapshot in (source.snapshots if source else ())
                    for feedback in feedbacks_by_snapshot.get(snapshot.id, ())
                )
                reports.append(
                    build_report(
                        session,
                        source,
                        plans_by_session.get(session_id, []),
                        submissions.get(session_id),
                        feedbacks,
                    )
                )
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
        feedbacks = self._repository.feedbacks_for_snapshots(
            tuple(snapshot.id for snapshot in (source.snapshots if source else ()))
        )
        return build_report(
            session,
            source,
            plans,
            self._repository.submission(session_id) if session.session_kind == "student_initiated" else None,
            tuple(feedback for values in feedbacks.values() for feedback in values),
        )

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
        if (
            value is None
            or value.session_kind != "classroom"
            or value.class_id != class_id
            or value.teacher_id != teacher_id
            or self._classroom_scope.owned_active(teacher_id, class_id) is None
        ):
            raise AppError("RESOURCE_NOT_FOUND", "课堂不存在", 404)
        return value

    def _require_student_session(self, student_id: int, session_id: int) -> PblSessionRecord:
        value = self._repository.get_session(session_id)
        if (
            value is None
            or value.status != "active"
            or (
                value.session_kind == "classroom"
                and not self._classroom_scope.active_member(student_id, value.class_id)
            )
            or (value.session_kind == "student_initiated" and value.created_by_student_id != student_id)
        ):
            raise AppError("RESOURCE_NOT_FOUND", "课堂不存在", 404)
        return value

    def _require_visible_student_session(self, student_id: int, session_id: int) -> PblSessionRecord:
        value = self._repository.get_session(session_id)
        if (
            value is None
            or (
                value.session_kind == "classroom"
                and not self._classroom_scope.active_member(student_id, value.class_id)
                and self._repository.find_participation(session_id, student_id) is None
            )
            or (value.session_kind == "student_initiated" and value.created_by_student_id != student_id)
        ):
            raise AppError("RESOURCE_NOT_FOUND", "研讨不存在", 404)
        return value

    def _require_suggestion(self, teacher_id: int, suggestion_id: int) -> PblSuggestionRecord:
        value = self._repository.suggestion_for_teacher(teacher_id, suggestion_id)
        if value is None:
            raise AppError("RESOURCE_NOT_FOUND", "建议不存在", 404)
        return value

    def submission_preview(self, student_id: int, session_id: int) -> dict:
        session, participation, snapshot = self.dialogue(student_id, session_id)
        if session.session_kind != "student_initiated" or participation is None:
            raise AppError("STATE_CONFLICT", "课堂研讨按课堂规则提供教师学情", 409)
        if participation.current_phase != "completed" or snapshot is None or snapshot.status != "ready":
            raise AppError("STATE_CONFLICT", "完成四阶段研讨后可提交", 409)
        shared = self._repository.submission(session_id)
        if shared and shared.get("preview_payload"):
            feedbacks = self._repository.feedbacks_for_snapshot(shared["snapshot_id"])
            suggestions = self._repository.suggestions_for_snapshot(shared["snapshot_id"])
            teacher_status = (
                "task_published"
                if any(item.status == "published" for item in suggestions)
                else "closed"
                if any(item.action_type == "closed" for item in feedbacks)
                else "responded"
                if feedbacks
                else "pending"
            )
            return {
                **shared["preview_payload"],
                "submission": self._submission_view(shared),
                "teacher_status": teacher_status,
                "feedbacks": [
                    {
                        "id": item.id,
                        "action_type": item.action_type,
                        "body": item.body,
                        "created_at": item.created_at,
                        "plan_id": item.plan_id,
                    }
                    for item in feedbacks
                ],
                "next_action": "进入正式任务"
                if teacher_status == "task_published"
                else "按反馈开启新一轮研讨"
                if teacher_status == "responded"
                else "查看教师结论"
                if teacher_status == "closed"
                else "等待教师审阅",
            }
        return {
            "session_id": session_id,
            "snapshot_id": snapshot.id,
            "knowledge_gaps": snapshot.knowledge_gaps,
            "reasoning_issues": snapshot.reasoning_issues,
            "evidence_summary": snapshot.phase_evidence_summary,
            "questions": [
                {"id": x.id, "title": x.title, "prompt": x.prompt}
                for x in self._repository.suggestions_for_snapshot(snapshot.id)
            ],
            "submission": self._submission_view(shared) if shared else None,
            "teacher_status": None,
            "feedbacks": [],
            "next_action": "完成后可提交给教师",
        }

    @staticmethod
    def _submission_view(shared: dict) -> dict:
        return {
            key: value
            for key, value in shared.items()
            if key not in {"teacher_id", "client_submission_id", "preview_payload"}
        }

    def submit_to_teacher(
        self, student_id: int, session_id: int, snapshot_id: int, class_id: int, client_id: str
    ) -> dict:
        preview = self.submission_preview(student_id, session_id)
        if preview["snapshot_id"] != snapshot_id:
            raise AppError("STATE_CONFLICT", "诊断版本已经改变，请重新预览", 409)
        classroom = next((c for c in self.classes_for_student(student_id) if c.id == class_id), None)
        if classroom is None:
            raise AppError("RESOURCE_NOT_FOUND", "请选择本人有效班级", 404)
        shared = self._repository.submission(session_id)
        if shared:
            if shared["snapshot_id"] != snapshot_id or shared["class_id"] != class_id:
                raise AppError("STATE_CONFLICT", "本轮已提交，不能改投", 409)
            return preview
        try:
            payload = {key: value for key, value in preview.items() if key != "submission"}
            self._repository.save_submission(
                session_id, snapshot_id, student_id, class_id, classroom.teacher_id, client_id, payload
            )
            self._uow.commit()
        except PersistenceConflict:
            self._uow.rollback()
            shared = self._repository.submission(session_id)
            if not shared or shared["snapshot_id"] != snapshot_id or shared["class_id"] != class_id:
                raise AppError("STATE_CONFLICT", "提交发生冲突，请重新加载", 409) from None
        return self.submission_preview(student_id, session_id)
