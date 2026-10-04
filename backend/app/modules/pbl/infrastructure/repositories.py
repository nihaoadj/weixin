from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, exists, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.classroom.infrastructure.models import ClassRoom
from app.modules.classroom.public import ClassroomScopePort
from app.modules.pbl.application.records import (
    InferenceResult,
    PblDiagnosticRecord,
    PblMessageResultRecord,
    PblParticipationRecord,
    PblPrivateFollowUpResultRecord,
    PblSessionRecord,
    PblSnapshotRecord,
    PrivateFollowupResult,
)
from app.modules.pbl.infrastructure.models import (
    PblDiagnosticSnapshot,
    PblMessage,
    PblParticipation,
    PblPrivateFollowUpResult,
    PblSession,
)
from app.modules.pbl.infrastructure.providers.coze_parser import unavailable_private_follow_up, unavailable_result
from app.modules.pbl.public import (
    PblStudentInsightRecord,
    PblTeacherDiagnosisRecord,
    PblTeacherDiscussionRecord,
    PblTeacherFinding,
)
from app.shared.errors import AppError, PersistenceConflict


class SqlAlchemyPblRepository:
    """PBL-owned persistence adapter; all ORM work stays below the application layer."""

    def __init__(self, session: Session, scope: ClassroomScopePort | None = None) -> None:
        self._session = session
        self._scope = scope

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
            ai_schema_version=value.ai_schema_version,
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
                    "interaction_style": message.interaction_style,
                    "turn_scope": message.turn_scope,
                    **({"reply_to_message_id": message.reply_to_message_id} if message.reply_to_message_id else {}),
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
            completion_snapshot_id=value.completion_snapshot_id,
            evidence_completed_revision=value.evidence_completed_revision,
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
            value.interaction_style,
            value.diagnosis_outcome,
            (),
        )

    def _private_record(self, value: PblPrivateFollowUpResult) -> PblPrivateFollowUpResultRecord:
        assistant = self._session.get(PblMessage, value.assistant_message_id)
        if assistant is None:
            raise AppError("STATE_CONFLICT", "私人问答结果关联损坏", 409)
        return PblPrivateFollowUpResultRecord(
            id=value.id,
            participation_id=value.participation_id,
            student_message_id=value.student_message_id,
            assistant_message_id=value.assistant_message_id,
            interaction_style=value.interaction_style,
            schema_version=value.schema_version,
            processing_status=value.processing_status,
            safety_status=value.safety_status,
            safety_notice=value.safety_notice,
            provider_name=value.provider_name,
            provider_mode=value.provider_mode,
            fallback_used=value.fallback_used,
            failure_category=value.failure_category,
            assistant_reply=assistant.content,
            created_at=value.created_at,
        )

    def create_session(
        self,
        class_id: int | None,
        teacher_id: int | None,
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
            ai_schema_version=8,
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
                    & ((PblSession.session_kind == "classroom") | (PblSession.created_by_student_id == student_id)),
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

    def set_interaction_style(self, participation_id: int, interaction_style: str) -> PblParticipationRecord:
        self._session.execute(
            update(PblParticipation)
            .where(
                PblParticipation.id == participation_id,
                PblParticipation.interaction_style != interaction_style,
                PblParticipation.phase_status != "completed",
            )
            .values(interaction_style=interaction_style, style_selected_at=datetime.now(UTC))
        )
        self._session.flush()
        return self.participation(participation_id)

    def find_student_session_by_client_id(self, student_id: int, client_session_id: str) -> PblSessionRecord | None:
        value = self._session.scalar(
            select(PblSession).where(
                PblSession.created_by_student_id == student_id,
                PblSession.client_session_id == client_session_id,
            )
        )
        return self._session_record(value) if value else None

    def latest_snapshot(self, participation_id: int) -> PblSnapshotRecord | None:
        participation = self._session.get(PblParticipation, participation_id)
        if participation and participation.phase_status == "completed":
            return self.completion_snapshot(participation_id)
        value = self._session.scalar(
            select(PblDiagnosticSnapshot)
            .where(PblDiagnosticSnapshot.participation_id == participation_id)
            .order_by(PblDiagnosticSnapshot.revision.desc())
        )
        return self._snapshot_record(value) if value else None

    def completion_snapshot(self, participation_id: int) -> PblSnapshotRecord | None:
        participation = self._session.get(PblParticipation, participation_id)
        if (
            participation is None
            or participation.phase_status != "completed"
            or not participation.completion_snapshot_id
        ):
            return None
        value = self._session.get(PblDiagnosticSnapshot, participation.completion_snapshot_id)
        if (
            value is None
            or value.participation_id != participation_id
            or value.phase_decision != "complete"
            or value.status != "ready"
            or participation.evidence_completed_revision != value.revision
        ):
            return None
        return self._snapshot_record(value)

    def student_insight_records(self, student_id: int) -> tuple[PblStudentInsightRecord, ...]:
        rows = self._session.execute(
            select(PblSession, PblParticipation, PblDiagnosticSnapshot)
            .join(PblParticipation, PblParticipation.session_id == PblSession.id)
            .outerjoin(
                PblDiagnosticSnapshot,
                and_(
                    PblDiagnosticSnapshot.id == PblParticipation.completion_snapshot_id,
                    PblParticipation.phase_status == "completed",
                    PblDiagnosticSnapshot.participation_id == PblParticipation.id,
                    PblDiagnosticSnapshot.revision == PblParticipation.evidence_completed_revision,
                    PblDiagnosticSnapshot.phase_decision == "complete",
                    PblDiagnosticSnapshot.status == "ready",
                ),
            )
            .where(
                PblParticipation.student_id == student_id,
                PblParticipation.revision > 0,
                or_(PblSession.session_kind != "student_initiated", PblSession.created_by_student_id == student_id),
            )
            .order_by(PblParticipation.updated_at.desc(), PblParticipation.id.desc())
        ).all()
        records = []
        for session, participation, snapshot in rows:
            case_context = session.case_context if isinstance(session.case_context, dict) else {}
            case_title = str(case_context.get("title") or "研讨记录").strip()[:100] or "研讨记录"
            gaps = snapshot.knowledge_gaps if snapshot and isinstance(snapshot.knowledge_gaps, list) else []
            issues = snapshot.reasoning_issues if snapshot and isinstance(snapshot.reasoning_issues, list) else []
            records.append(
                PblStudentInsightRecord(
                    participation_id=participation.id,
                    session_id=session.id,
                    topic_code=session.topic_code,
                    case_title=case_title,
                    session_kind=session.session_kind,
                    goal_point_codes=tuple(session.goal_point_codes or ()),
                    current_phase=participation.current_phase,
                    phase_status=participation.phase_status,
                    participation_created_at=participation.created_at,
                    updated_at=participation.updated_at,
                    phase_completed_at=participation.phase_completed_at,
                    diagnosis_created_at=snapshot.created_at if snapshot else None,
                    diagnosis_outcome=snapshot.diagnosis_outcome if snapshot else None,
                    knowledge_gap_codes=tuple(
                        sorted(
                            {
                                str(item["point_code"])
                                for item in gaps
                                if isinstance(item, dict) and isinstance(item.get("point_code"), str)
                            }
                        )
                    ),
                    reasoning_issue_codes=tuple(
                        sorted(
                            {
                                str(item["dimension_id"])
                                for item in issues
                                if isinstance(item, dict) and isinstance(item.get("dimension_id"), str)
                            }
                        )
                    ),
                )
            )
        return tuple(records)

    def teacher_discussions(self, teacher_id, class_ids, start, end, session_id=None):
        query = (
            select(PblSession, PblParticipation)
            .join(PblParticipation, PblParticipation.session_id == PblSession.id)
            .where(
                PblSession.session_kind == "classroom",
                PblSession.teacher_id == teacher_id,
                PblSession.class_id.in_(class_ids),
                PblParticipation.created_at >= start,
                PblParticipation.created_at < end,
            )
            .order_by(PblParticipation.created_at.desc(), PblParticipation.id.desc())
        )
        if session_id is not None:
            query = query.where(PblSession.id == session_id)
        return tuple(
            PblTeacherDiscussionRecord(
                participation.id,
                session.id,
                session.class_id,
                participation.student_id,
                participation.current_phase,
                participation.phase_status,
                participation.created_at,
                participation.phase_completed_at,
            )
            for session, participation in self._session.execute(query).all()
        )

    def teacher_diagnoses(
        self,
        teacher_id: int,
        class_ids: tuple[int, ...],
        start: datetime,
        end: datetime,
        session_id: int | None = None,
    ) -> tuple[PblTeacherDiagnosisRecord, ...]:
        # Frozen completion identities are authoritative; current membership is
        # deliberately not required for historical classroom facts.
        query = (
            select(PblSession, PblParticipation, PblDiagnosticSnapshot)
            .join(PblParticipation, PblParticipation.session_id == PblSession.id)
            .join(PblDiagnosticSnapshot, PblDiagnosticSnapshot.id == PblParticipation.completion_snapshot_id)
            .where(
                PblSession.session_kind == "classroom",
                PblSession.teacher_id == teacher_id,
                PblSession.class_id.in_(class_ids),
                PblParticipation.phase_status == "completed",
                PblDiagnosticSnapshot.participation_id == PblParticipation.id,
                PblDiagnosticSnapshot.revision == PblParticipation.evidence_completed_revision,
                PblDiagnosticSnapshot.phase_decision == "complete",
                PblDiagnosticSnapshot.status == "ready",
                PblDiagnosticSnapshot.created_at >= start,
                PblDiagnosticSnapshot.created_at < end,
            )
            .order_by(PblDiagnosticSnapshot.created_at.desc(), PblDiagnosticSnapshot.id.desc())
        )
        if session_id is not None:
            query = query.where(PblSession.id == session_id)

        def codes(value, key):
            return (
                tuple(
                    sorted(
                        {
                            item[key]
                            for item in value
                            if isinstance(item, dict) and isinstance(item.get(key), str) and item[key].strip()
                        }
                    )
                )
                if isinstance(value, list)
                else ()
            )

        def findings(value, key):
            # Only the structured finding explanation; never copy evidence text,
            # messages, provider output or references into the summary projection.
            return (
                tuple(
                    PblTeacherFinding(item[key], " ".join(item["summary"].split())[:160])
                    for item in value
                    if isinstance(item, dict)
                    and isinstance(item.get(key), str)
                    and item[key].strip()
                    and isinstance(item.get("summary"), str)
                )
                if isinstance(value, list)
                else ()
            )

        return tuple(
            PblTeacherDiagnosisRecord(
                participation.id,
                session.id,
                session.class_id,
                participation.student_id,
                snapshot.created_at,
                codes(snapshot.knowledge_gaps, "point_code"),
                codes(snapshot.reasoning_issues, "dimension_id"),
                findings(snapshot.knowledge_gaps, "point_code"),
                findings(snapshot.reasoning_issues, "dimension_id"),
            )
            for session, participation, snapshot in self._session.execute(query)
        )

    def student_dialogues_for_point(self, student_id: int, point_code: str) -> tuple[dict, ...]:
        rows = self._session.execute(
            select(PblSession.id, PblSession.goal_point_codes, PblParticipation.id, PblParticipation.current_phase)
            .join(PblParticipation, PblParticipation.session_id == PblSession.id)
            .where(PblParticipation.student_id == student_id)
            .order_by(PblParticipation.updated_at.desc(), PblParticipation.id.desc())
        ).all()
        return tuple(
            {"session_id": session_id, "participation_id": participation_id, "phase": phase}
            for session_id, goals, participation_id, phase in rows
            if point_code in goals
        )

    def append_student_message(
        self,
        participation_id: int,
        client_message_id: str,
        content: str,
        interaction_style: str = "guided",
        turn_scope: str = "evidence",
    ) -> PblParticipationRecord | None:
        if turn_scope not in {"evidence", "private_follow_up"}:
            raise AppError("STATE_CONFLICT", "消息范围无效", 409)
        self._expire_pending(participation_id)
        value = self._session.get(PblParticipation, participation_id)
        assert value is not None
        duplicate = self._session.scalar(
            select(PblMessage).where(
                PblMessage.participation_id == participation_id, PblMessage.client_message_id == client_message_id
            )
        )
        if duplicate:
            if (
                duplicate.content != content
                or duplicate.interaction_style != interaction_style
                or duplicate.turn_scope != turn_scope
            ):
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
        style_values = {"interaction_style": interaction_style}
        if value.interaction_style != interaction_style:
            style_values["style_selected_at"] = datetime.now(UTC)
        changed = self._session.execute(
            update(PblParticipation)
            .where(PblParticipation.id == participation_id, PblParticipation.revision == revision)
            .values(revision=revision + 1, **style_values)
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
                interaction_style=interaction_style,
                turn_scope=turn_scope,
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
        pending = self._session.scalar(
            select(PblMessage).where(
                PblMessage.participation_id == participation_id,
                PblMessage.request_revision == revision,
                PblMessage.processing_status == "pending",
                PblMessage.turn_scope == "evidence",
            )
        )
        if pending is None:
            return None
        if pending.interaction_style != result.interaction_style:
            raise AppError("STATE_CONFLICT", "回应方式与本轮请求不一致", 409)
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
        assessment = result.phase_assessment or {}
        assessed_phase = str(assessment.get("phase") or part.current_phase)
        phase_decision = str(assessment.get("decision") or "unavailable")
        snapshot = PblDiagnosticSnapshot(
            participation_id=part.id,
            revision=revision,
            status=result.diagnostic_status,
            interaction_style=pending.interaction_style,
            assistant_reply=result.assistant_reply[:4000],
            follow_up_question=result.follow_up_question,
            knowledge_gaps=gaps,
            reasoning_issues=issues,
            diagnosis_outcome=result.diagnosis_outcome,
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
        if phase_decision == "complete":
            if part.completion_snapshot_id is not None or part.evidence_completed_revision is not None:
                raise AppError("STATE_CONFLICT", "完成证据边界已经存在", 409)
            part.completion_snapshot_id = snapshot.id
            part.evidence_completed_revision = revision
        self._session.execute(
            update(PblMessage)
            .where(PblMessage.participation_id == participation_id, PblMessage.request_revision == revision)
            .values(result_snapshot_id=snapshot.id)
        )
        next_sequence = (
            self._session.scalar(select(func.max(PblMessage.sequence)).where(PblMessage.participation_id == part.id))
            or 0
        ) + 1
        assistant = PblMessage(
            participation_id=part.id,
            sequence=next_sequence,
            role="assistant",
            interaction_style=pending.interaction_style,
            turn_scope="evidence",
            reply_to_message_id=pending.id,
            processing_status="completed",
            content=result.assistant_reply[:4000],
        )
        self._session.add(assistant)
        self._session.flush()
        return self._snapshot_record(snapshot)

    def save_private_follow_up_result(
        self, participation_id: int, revision: int, result: PrivateFollowupResult
    ) -> PblPrivateFollowUpResultRecord | None:
        part = self._session.get(PblParticipation, participation_id)
        if part is None or self.completion_snapshot(participation_id) is None:
            raise AppError("STATE_CONFLICT", "完成证据边界不完整", 409)
        pending = self._session.scalar(
            select(PblMessage).where(
                PblMessage.participation_id == participation_id,
                PblMessage.request_revision == revision,
                PblMessage.processing_status == "pending",
                PblMessage.turn_scope == "private_follow_up",
            )
        )
        if pending is None:
            return None
        if pending.interaction_style != result.interaction_style:
            raise AppError("STATE_CONFLICT", "回应方式与本轮请求不一致", 409)
        if result.processing_status not in {"completed", "unavailable"}:
            raise AppError("STATE_CONFLICT", "私人问答处理状态无效", 409)
        changed = self._session.execute(
            update(PblMessage)
            .where(
                PblMessage.id == pending.id,
                PblMessage.processing_status == "pending",
                exists().where(PblParticipation.id == participation_id, PblParticipation.revision == revision),
            )
            .values(processing_status=result.processing_status)
        )
        if changed.rowcount != 1:
            return None
        next_sequence = (
            self._session.scalar(select(func.max(PblMessage.sequence)).where(PblMessage.participation_id == part.id))
            or 0
        ) + 1
        assistant = PblMessage(
            participation_id=part.id,
            sequence=next_sequence,
            role="assistant",
            content=result.assistant_reply[:4000],
            interaction_style=pending.interaction_style,
            turn_scope="private_follow_up",
            reply_to_message_id=pending.id,
            processing_status=result.processing_status,
        )
        self._session.add(assistant)
        self._session.flush()
        metadata = result.provider_metadata or {}
        value = PblPrivateFollowUpResult(
            participation_id=part.id,
            student_message_id=pending.id,
            assistant_message_id=assistant.id,
            interaction_style=pending.interaction_style,
            schema_version=result.schema_version,
            processing_status=result.processing_status,
            safety_status=result.safety_status,
            safety_notice=(result.safety_notice or "")[:500] or None,
            provider_name=str(metadata.get("provider") or "unknown")[:40],
            provider_mode=(str(metadata.get("mode"))[:40] if metadata.get("mode") else None),
            fallback_used=result.fallback_used,
            failure_category=(result.failure_reason or "")[:100] or None,
        )
        self._session.add(value)
        self._session.flush()
        return self._private_record(value)

    def participation(self, participation_id: int) -> PblParticipationRecord | None:
        value = self._session.get(PblParticipation, participation_id)
        return self._part_record(value) if value else None

    def _diagnostic_record(self, snapshot: PblDiagnosticSnapshot) -> PblDiagnosticRecord:
        part = self._session.get(PblParticipation, snapshot.participation_id)
        session = self._session.get(PblSession, part.session_id)
        return PblDiagnosticRecord(
            self._snapshot_record(snapshot),
            (),
            student_id=part.student_id,
            class_id=session.class_id,
            session_id=session.id,
            topic_code=session.topic_code,
            session_kind=session.session_kind,
            interaction_style=snapshot.interaction_style,
            goal_point_codes=tuple(session.goal_point_codes or []),
            completion_snapshot_id=part.completion_snapshot_id,
            case_id=session.case_id,
        )

    def diagnostics_for_teacher(self, teacher_id: int, limit: int, offset: int, filters: dict):
        statement = (
            select(PblDiagnosticSnapshot)
            .join(
                PblParticipation,
                PblParticipation.id == PblDiagnosticSnapshot.participation_id,
            )
            .join(PblSession, PblSession.id == PblParticipation.session_id)
            .where(
                self._teacher_snapshot_condition(teacher_id),
                PblDiagnosticSnapshot.status == "ready",
            )
        )
        for key, column in (
            ("class_id", PblSession.class_id),
            ("session_id", PblSession.id),
            ("student_id", PblParticipation.student_id),
        ):
            if filters.get(key):
                statement = statement.where(column == filters[key])
        statement = statement.where(PblSession.session_kind == "classroom")
        # A private dialogue may be submitted at an earlier snapshot and then
        # continue privately.  Keep the newest *visible* snapshot per learner,
        # rather than allowing a later private revision to hide the submission.
        visible = self._session.scalars(statement.order_by(PblDiagnosticSnapshot.id.desc())).all()
        latest = []
        participations = set()
        for snapshot in visible:
            if snapshot.participation_id in participations:
                continue
            participations.add(snapshot.participation_id)
            latest.append(snapshot)
        return tuple(self._diagnostic_record(snapshot) for snapshot in latest[offset : offset + limit]), len(latest)

    def diagnostic_for_teacher(self, teacher_id: int, snapshot_id: int) -> PblDiagnosticRecord | None:
        snapshot = self._session.scalar(
            select(PblDiagnosticSnapshot)
            .join(
                PblParticipation,
                PblParticipation.id == PblDiagnosticSnapshot.participation_id,
            )
            .join(PblSession, PblSession.id == PblParticipation.session_id)
            .where(
                PblDiagnosticSnapshot.id == snapshot_id,
                self._teacher_snapshot_condition(teacher_id),
                PblDiagnosticSnapshot.status == "ready",
            )
        )
        return self._diagnostic_record(snapshot) if snapshot else None

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
        if message is None:
            return None
        if message.turn_scope == "evidence":
            snapshot = (
                self._session.get(PblDiagnosticSnapshot, message.result_snapshot_id)
                if message.result_snapshot_id
                else None
            )
            if snapshot:
                return PblMessageResultRecord(turn_scope="evidence", snapshot=self._snapshot_record(snapshot))
        elif message.turn_scope == "private_follow_up":
            private = self._session.scalar(
                select(PblPrivateFollowUpResult).where(PblPrivateFollowUpResult.student_message_id == message.id)
            )
            if private:
                return PblMessageResultRecord(
                    turn_scope="private_follow_up", private_follow_up=self._private_record(private)
                )
        else:
            raise AppError("STATE_CONFLICT", "消息范围损坏", 409)
        if message.processing_status != "pending":
            raise AppError("STATE_CONFLICT", "消息结果关联损坏", 409)
        return None

    def _expire_pending(self, participation_id: int):
        stale = self._session.scalar(
            select(PblMessage).where(
                PblMessage.participation_id == participation_id,
                PblMessage.processing_status == "pending",
                PblMessage.created_at < datetime.now(UTC) - timedelta(seconds=60),
            )
        )
        if stale:
            if stale.turn_scope == "private_follow_up":
                self.save_private_follow_up_result(
                    participation_id,
                    stale.request_revision,
                    unavailable_private_follow_up("interrupted_request", stale.interaction_style),
                )
            else:
                self.save_result(
                    participation_id,
                    stale.request_revision,
                    unavailable_result("interrupted_request", stale.interaction_style),
                )

    def revisions_for_teacher(self, teacher_id: int, snapshot_id: int):
        diagnostic = self.diagnostic_for_teacher(teacher_id, snapshot_id)
        if not diagnostic:
            return ()
        rows = self._session.scalars(
            select(PblDiagnosticSnapshot)
            .where(
                PblDiagnosticSnapshot.participation_id == diagnostic.snapshot.participation_id,
                self._teacher_snapshot_condition(teacher_id),
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
            PblDiagnosticSnapshot.schema_version == 8,
        )
        phase_rows = self._session.execute(
            select(PblParticipation.current_phase, func.count(PblParticipation.id))
            .where(PblParticipation.session_id == session_id)
            .group_by(PblParticipation.current_phase)
        ).all()
        return {
            "participants": self._session.scalar(select(func.count()).select_from(parts.subquery())) or 0,
            "diagnoses": self._session.scalar(select(func.count()).select_from(snapshots.subquery())) or 0,
            "phase_counts": {str(phase): int(count) for phase, count in phase_rows},
        }

    def _teacher_snapshot_condition(self, teacher_id: int):
        if self._scope is None:
            return PblDiagnosticSnapshot.id.in_([])
        allowed = (
            select(PblDiagnosticSnapshot.id)
            .join(PblParticipation, PblParticipation.id == PblDiagnosticSnapshot.participation_id)
            .join(PblSession, PblSession.id == PblParticipation.session_id)
            .join(ClassRoom, ClassRoom.id == PblSession.class_id)
            .where(
                PblSession.teacher_id == teacher_id,
                ClassRoom.teacher_id == teacher_id,
                PblSession.session_kind == "classroom",
            )
        )
        return PblDiagnosticSnapshot.id.in_(allowed)

    def list_sessions_owned_by_teacher(self, teacher_id: int) -> tuple[PblSessionRecord, ...]:
        rows = self._session.scalars(
            select(PblSession).where(PblSession.teacher_id == teacher_id).order_by(PblSession.created_at.desc())
        ).all()
        return tuple(
            self._session_record(row)
            for row in rows
            if row.class_id and self._scope and self._scope.owned_active(teacher_id, row.class_id)
        )

    def session_dashboard_rows(self, session_id: int) -> tuple[dict, ...]:
        rows = self._session.execute(
            select(PblParticipation, PblDiagnosticSnapshot)
            .outerjoin(
                PblDiagnosticSnapshot,
                and_(
                    PblDiagnosticSnapshot.participation_id == PblParticipation.id,
                    or_(
                        PblParticipation.phase_status != "completed",
                        PblDiagnosticSnapshot.id == PblParticipation.completion_snapshot_id,
                    ),
                ),
            )
            .where(PblParticipation.session_id == session_id)
            .order_by(PblParticipation.id, PblDiagnosticSnapshot.revision.desc())
        ).all()
        result, seen = [], set()
        for participation, snapshot in rows:
            if participation.id in seen:
                continue
            seen.add(participation.id)
            result.append(
                {
                    "student_id": participation.student_id,
                    "current_phase": participation.current_phase,
                    "phase_status": participation.phase_status,
                    "last_activity_at": (
                        snapshot.created_at
                        if participation.phase_status == "completed" and snapshot is not None
                        else participation.updated_at
                    ),
                    "snapshot_id": snapshot.id if snapshot and snapshot.status == "ready" else None,
                }
            )
        return tuple(result)
