from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.content.public import QuestionPublicationPort
from app.modules.pbl.application.ports import PblInferenceGateway
from app.modules.pbl.application.records import InferenceRequest, InferenceResult
from app.modules.pbl.domain.catalog import PATHOLOGY_POINTS
from app.modules.pbl.infrastructure.models import (
    PblDiagnosticSnapshot,
    PblParticipation,
    PblQuestionSuggestion,
    PblSession,
)
from app.shared.errors import AppError


class PblApplication:
    def __init__(self, session: Session, gateway: PblInferenceGateway, provider: str, mode: str | None) -> None:
        self._db, self._gateway, self._provider, self._mode = session, gateway, provider, mode

    def create_session(self, teacher_id: int, class_id: int, topic_code: str) -> PblSession:
        room = self._db.get(ClassRoom, class_id)
        if room is None or room.teacher_id != teacher_id:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        if topic_code not in PATHOLOGY_POINTS:
            raise AppError("VALIDATION_ERROR", "病理学主题无效", 422)
        item = PblSession(
            class_id=class_id,
            teacher_id=teacher_id,
            topic_code=topic_code,
            provider=self._provider,
            invocation_mode=self._mode,
        )
        self._db.add(item)
        self._db.commit()
        self._db.refresh(item)
        return item

    def close_session(self, teacher_id: int, class_id: int, session_id: int) -> PblSession:
        item = self._owned(teacher_id, class_id, session_id)
        if item.status != "closed":
            item.status, item.closed_at = "closed", datetime.now(UTC)
            self._db.commit()
        return item

    def active_for_student(self, student_id: int) -> tuple[PblSession, ...]:
        return tuple(
            self._db.scalars(
                select(PblSession)
                .join(ClassMember, ClassMember.class_id == PblSession.class_id)
                .where(ClassMember.student_id == student_id, PblSession.status == "active")
            ).all()
        )

    def participation(self, student_id: int, session_id: int) -> tuple[PblParticipation, PblDiagnosticSnapshot | None]:
        self._require_student_session(student_id, session_id)
        part = self._db.scalar(
            select(PblParticipation).where(
                PblParticipation.session_id == session_id, PblParticipation.student_id == student_id
            )
        )
        if part is None:
            part = PblParticipation(
                session_id=session_id, student_id=student_id, coze_user_ref=f"pbl-{session_id}-{student_id}"
            )
            self._db.add(part)
            self._db.commit()
            self._db.refresh(part)
        latest = self._db.scalar(
            select(PblDiagnosticSnapshot)
            .where(PblDiagnosticSnapshot.participation_id == part.id)
            .order_by(PblDiagnosticSnapshot.revision.desc())
        )
        return part, latest

    def message(
        self, student_id: int, session_id: int, client_message_id: str, content: str
    ) -> tuple[PblParticipation, PblDiagnosticSnapshot]:
        if not content.strip() or len(content) > 2000:
            raise AppError("VALIDATION_ERROR", "消息长度无效", 422)
        part, existing = self.participation(student_id, session_id)
        if any(m.get("client_message_id") == client_message_id for m in part.messages):
            if existing is None:
                raise AppError("STATE_CONFLICT", "消息正在处理", 409)
            return part, existing
        history = list(part.messages)[-20:]
        part.messages = [
            *part.messages,
            {"role": "student", "content": content.strip(), "client_message_id": client_message_id},
        ]
        part.revision += 1
        revision = part.revision
        self._db.commit()
        session = self._db.get(PblSession, session_id)
        result = self._gateway.infer(InferenceRequest(session_id, session.topic_code, content.strip(), tuple(history)))
        part = self._db.get(PblParticipation, part.id)
        if part is None or part.revision != revision:
            raise AppError("STATE_CONFLICT", "对话已更新，请重试", 409)
        snapshot = self._save_result(part, revision, result)
        self._db.commit()
        return part, snapshot

    def diagnostics(self, teacher_id: int) -> tuple[PblDiagnosticSnapshot, ...]:
        return tuple(
            self._db.scalars(
                select(PblDiagnosticSnapshot)
                .join(PblParticipation)
                .join(PblSession)
                .where(PblSession.teacher_id == teacher_id, PblDiagnosticSnapshot.status == "ready")
                .order_by(PblDiagnosticSnapshot.id.desc())
            ).all()
        )

    def edit_suggestion(
        self, teacher_id: int, suggestion_id: int, version: int, title: str, prompt: str, reject: bool
    ) -> PblQuestionSuggestion:
        item = self._suggestion_for_teacher(teacher_id, suggestion_id)
        if item.version != version:
            raise AppError("STATE_CONFLICT", "建议已被更新", 409)
        if item.status in {"published", "superseded"}:
            raise AppError("STATE_CONFLICT", "建议不可编辑", 409)
        item.status = "rejected" if reject else "edited"
        item.title = title.strip() or item.title
        item.prompt = prompt.strip() or item.prompt
        item.version += 1
        self._db.commit()
        return item

    def adopt(self, teacher_id: int, suggestion_id: int) -> PblQuestionSuggestion:
        item = self._suggestion_for_teacher(teacher_id, suggestion_id)
        if item.status == "rejected":
            raise AppError("STATE_CONFLICT", "建议已拒绝", 409)
        if item.problem_id is None:
            session = self._db.scalar(
                select(PblSession)
                .join(PblParticipation, PblParticipation.session_id == PblSession.id)
                .join(PblDiagnosticSnapshot, PblDiagnosticSnapshot.participation_id == PblParticipation.id)
                .where(PblDiagnosticSnapshot.id == item.snapshot_id)
            )
            room = self._db.get(ClassRoom, session.class_id)
            item.problem_id = QuestionPublicationPort(self._db).adopt_open_question(
                teacher_id=teacher_id, source_id=item.id, title=item.title, prompt=item.prompt, class_code=room.code
            )
            item.status = "published"
            item.version += 1
            self._db.commit()
        return item

    def _save_result(self, part: PblParticipation, revision: int, result: InferenceResult) -> PblDiagnosticSnapshot:
        gaps, issues, recs = (
            list(result.knowledge_gaps),
            list(result.reasoning_issues),
            list(result.recommended_questions),
        )
        if result.diagnostic_status == "ready" and not (gaps or issues):
            result = InferenceResult("请补充你的判断依据。", "insufficient_evidence")
            recs = []
        if result.diagnostic_status != "ready":
            recs = []
        snap = PblDiagnosticSnapshot(
            participation_id=part.id,
            revision=revision,
            status=result.diagnostic_status,
            assistant_reply=result.assistant_reply[:4000],
            follow_up_question=result.follow_up_question,
            knowledge_gaps=gaps[:10],
            reasoning_issues=issues[:10],
            provider_metadata=result.provider_metadata or {},
            failure_reason=result.failure_reason,
        )
        self._db.add(snap)
        self._db.flush()
        for old in self._db.scalars(
            select(PblQuestionSuggestion)
            .join(PblDiagnosticSnapshot)
            .where(PblDiagnosticSnapshot.participation_id == part.id, PblQuestionSuggestion.status == "proposed")
        ).all():
            old.status = "superseded"
        for q in recs[:5]:
            links = [str(x) for x in q.get("linked_findings", [])][:5]
            if links:
                self._db.add(
                    PblQuestionSuggestion(
                        snapshot_id=snap.id,
                        title=str(q.get("title", "PBL 讨论题"))[:200],
                        prompt=str(q.get("prompt", ""))[:2000],
                        linked_findings=links,
                    )
                )
        return snap

    def _owned(self, teacher_id: int, class_id: int, session_id: int) -> PblSession:
        item = self._db.get(PblSession, session_id)
        if item is None or item.class_id != class_id or item.teacher_id != teacher_id:
            raise AppError("RESOURCE_NOT_FOUND", "课堂不存在", 404)
        return item

    def _require_student_session(self, student_id: int, session_id: int) -> None:
        item = self._db.get(PblSession, session_id)
        member = self._db.scalar(
            select(ClassMember).where(
                ClassMember.class_id == (item.class_id if item else -1), ClassMember.student_id == student_id
            )
        )
        if item is None or item.status != "active" or member is None:
            raise AppError("RESOURCE_NOT_FOUND", "课堂不存在", 404)

    def _suggestion_for_teacher(self, teacher_id: int, suggestion_id: int) -> PblQuestionSuggestion:
        item = self._db.get(PblQuestionSuggestion, suggestion_id)
        if item is None:
            raise AppError("RESOURCE_NOT_FOUND", "建议不存在", 404)
        owner = self._db.scalar(
            select(PblSession.teacher_id)
            .join(PblParticipation, PblParticipation.session_id == PblSession.id)
            .join(PblDiagnosticSnapshot, PblDiagnosticSnapshot.participation_id == PblParticipation.id)
            .where(PblDiagnosticSnapshot.id == item.snapshot_id)
        )
        if owner != teacher_id:
            raise AppError("RESOURCE_NOT_FOUND", "建议不存在", 404)
        return item
