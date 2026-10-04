from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256

from app.modules.classroom.public import ClassroomScopePort
from app.modules.content.public import (
    KnowledgeCatalogPort,
    QuestionPublicationPort,
)
from app.modules.learning.public import (
    CompletionLearningRoutePort,
    LearningEvidenceCommand,
    LearningEvidenceMetricCommand,
    LearningEvidencePort,
)
from app.modules.pbl.application.ports import PblInferenceGateway, PblRepository
from app.modules.pbl.application.records import (
    InferenceRequest,
    PblDiagnosticRecord,
    PblMessageSubmissionRecord,
    PblParticipationRecord,
    PblSessionRecord,
    PblSnapshotRecord,
    PblSuggestionRecord,
    PrivateFollowupRequest,
)
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
        knowledge_catalog: KnowledgeCatalogPort,
        learning_evidence: LearningEvidencePort | None = None,
        completion_routes: CompletionLearningRoutePort | None = None,
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._gateway = gateway
        self._classroom_scope = classroom_scope
        self._publication = publication
        self._provider = provider
        self._mode = mode
        self._knowledge_catalog = knowledge_catalog
        self._learning_evidence = learning_evidence
        self._completion_routes = completion_routes

    def create_session(
        self, teacher_id: int, class_id: int, topic_code: str, case_id: int, goals: tuple[str, ...]
    ) -> PblSessionRecord:
        classroom = self._classroom_scope.owned_active(teacher_id, class_id)
        if classroom is None:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        module_labels = self._knowledge_catalog.module_labels()
        if topic_code not in module_labels or len(goals) != 1 or len(set(goals)) != 1:
            raise AppError("VALIDATION_ERROR", "请选择主题及一个目标知识点", 422)
        if any(
            (point := self._knowledge_catalog.point_view(code)) is None or point["system_code"] != topic_code
            for code in goals
        ):
            raise AppError("VALIDATION_ERROR", "目标知识点不属于课堂主题", 422)
        context = self._publication.case_context(case_id, classroom.code, topic_code, teacher_id)
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
        # Keep the legacy request field for compatibility, but student-created
        # dialogues are always private and never inherit class/teacher scope.
        private_class_id = None
        unique_goals = tuple(dict.fromkeys(goals))
        views = tuple(self._knowledge_catalog.point_view(code) for code in unique_goals)
        if len(unique_goals) != 1 or len(goals) != 1 or any(view is None for view in views):
            raise AppError("VALIDATION_ERROR", "请选择一个病理知识点", 422)
        topics = {str(view["system_code"]) for view in views if view is not None}
        module_labels = self._knowledge_catalog.module_labels()
        if len(topics) != 1 or next(iter(topics)) not in module_labels:
            raise AppError("VALIDATION_ERROR", "知识点必须属于同一病理主题", 422)
        topic_code = next(iter(topics))
        existing = self._repository.find_student_session_by_client_id(student_id, client_id)
        if existing is not None:
            participation = self._repository.find_participation(existing.id, student_id)
            if existing.goal_point_codes != unique_goals or participation is None:
                raise AppError("STATE_CONFLICT", "会话标识已用于其他设置", 409)
            return existing, participation
        try:
            session = self._repository.create_session(
                private_class_id,
                None,
                topic_code,
                self._provider,
                self._mode,
                {
                    "case_id": None,
                    "case_version": None,
                    "case_digest": None,
                    "case_context": {"title": f"{module_labels[topic_code]}主动研讨"},
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
            if concurrent is None or concurrent.goal_point_codes != unique_goals or concurrent_participation is None:
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
            if existing.phase_status == "completed":
                return session, existing, self._require_completion_snapshot(existing)
            current = self._repository.set_interaction_style(existing.id, style)
            self._uow.commit()
            return session, current, self._repository.latest_snapshot(existing.id)
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
        interaction_style: str | None = None,
        *,
        allow_implicit_guided_start: bool = False,
    ) -> PblMessageSubmissionRecord:
        normalized = content.strip()
        if not normalized or len(normalized) > 2000:
            raise AppError("VALIDATION_ERROR", "消息长度无效", 422)
        if not client_message_id.strip() or len(client_message_id) > 100:
            raise AppError("VALIDATION_ERROR", "消息标识无效", 422)
        if interaction_style is not None:
            self._interaction_style(interaction_style)
        self._require_visible_student_session(student_id, session_id)

        # A completed duplicate remains readable after closure; new writes require an active classroom.
        participation = self._repository.find_participation(session_id, student_id)
        style = interaction_style or (participation.interaction_style if participation else "guided")
        if participation is None:
            self._require_student_session(student_id, session_id)
            participation = self._repository.get_or_create_participation(
                session_id, student_id, interaction_style=style
            )
        duplicate = self._repository.message_result(participation.id, client_message_id)
        if duplicate:
            original = next(
                (m for m in participation.messages if m.get("client_message_id") == client_message_id), None
            )
            if not original or original["content"] != normalized or original["interaction_style"] != style:
                raise AppError("STATE_CONFLICT", "消息标识已用于其他内容", 409)
            if original.get("turn_scope") != duplicate.turn_scope:
                raise AppError("STATE_CONFLICT", "消息范围与结果关联损坏", 409)
            self._uow.commit()
            current = self._repository.participation(participation.id)
            if current is None:
                raise AppError("STATE_CONFLICT", "对话已更新，请重试", 409)
            if duplicate.turn_scope == "evidence":
                if duplicate.snapshot is None:
                    raise AppError("STATE_CONFLICT", "诊断结果关联损坏", 409)
                return PblMessageSubmissionRecord(current, duplicate.snapshot, "evidence_assessment", "evidence")
            completion = self._require_completion_snapshot(current)
            if duplicate.private_follow_up is None:
                raise AppError("STATE_CONFLICT", "私人问答结果关联损坏", 409)
            return PblMessageSubmissionRecord(
                current,
                completion,
                "private_follow_up",
                "private_follow_up",
                duplicate.private_follow_up,
            )

        turn_scope = "private_follow_up" if participation.phase_status == "completed" else "evidence"
        if turn_scope == "private_follow_up":
            self._require_completion_snapshot(participation)
        else:
            self._require_student_session(student_id, session_id)
        updated = self._repository.append_student_message(
            participation.id, client_message_id, normalized, style, turn_scope
        )
        if updated is None:
            raise AppError("STATE_CONFLICT", "消息正在处理", 409)

        # Persist the idempotency key before the external call. The result write
        # checks the same revision, so a concurrent outcome cannot overwrite it.
        self._uow.commit()
        session = self._repository.get_session(session_id)
        if session is None:
            raise AppError("RESOURCE_NOT_FOUND", "课堂不存在", 404)
        if turn_scope == "private_follow_up":
            latest_message = updated.messages[-1]
            private_result = self._gateway.private_follow_up(
                PrivateFollowupRequest(
                    session_ref=self._anonymous_ref("session", session.id),
                    participation_ref=self._anonymous_ref("participation", updated.id),
                    interaction_style=style,
                    learning_topic=session.topic_code,
                    learning_goals=session.goal_point_codes,
                    messages=updated.messages,
                    latest_student_message_id=int(latest_message["id"]),
                    # Do not attach the evidence-phase provider conversation. The
                    # bounded, server-selected message window is the private context.
                    conversation_ref=None,
                )
            )
            private_result = replace(
                private_result,
                provider_metadata={
                    **(private_result.provider_metadata or {}),
                    "provider": self._provider,
                    **({"mode": self._mode} if self._mode else {}),
                },
            )
            saved_private = self._repository.save_private_follow_up_result(updated.id, updated.revision, private_result)
            if saved_private is None:
                self._uow.rollback()
                raise AppError("STATE_CONFLICT", "对话已更新，请重试", 409)
            current = self._repository.participation(updated.id)
            if current is None:
                self._uow.rollback()
                raise AppError("STATE_CONFLICT", "对话已更新，请重试", 409)
            completion = self._require_completion_snapshot(current)
            self._uow.commit()
            return PblMessageSubmissionRecord(
                current, completion, "private_follow_up", "private_follow_up", saved_private
            )
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
                interaction_style=updated.messages[-1]["interaction_style"],
                session_kind=session.session_kind,
                schema_version=session.ai_schema_version,
                allowed_resource_refs=(),
                allowed_points=tuple(
                    {"code": str(point["code"]), "title": str(point["title"])}
                    for point in self._knowledge_catalog.tree_view()
                ),
            )
        )
        snapshot = self._repository.save_result(updated.id, updated.revision, result)
        if snapshot is None:
            self._uow.rollback()
            raise AppError("STATE_CONFLICT", "对话已更新，请重试", 409)
        current = self._repository.participation(updated.id)
        if current is None:
            raise AppError("STATE_CONFLICT", "对话已更新，请重试", 409)
        if (
            self._learning_evidence is not None
            and session.session_kind == "student_initiated"
            and current.current_phase == "completed"
        ):
            self._learning_evidence.append(
                LearningEvidenceCommand(
                    student_id=student_id,
                    class_id=None,
                    source_type="self_pbl_completion",
                    source_id=str(session.id),
                    source_version=snapshot.schema_version,
                    authority_level="personal_unverified",
                    visibility_scope="student_only",
                    event_kind="engagement",
                    occurred_at=snapshot.created_at or datetime.now(UTC),
                    dedupe_key=f"self-pbl-completion:{session.id}:v{snapshot.schema_version}",
                    metrics=tuple(
                        LearningEvidenceMetricCommand("knowledge", code, result="observed")
                        for code in session.goal_point_codes
                    ),
                )
            )
        locator = None
        if current.evidence_locked and self._completion_routes is not None:
            completion = self._require_completion_snapshot(current)
            if (
                completion.status != "ready"
                or completion.safety_status != "educational"
                or completion.revision != current.evidence_completed_revision
            ):
                self._uow.rollback()
                raise AppError("STATE_CONFLICT", "完成分析尚未就绪", 409)
            locator = self._completion_routes.ensure_shell(
                {
                    "student_id": student_id,
                    "source_participation_id": current.id,
                    "session_id": session.id,
                    "completion_snapshot_id": completion.id,
                    "source_kind": "classroom" if session.session_kind == "classroom" else "autonomous",
                    "class_id": session.class_id,
                    "teacher_id": session.teacher_id,
                    "goal_point_codes": session.goal_point_codes,
                    "diagnosis_summary": {
                        "knowledge_gaps": list(completion.knowledge_gaps),
                        "reasoning_issues": list(completion.reasoning_issues),
                        "diagnosis_outcome": completion.diagnosis_outcome,
                    },
                }
            )
        self._uow.commit()
        return PblMessageSubmissionRecord(
            current,
            snapshot,
            "evidence_assessment",
            "evidence",
            learning_route_id=locator["route_id"] if locator else None,
            final_test_id=locator["test_id"] if locator else None,
            route_generation_state="pending" if locator else None,
            test_generation_state="pending" if locator else None,
            learning_route_created=locator["created"] if locator else False,
        )

    @staticmethod
    def _anonymous_ref(kind: str, value: int) -> str:
        return f"pbl-{kind}-{sha256(f'{kind}:{value}'.encode()).hexdigest()[:24]}"

    def _require_completion_snapshot(self, participation: PblParticipationRecord) -> PblSnapshotRecord:
        snapshot = self._repository.completion_snapshot(participation.id)
        if snapshot is None:
            raise AppError("STATE_CONFLICT", "完成证据边界不完整，请刷新后重试", 409)
        return snapshot

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
        from app.modules.learning.public import retired_learning_flow

        retired_learning_flow()

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
        from app.modules.learning.public import retired_learning_flow

        retired_learning_flow()

    def _work_status(self, teacher_id: int, value: PblDiagnosticRecord, feedbacks) -> str:
        locator = (
            self._completion_routes.review_locator(teacher_id, value.snapshot.participation_id)
            if self._completion_routes
            else None
        )
        return "task_published" if locator and locator["review_state"] == "released" else "pending"

    def _work_item_view(self, teacher_id: int, value: PblDiagnosticRecord, feedbacks) -> dict:
        locator = (
            self._completion_routes.review_locator(teacher_id, value.snapshot.participation_id)
            if self._completion_routes
            else None
        )
        state = "task_published" if locator and locator["review_state"] == "released" else "pending"
        return {
            "snapshot_id": value.snapshot.id,
            "session_id": value.session_id,
            "source": "classroom_diagnostic",
            "read_only": False,
            "status": state,
            "package_id": None,
            "learning_route_id": locator["learning_route_id"] if locator else None,
            "final_test_id": locator["final_test_id"] if locator else None,
            "test_generation_state": locator["generation_state"] if locator else None,
            "test_review_state": locator["review_state"] if locator else None,
            "student": {"id": value.student_id, "name": value.student_name},
            "class": {"id": value.class_id, "name": value.class_name},
            "topic": value.topic_code,
            "entered_at": value.snapshot.created_at,
            "last_activity_at": locator["updated_at"] if locator else value.snapshot.created_at,
            "knowledge_gap_count": len(value.snapshot.knowledge_gaps),
            "reasoning_issue_count": len(value.snapshot.reasoning_issues),
            "next_action": "查看学习进展" if state == "task_published" else "审阅最终测试",
        }

    def work_items(self, teacher_id: int, limit: int, offset: int, filters: dict):
        # Status is derived from append-only feedback and published suggestions, so it must be
        # applied before pagination.  Source/class filtering remains in the repository query.
        diagnostic_filters = {key: value for key, value in filters.items() if key != "work_status"}
        values, _ = self.diagnostics(teacher_id, 10000, 0, diagnostic_filters)
        all_items = []
        for value in values:
            item = self._work_item_view(teacher_id, value, ())
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
        return {
            "work_item": self._work_item_view(teacher_id, diagnostic, ()),
            "diagnostic": diagnostic,
            "feedbacks": (),
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
        from app.modules.learning.public import retired_learning_flow

        retired_learning_flow()

    def follow_ups(self, teacher_id: int, limit: int, offset: int, filters: dict):
        return {"items": [], "total": 0, "limit": limit, "offset": offset}

    def follow_up(self, teacher_id: int, plan_id: int):
        raise AppError("RESOURCE_NOT_FOUND", "学习跟进不存在", 404)

    def follow_up_feedback(self, teacher_id: int, plan_id: int, client_feedback_id: str, body: str):
        from app.modules.learning.public import retired_learning_flow

        retired_learning_flow()

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
                    "class_name": self._classroom_scope.owned(teacher_id, item.class_id).name,
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
        session = self._repository.get_session(session_id)
        if (
            session is None
            or session.session_kind != "classroom"
            or session.class_id != class_id
            or session.teacher_id != teacher_id
            or self._classroom_scope.owned(teacher_id, class_id) is None
        ):
            raise AppError("RESOURCE_NOT_FOUND", "课堂不存在", 404)
        progress = (
            self._completion_routes.classroom_progress(teacher_id, class_id, session_id)
            if self._completion_routes
            else []
        )
        by_student = {item["student_id"]: item for item in progress}
        names = {item.id: item.nickname for item in self._classroom_scope.students(teacher_id, class_id)}
        rows = []
        for source in self._repository.session_dashboard_rows(session_id):
            state = by_student.get(source["student_id"], {})
            rows.append(
                {
                    **source,
                    "student_name": names.get(source["student_id"], "已离班学生"),
                    "learning_route_id": state.get("learning_route_id"),
                    "final_test_id": state.get("final_test_id"),
                    "result_id": state.get("result_id"),
                    "route_status": state.get("route_status"),
                    "score": state.get("score"),
                    "work_item_status": state.get("work_item_status"),
                    "task_progress": state.get("task_progress", {"completed": 0, "total": 0}),
                }
            )
        published = [item for item in progress if item["generation_state"] == "published"]
        scores = [item["score"] for item in published if item["score"] is not None]
        counts = self._repository.session_counts(session_id)
        summary = {
            **counts,
            "published_routes": len(published),
            "completed_routes": len(scores),
            "completion_rate": round(len(scores) * 100 / len(published), 1) if published else None,
            "average_score": round(sum(scores) / len(scores), 1) if scores else None,
        }
        return {
            "session": {"id": session.id, "class_id": class_id, "status": session.status},
            "summary": summary,
            "students": rows,
        }

    def learning_plans(self, student_id: int):
        return ()

    def _catalog_labels(self) -> tuple[dict[str, str], dict[str, str]]:
        point_labels = {str(point["code"]): str(point["title"]) for point in self._knowledge_catalog.tree_view()}
        return point_labels, self._knowledge_catalog.module_labels()

    def learning_report_page(self, student_id: int, limit: int, offset: int):
        return {"items": [], "total": 0, "limit": limit, "offset": offset}

    def learning_report(self, student_id: int, session_id: int):
        raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)

    def submit_task(self, student_id: int, task_id: int, submission_id: str, answer: dict):
        from app.modules.learning.public import retired_learning_flow

        retired_learning_flow()

    def learning_results(self, teacher_id: int, session_id: int | None = None):
        return ()

    def verify_learning(self, teacher_id: int, plan_id: int, version: int, decision: str, note: str):
        from app.modules.learning.public import retired_learning_flow

        retired_learning_flow()

    def summary(self, teacher_id: int, class_id: int, session_id: int):
        return self.session_dashboard(teacher_id, class_id, session_id)["summary"]

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

    def _require_classroom_diagnostic(self, teacher_id: int, snapshot_id: int) -> PblDiagnosticRecord:
        diagnostic = self.diagnostic(teacher_id, snapshot_id)
        if diagnostic.session_kind != "classroom":
            raise AppError("STATE_CONFLICT", "历史共享记录仅供查看，不能继续处置", 409)
        return diagnostic
