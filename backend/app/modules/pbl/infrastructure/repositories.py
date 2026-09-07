from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.modules.pbl.application.records import (
    InferenceResult,
    PblDiagnosticRecord,
    PblParticipationRecord,
    PblReportParticipationRecord,
    PblSessionRecord,
    PblSnapshotRecord,
    PblSuggestionRecord,
)
from app.modules.pbl.infrastructure.models import (
    PblDiagnosticSnapshot,
    PblMessage,
    PblParticipation,
    PblQuestionSuggestion,
    PblSession,
)
from app.shared.errors import AppError, PersistenceConflict


class SqlAlchemyPblRepository:
    """PBL-owned persistence adapter; all ORM work stays below the application layer."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _session_record(value: PblSession) -> PblSessionRecord:
        return PblSessionRecord(
            id=value.id,
            class_id=value.class_id,
            teacher_id=value.teacher_id,
            topic_code=value.topic_code,
            provider=value.provider,
            invocation_mode=value.invocation_mode,
            status=value.status,
            created_at=value.created_at,
            closed_at=value.closed_at,
            case_id=value.case_id,
            case_version=value.case_version,
            case_digest=value.case_digest,
            case_context=value.case_context,
            goal_point_codes=tuple(value.goal_point_codes),
            phase=value.phase,
            version=value.version,
            session_kind=value.session_kind,
            created_by_student_id=value.created_by_student_id,
            client_session_id=value.client_session_id,
        )

    def _part_record(self, value: PblParticipation) -> PblParticipationRecord:
        messages = self._session.scalars(
            select(PblMessage).where(PblMessage.participation_id == value.id).order_by(PblMessage.sequence.asc())
        ).all()
        return PblParticipationRecord(
            id=value.id,
            session_id=value.session_id,
            student_id=value.student_id,
            coze_user_ref=value.coze_user_ref,
            coze_conversation_ref=value.coze_conversation_ref,
            messages=tuple(
                {
                    "id": str(message.id),
                    "sequence": message.sequence,
                    "request_revision": message.request_revision,
                    "processing_status": message.processing_status,
                    "role": message.role,
                    "content": message.content,
                    **({"client_message_id": message.client_message_id} if message.client_message_id else {}),
                }
                for message in messages
            ),
            revision=value.revision,
            current_phase=value.current_phase,
            phase_started_revision=value.phase_started_revision,
            phase_status=value.phase_status,
            phase_completed_at=value.phase_completed_at,
            interaction_style=value.interaction_style,
            style_selected_at=value.style_selected_at,
        )

    @staticmethod
    def _snapshot_record(value: PblDiagnosticSnapshot) -> PblSnapshotRecord:
        return PblSnapshotRecord(
            value.id,
            value.participation_id,
            value.revision,
            value.status,
            value.assistant_reply,
            value.follow_up_question,
            tuple(value.knowledge_gaps or []),
            tuple(value.reasoning_issues or []),
            dict(value.provider_metadata or {}),
            value.failure_reason,
            value.schema_version,
            value.safety_notice,
            value.safety_status,
            value.created_at,
            value.phase,
            value.phase_decision,
            tuple(value.phase_evidence_message_ids or []),
            value.phase_evidence_summary or "",
            tuple(value.phase_missing_elements or []),
        )

    @staticmethod
    def _suggestion_record(value: PblQuestionSuggestion) -> PblSuggestionRecord:
        return PblSuggestionRecord(
            value.id,
            value.snapshot_id,
            value.title,
            value.prompt,
            tuple(value.linked_findings or []),
            value.status,
            value.version,
            value.problem_id,
        )

    def create_session(
        self,
        class_id: int,
        teacher_id: int,
        topic_code: str,
        provider: str,
        mode: str | None,
        context: dict,
        goals: tuple[str, ...],
        session_kind: str = "classroom",
        created_by_student_id: int | None = None,
        client_session_id: str | None = None,
    ) -> PblSessionRecord:
        value = PblSession(
            class_id=class_id,
            teacher_id=teacher_id,
            topic_code=topic_code,
            provider=provider,
            invocation_mode=mode,
            session_kind=session_kind,
            created_by_student_id=created_by_student_id,
            client_session_id=client_session_id,
            **context,
            goal_point_codes=list(goals),
        )
        self._session.add(value)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise PersistenceConflict from error
        return self._session_record(value)

    def get_session(self, session_id: int) -> PblSessionRecord | None:
        value = self._session.get(PblSession, session_id)
        return self._session_record(value) if value else None

    def close_session(self, session_id: int) -> PblSessionRecord:
        value = self._session.get(PblSession, session_id)
        assert value is not None
        if value.status != "closed":
            value.version += 1
            value.status = "closed"
            value.closed_at = datetime.now(UTC)
            self._session.flush()
        return self._session_record(value)

    def list_active_sessions(self, class_ids: tuple[int, ...], student_id: int) -> tuple[PblSessionRecord, ...]:
        values = self._session.scalars(
            select(PblSession)
            .where(
                or_(
                    (PblSession.class_id.in_(class_ids))
                    & (PblSession.status == "active")
                    & (
                        (PblSession.session_kind == "classroom")
                        | (PblSession.created_by_student_id == student_id)
                    ),
                    exists().where(
                        PblParticipation.session_id == PblSession.id, PblParticipation.student_id == student_id
                    ),
                )
            )
            .order_by(PblSession.id.desc())
        ).all()
        return tuple(self._session_record(value) for value in values)

    def list_sessions_for_teacher(self, teacher_id: int, class_id: int) -> tuple[PblSessionRecord, ...]:
        values = self._session.scalars(
            select(PblSession)
            .where(
                PblSession.teacher_id == teacher_id,
                PblSession.class_id == class_id,
                PblSession.session_kind == "classroom",
            )
            .order_by(PblSession.id.desc())
        ).all()
        return tuple(self._session_record(value) for value in values)

    def get_or_create_participation(
        self, session_id: int, student_id: int, interaction_style: str = "guided"
    ) -> PblParticipationRecord:
        value = self._session.scalar(
            select(PblParticipation).where(
                PblParticipation.session_id == session_id,
                PblParticipation.student_id == student_id,
            )
        )
        if value is None:
            value = PblParticipation(
                session_id=session_id,
                student_id=student_id,
                coze_user_ref=f"pbl-{session_id}-{student_id}",
                interaction_style=interaction_style,
            )
            self._session.add(value)
            self._session.flush()
        return self._part_record(value)

    def find_student_session_by_client_id(
        self, student_id: int, client_session_id: str
    ) -> PblSessionRecord | None:
        value = self._session.scalar(
            select(PblSession).where(
                PblSession.created_by_student_id == student_id,
                PblSession.client_session_id == client_session_id,
            )
        )
        return self._session_record(value) if value else None

    def latest_snapshot(self, participation_id: int) -> PblSnapshotRecord | None:
        value = self._session.scalar(
            select(PblDiagnosticSnapshot)
            .where(PblDiagnosticSnapshot.participation_id == participation_id)
            .order_by(PblDiagnosticSnapshot.revision.desc())
        )
        return self._snapshot_record(value) if value else None

    def report_participations(self, student_id: int) -> tuple[PblReportParticipationRecord, ...]:
        values = self._session.scalars(
            select(PblParticipation)
            .where(PblParticipation.student_id == student_id)
            .order_by(PblParticipation.updated_at.desc(), PblParticipation.id.desc())
        ).all()
        result = []
        for value in values:
            session = self._session.get(PblSession, value.session_id)
            if session is None:
                continue
            snapshots = self._session.scalars(
                select(PblDiagnosticSnapshot)
                .where(PblDiagnosticSnapshot.participation_id == value.id)
                .order_by(PblDiagnosticSnapshot.revision.asc())
            ).all()
            participation = PblParticipationRecord(
                id=value.id,
                session_id=value.session_id,
                student_id=value.student_id,
                coze_user_ref=value.coze_user_ref,
                coze_conversation_ref=value.coze_conversation_ref,
                messages=(),
                revision=value.revision,
                current_phase=value.current_phase,
                phase_started_revision=value.phase_started_revision,
                phase_status=value.phase_status,
                phase_completed_at=value.phase_completed_at,
                interaction_style=value.interaction_style,
                style_selected_at=value.style_selected_at,
            )
            result.append(
                PblReportParticipationRecord(
                    self._session_record(session),
                    participation,
                    tuple(self._snapshot_record(snapshot) for snapshot in snapshots),
                )
            )
        return tuple(result)

    def append_student_message(
        self, participation_id: int, client_message_id: str, content: str
    ) -> PblParticipationRecord | None:
        self._expire_pending(participation_id)
        value = self._session.get(PblParticipation, participation_id)
        assert value is not None
        duplicate = self._session.scalar(
            select(PblMessage).where(
                PblMessage.participation_id == participation_id, PblMessage.client_message_id == client_message_id
            )
        )
        if duplicate:
            if duplicate.content != content:
                raise AppError("STATE_CONFLICT", "消息标识已用于其他内容", 409)
            return None
        pending = self._session.scalar(
            select(PblMessage.id).where(
                PblMessage.participation_id == participation_id, PblMessage.processing_status == "pending"
            )
        )
        if pending:
            raise AppError("STATE_CONFLICT", "上一条消息仍在处理", 409)
        revision = value.revision
        changed = self._session.execute(
            update(PblParticipation)
            .where(PblParticipation.id == participation_id, PblParticipation.revision == revision)
            .values(revision=revision + 1)
        )
        if changed.rowcount != 1:
            raise AppError("STATE_CONFLICT", "对话已更新", 409)
        sequence = (
            self._session.scalar(
                select(func.max(PblMessage.sequence)).where(PblMessage.participation_id == participation_id)
            )
            or 0
        ) + 1
        self._session.add(
            PblMessage(
                participation_id=participation_id,
                sequence=sequence,
                role="student",
                content=content,
                client_message_id=client_message_id,
                request_revision=revision + 1,
                processing_status="pending",
            )
        )
        self._session.flush()
        self._session.refresh(value)
        return self._part_record(value)

    def save_result(self, participation_id: int, revision: int, result: InferenceResult) -> PblSnapshotRecord | None:
        part = self._session.get(PblParticipation, participation_id)
        if part is None:
            return None
        changed = self._session.execute(
            update(PblMessage)
            .where(
                PblMessage.participation_id == participation_id,
                PblMessage.request_revision == revision,
                PblMessage.processing_status == "pending",
                exists().where(PblParticipation.id == participation_id, PblParticipation.revision == revision),
            )
            .values(processing_status="completed")
        )
        if changed.rowcount != 1:
            return None
        gaps = list(result.knowledge_gaps)[:10]
        issues = list(result.reasoning_issues)[:10]
        recommendations = list(result.recommended_questions)[:5]
        if result.diagnostic_status != "ready" or not (gaps or issues):
            recommendations = []
        assessment = result.phase_assessment or {}
        assessed_phase = str(assessment.get("phase") or part.current_phase)
        phase_decision = str(assessment.get("decision") or "unavailable")
        snapshot = PblDiagnosticSnapshot(
            participation_id=part.id,
            revision=revision,
            status=result.diagnostic_status,
            assistant_reply=result.assistant_reply[:4000],
            follow_up_question=result.follow_up_question,
            knowledge_gaps=gaps,
            reasoning_issues=issues,
            provider_metadata=result.provider_metadata or {},
            failure_reason=result.failure_reason,
            schema_version=result.schema_version,
            safety_notice=result.safety_notice,
            safety_status=result.safety_status,
            phase=assessed_phase,
            phase_decision=phase_decision,
            phase_evidence_message_ids=list(assessment.get("evidence_message_ids") or []),
            phase_evidence_summary=str(assessment.get("evidence_summary") or "")[:500],
            phase_missing_elements=[str(item)[:200] for item in assessment.get("missing_elements", [])][:10],
        )
        self._session.add(snapshot)
        if result.conversation_ref:
            part.coze_conversation_ref = result.conversation_ref[:120]
        if phase_decision == "advance":
            phases = ("problem_framing", "hypothesis", "evidence", "synthesis")
            index = phases.index(part.current_phase)
            part.current_phase = phases[index + 1]
            part.phase_started_revision = revision
            part.phase_status = "active"
        elif phase_decision == "complete":
            part.current_phase = "completed"
            part.phase_started_revision = revision
            part.phase_status = "completed"
            part.phase_completed_at = datetime.now(UTC)
        self._session.flush()
        self._session.execute(
            update(PblMessage)
            .where(PblMessage.participation_id == participation_id, PblMessage.request_revision == revision)
            .values(result_snapshot_id=snapshot.id)
        )
        next_sequence = (
            self._session.scalar(select(func.max(PblMessage.sequence)).where(PblMessage.participation_id == part.id))
            or 0
        ) + 1
        self._session.add(
            PblMessage(
                participation_id=part.id,
                sequence=next_sequence,
                role="assistant",
                processing_status="completed",
                content=result.assistant_reply[:4000],
            )
        )
        proposed = self._session.scalars(
            select(PblQuestionSuggestion)
            .join(PblDiagnosticSnapshot)
            .where(
                PblDiagnosticSnapshot.participation_id == part.id,
                PblQuestionSuggestion.status.in_(("proposed", "edited")),
            )
        ).all()
        for old in proposed:
            old.status = "superseded"
        for item in recommendations:
            linked_findings = [str(value) for value in item.get("linked_findings", [])][:5]
            if linked_findings:
                self._session.add(
                    PblQuestionSuggestion(
                        snapshot_id=snapshot.id,
                        title=str(item.get("title", "PBL 讨论题"))[:200],
                        prompt=str(item.get("prompt", ""))[:2000],
                        linked_findings=linked_findings,
                    )
                )
        self._session.flush()
        return self._snapshot_record(snapshot)

    def participation(self, participation_id: int) -> PblParticipationRecord | None:
        value = self._session.get(PblParticipation, participation_id)
        return self._part_record(value) if value else None

    def _diagnostic_record(self, snapshot: PblDiagnosticSnapshot) -> PblDiagnosticRecord:
        part = self._session.get(PblParticipation, snapshot.participation_id)
        session = self._session.get(PblSession, part.session_id)
        return PblDiagnosticRecord(
            self._snapshot_record(snapshot),
            tuple(
                self._suggestion_record(value)
                for value in self._session.scalars(
                    select(PblQuestionSuggestion).where(PblQuestionSuggestion.snapshot_id == snapshot.id)
                ).all()
            ),
            student_id=part.student_id,
            class_id=session.class_id,
            session_id=session.id,
            topic_code=session.topic_code,
            session_kind=session.session_kind,
            interaction_style=part.interaction_style,
        )

    def diagnostics_for_teacher(self, teacher_id: int, limit: int, offset: int, filters: dict):
        newer = aliased(PblDiagnosticSnapshot)
        statement = (
            select(PblDiagnosticSnapshot)
            .join(PblParticipation)
            .join(PblSession)
            .where(
                PblSession.teacher_id == teacher_id,
                PblDiagnosticSnapshot.status == "ready",
                ~exists().where(
                    newer.participation_id == PblDiagnosticSnapshot.participation_id,
                    newer.status == "ready",
                    newer.revision > PblDiagnosticSnapshot.revision,
                ),
            )
        )
        for key, column in (
            ("class_id", PblSession.class_id),
            ("session_id", PblSession.id),
            ("student_id", PblParticipation.student_id),
        ):
            if filters.get(key):
                statement = statement.where(column == filters[key])
        if filters.get("status"):
            statement = statement.where(
                exists().where(
                    PblQuestionSuggestion.snapshot_id == PblDiagnosticSnapshot.id,
                    PblQuestionSuggestion.status == filters["status"],
                )
            )
        total = self._session.scalar(select(func.count()).select_from(statement.subquery()))
        snapshots = self._session.scalars(
            statement.order_by(PblDiagnosticSnapshot.id.desc()).limit(limit).offset(offset)
        ).all()
        return tuple(self._diagnostic_record(snapshot) for snapshot in snapshots), int(total or 0)

    def diagnostic_for_teacher(self, teacher_id: int, snapshot_id: int) -> PblDiagnosticRecord | None:
        snapshot = self._session.scalar(
            select(PblDiagnosticSnapshot)
            .join(PblParticipation)
            .join(PblSession)
            .where(
                PblDiagnosticSnapshot.id == snapshot_id,
                PblSession.teacher_id == teacher_id,
                PblDiagnosticSnapshot.status == "ready",
            )
        )
        return self._diagnostic_record(snapshot) if snapshot else None

    def suggestion_for_teacher(self, teacher_id: int, suggestion_id: int) -> PblSuggestionRecord | None:
        value = self._session.get(PblQuestionSuggestion, suggestion_id)
        if value is None:
            return None
        owner = self._session.scalar(
            select(PblSession.teacher_id)
            .join(PblParticipation, PblParticipation.session_id == PblSession.id)
            .join(PblDiagnosticSnapshot, PblDiagnosticSnapshot.participation_id == PblParticipation.id)
            .where(PblDiagnosticSnapshot.id == value.snapshot_id)
        )
        return self._suggestion_record(value) if owner == teacher_id else None

    def session_for_suggestion(self, suggestion_id: int) -> PblSessionRecord | None:
        value = self._session.scalar(
            select(PblSession)
            .join(PblParticipation, PblParticipation.session_id == PblSession.id)
            .join(PblDiagnosticSnapshot, PblDiagnosticSnapshot.participation_id == PblParticipation.id)
            .join(PblQuestionSuggestion, PblQuestionSuggestion.snapshot_id == PblDiagnosticSnapshot.id)
            .where(PblQuestionSuggestion.id == suggestion_id)
        )
        return self._session_record(value) if value else None

    def update_suggestion(
        self, suggestion_id: int, title: str, prompt: str, status: str, version: int
    ) -> PblSuggestionRecord:
        value = self._session.get(PblQuestionSuggestion, suggestion_id)
        assert value is not None
        changed = self._session.execute(
            update(PblQuestionSuggestion)
            .where(
                PblQuestionSuggestion.id == suggestion_id,
                PblQuestionSuggestion.version == version - 1,
                PblQuestionSuggestion.status.in_(("proposed", "edited")),
            )
            .values(title=title, prompt=prompt, status=status, version=version)
        )
        if changed.rowcount != 1:
            raise AppError("STATE_CONFLICT", "建议版本或状态已更新", 409)
        self._session.flush()
        self._session.refresh(value)
        return self._suggestion_record(value)

    def attach_problem(self, suggestion_id: int, problem_id: int, version: int) -> PblSuggestionRecord:
        value = self._session.get(PblQuestionSuggestion, suggestion_id)
        assert value is not None
        value.problem_id = problem_id
        value.status = "published"
        value.version = version
        self._session.flush()
        return self._suggestion_record(value)

    def find_participation(self, session_id: int, student_id: int):
        value = self._session.scalar(
            select(PblParticipation).where(
                PblParticipation.session_id == session_id, PblParticipation.student_id == student_id
            )
        )
        return self._part_record(value) if value else None

    def message_result(self, participation_id: int, client_message_id: str):
        self._expire_pending(participation_id)
        message = self._session.scalar(
            select(PblMessage).where(
                PblMessage.participation_id == participation_id, PblMessage.client_message_id == client_message_id
            )
        )
        snapshot = (
            self._session.get(PblDiagnosticSnapshot, message.result_snapshot_id)
            if message and message.result_snapshot_id
            else None
        )
        return self._snapshot_record(snapshot) if snapshot else None

    def _expire_pending(self, participation_id: int):
        stale = self._session.scalar(
            select(PblMessage).where(
                PblMessage.participation_id == participation_id,
                PblMessage.processing_status == "pending",
                PblMessage.created_at < datetime.now(UTC) - timedelta(seconds=60),
            )
        )
        if stale:
            self.save_result(
                participation_id,
                stale.request_revision,
                InferenceResult(
                    assistant_reply="上一次请求处理已中断，未生成诊断。请重新提问继续。",
                    diagnostic_status="unavailable",
                    failure_reason="interrupted_request",
                ),
            )

    def revisions_for_teacher(self, teacher_id: int, snapshot_id: int):
        diagnostic = self.diagnostic_for_teacher(teacher_id, snapshot_id)
        if not diagnostic:
            return ()
        rows = self._session.scalars(
            select(PblDiagnosticSnapshot)
            .where(
                PblDiagnosticSnapshot.participation_id == diagnostic.snapshot.participation_id,
                PblDiagnosticSnapshot.status == "ready",
            )
            .order_by(PblDiagnosticSnapshot.revision.desc())
        ).all()
        return tuple(self._diagnostic_record(row) for row in rows)

    def session_counts(self, session_id: int):
        parts = select(PblParticipation.id).where(PblParticipation.session_id == session_id)
        snapshots = select(PblDiagnosticSnapshot.id).where(
            PblDiagnosticSnapshot.participation_id.in_(parts),
            PblDiagnosticSnapshot.status == "ready",
            PblDiagnosticSnapshot.schema_version.in_((3, 4)),
        )
        phase_rows = self._session.execute(
            select(PblParticipation.current_phase, func.count(PblParticipation.id))
            .where(PblParticipation.session_id == session_id)
            .group_by(PblParticipation.current_phase)
        ).all()
        return {
            "participants": self._session.scalar(select(func.count()).select_from(parts.subquery())) or 0,
            "diagnoses": self._session.scalar(select(func.count()).select_from(snapshots.subquery())) or 0,
            "published_suggestions": self._session.scalar(
                select(func.count(PblQuestionSuggestion.id)).where(
                    PblQuestionSuggestion.snapshot_id.in_(snapshots), PblQuestionSuggestion.status == "published"
                )
            )
            or 0,
            "phase_counts": {str(phase): int(count) for phase, count in phase_rows},
        }
