from app.modules.pbl.application.use_cases import PblApplication
from app.modules.pbl.infrastructure.repositories import SqlAlchemyPblRepository


class StudyDialogues:
    def __init__(self, application: PblApplication, repository: SqlAlchemyPblRepository):
        self._app = application
        self._repo = repository

    def start(self, student_id: int, point_code: str, client_id: str, style: str) -> int:
        session, _ = self._app.create_student_dialogue(student_id, client_id, None, style, (point_code,))
        return session.id

    def state(self, student_id: int, session_id: int) -> dict:
        session, part, snap = self._app.dialogue(student_id, session_id)
        completed = bool(
            part
            and part.current_phase == "completed"
            and snap
            and snap.status == "ready"
            and snap.safety_status == "educational"
            and snap.schema_version in {3, 4}
        )
        return {
            "session_id": session.id,
            "phase": part.current_phase if part else "problem_framing",
            "completed": completed,
            "snapshot_id": snap.id if completed else None,
            "goals": list(session.goal_point_codes),
            "findings": list((*snap.knowledge_gaps, *snap.reasoning_issues)) if completed else [],
            "summary": snap.assistant_reply if completed else "",
            "suggestions": [
                {
                    "id": q.id,
                    "title": q.title,
                    "prompt": q.prompt,
                    "linked_findings": list(q.linked_findings),
                    "version": q.version,
                }
                for q in self._repo.suggestions_for_snapshot(snap.id)
            ]
            if completed
            else [],
        }
