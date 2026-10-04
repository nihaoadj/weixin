"""Knowledge material reads and autonomous discussion creation, without study paths."""

from app.modules.content.public import KnowledgeCatalogPort
from app.modules.pbl.public import StudyDialoguePort
from app.shared.errors import AppError


class StudyApplication:
    def __init__(self, dialogues: StudyDialoguePort, knowledge_catalog: KnowledgeCatalogPort):
        self.dialogues = dialogues
        self.catalog = knowledge_catalog

    def read(self, student_id: int, point_code: str) -> dict:
        material = self.catalog.study_material_view(point_code)
        if material is None:
            raise AppError("RESOURCE_NOT_FOUND", "知识点不存在", 404)
        return {"material": material, "sessions": self.dialogues.list_for_point(student_id, point_code)}

    def start(self, student_id: int, point_code: str, client_id: str, style: str) -> dict:
        if self.catalog.study_material_view(point_code) is None or not client_id.strip():
            raise AppError("VALIDATION_ERROR", "知识点或学习标识无效", 422)
        session_id = self.dialogues.start(student_id, point_code, client_id, style)
        return next(
            item for item in self.dialogues.list_for_point(student_id, point_code) if item["session_id"] == session_id
        )
