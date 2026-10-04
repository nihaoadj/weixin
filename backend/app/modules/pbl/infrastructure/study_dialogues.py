from app.modules.pbl.application.use_cases import PblApplication
from app.modules.pbl.infrastructure.repositories import SqlAlchemyPblRepository


class StudyDialogues:
    def __init__(self, application: PblApplication, repository: SqlAlchemyPblRepository, routes=None):
        self._app = application
        self._repo = repository
        self._routes = routes

    def list_for_point(self, student_id: int, point_code: str) -> list[dict]:
        result = []
        for item in self._repo.student_dialogues_for_point(student_id, point_code):
            locator = self._routes.completion_locator(item["participation_id"]) if self._routes else None
            result.append(
                {
                    "session_id": item["session_id"],
                    "point_code": point_code,
                    "phase": item["phase"],
                    "learning_route_id": locator["learning_route_id"] if locator else None,
                }
            )
        return result

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
            and snap.schema_version == 8
        )
        return {
            "session_id": session.id,
            "phase": part.current_phase if part else "problem_framing",
            "completed": completed,
            "snapshot_id": snap.id if completed else None,
            "goals": list(session.goal_point_codes),
            "findings": list((*snap.knowledge_gaps, *snap.reasoning_issues)) if completed else [],
            "summary": snap.assistant_reply if completed else "",
            "suggestions": [],
        }
