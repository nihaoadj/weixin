from app.modules.content.public import study_material_view
from app.modules.learning.application.study_ports import PracticeGenerator, StudyRepository
from app.modules.pbl.public import StudyDialoguePort
from app.shared.errors import AppError, PersistenceConflict


class StudyApplication:
    def __init__(self, repository: StudyRepository, dialogues: StudyDialoguePort, generator: PracticeGenerator, uow):
        self._repository = repository
        self._dialogues = dialogues
        self._generator = generator
        self._uow = uow

    def read(self, student_id: int, point_code: str) -> dict:
        material = study_material_view(point_code)
        if material is None:
            raise AppError("RESOURCE_NOT_FOUND", "知识点不存在", 404)
        paths = self._repository.paths(student_id, point_code)
        path = paths[0] if paths else None
        state = self._dialogues.state(student_id, path["session_id"]) if path else None
        legacy = self._repository.legacy_access(student_id, point_code)
        unlocked = bool(legacy or (state and state["completed"]))
        groups = self._repository.groups(student_id, path["id"]) if path else []
        attempts = sum(len(self._repository.attempts(student_id, item["id"])) for item in groups)
        return self._view(material, path, state, legacy, unlocked, attempts, paths)

    def start(self, student_id: int, point_code: str, client_id: str, style: str, new_round: bool) -> dict:
        material = study_material_view(point_code)
        if material is None or not client_id.strip():
            raise AppError("VALIDATION_ERROR", "知识点或学习标识无效", 422)
        paths = self._repository.paths(student_id, point_code)
        if paths and not new_round:
            path = paths[0]
        else:
            session_id = self._dialogues.start(student_id, point_code, client_id.strip(), style)
            try:
                path = self._repository.save_path(
                    student_id, point_code, session_id, client_id.strip(), material["version"]
                )
                self._uow.commit()
            except PersistenceConflict:
                self._uow.rollback()
                paths = self._repository.paths(student_id, point_code)
                if not paths:
                    raise AppError("STATE_CONFLICT", "学习路径创建冲突", 409) from None
                path = paths[0]
        state = self._dialogues.state(student_id, path["session_id"])
        legacy = self._repository.legacy_access(student_id, point_code)
        groups = self._repository.groups(student_id, path["id"])
        attempts = sum(len(self._repository.attempts(student_id, item["id"])) for item in groups)
        return self._view(material, path, state, legacy, bool(legacy or state["completed"]), attempts, paths)

    def practices(self, student_id: int, path_id: int | None = None) -> list[dict]:
        return [
            self._group_view(student_id, item, answers=True) for item in self._repository.groups(student_id, path_id)
        ]

    def practice(self, student_id: int, group_id: int, *, answers: bool) -> dict:
        group = self._repository.group(student_id, group_id)
        if group is None:
            raise AppError("RESOURCE_NOT_FOUND", "自主练习不存在", 404)
        return self._group_view(student_id, group, answers=answers)

    def generate(self, student_id: int, path_id: int, cycle: int, client_id: str) -> dict:
        if cycle not in {1, 2} or not client_id.strip():
            raise AppError("VALIDATION_ERROR", "练习轮次或标识无效", 422)
        path = self._repository.path(student_id, path_id)
        if path is None:
            raise AppError("RESOURCE_NOT_FOUND", "学习路径不存在", 404)
        state = self._dialogues.state(student_id, path["session_id"])
        if not state["completed"]:
            raise AppError("STATE_CONFLICT", "完成四阶段研讨后可开始自主练习", 409)
        existing = self._repository.groups(student_id, path_id)
        if cycle == 2:
            first = next((item for item in existing if item["cycle"] == 1), None)
            if first is None or first["status"] != "ready":
                raise AppError("STATE_CONFLICT", "请先完成第一轮练习", 409)
            attempts = self._repository.attempts(student_id, first["id"])
            if len(attempts) < len(first["questions"]) or not any(not item["correct"] for item in attempts):
                raise AppError("STATE_CONFLICT", "仅错题可开启一次变式再测", 409)
        try:
            group = self._repository.claim_group(path, cycle, client_id.strip(), state["snapshot_id"])
            self._uow.commit()
        except PersistenceConflict:
            self._uow.rollback()
            raise AppError("STATE_CONFLICT", "练习创建冲突，请重新加载", 409) from None
        if group["status"] == "ready":
            return self._group_view(student_id, group, answers=False)
        try:
            material = study_material_view(path["point_code"])
            questions = self._generator.generate(
                {
                    "point_code": path["point_code"],
                    "cycle": cycle,
                    "material": material,
                    "findings": state["findings"],
                    "suggestions": state["suggestions"],
                }
            )
            self._repository.finish_group(group["id"], group["claim"], questions, None)
            self._uow.commit()
        except Exception:
            self._uow.rollback()
            # A failure is recorded only after the provider transaction has been rolled back.
            self._repository.finish_group(group["id"], group["claim"], [], "practice_generation_unavailable")
            self._uow.commit()
            raise AppError("SERVICE_ERROR", "未审核练习生成失败，请稍后重试", 503) from None
        return self.practice(student_id, group["id"], answers=False)

    def answer(self, student_id: int, group_id: int, question_index: int, selected_option: int, client_id: str) -> dict:
        group = self._repository.group(student_id, group_id)
        if group is None or group["status"] != "ready":
            raise AppError("RESOURCE_NOT_FOUND", "自主练习不存在", 404)
        questions = group["questions"]
        if not 0 <= question_index < len(questions) or not 0 <= selected_option < len(
            questions[question_index]["options"]
        ):
            raise AppError("VALIDATION_ERROR", "题目或选项无效", 422)
        correct = selected_option == questions[question_index]["reference_option"]
        try:
            attempt = self._repository.save_attempt(
                student_id, group_id, question_index, client_id.strip(), selected_option, correct
            )
            self._uow.commit()
        except PersistenceConflict:
            self._uow.rollback()
            raise AppError("STATE_CONFLICT", "作答保存冲突", 409) from None
        return {
            "id": attempt["id"],
            "question_index": question_index,
            "selected_option": selected_option,
            "correct": correct,
            "explanation": questions[question_index]["explanation"],
            "reference_option": questions[question_index]["reference_option"],
            "due_at": attempt["due_at"],
            "created_at": attempt["created_at"],
        }

    def _view(self, material, path, state, legacy, unlocked, attempts, history):
        return {
            "material": material,
            "path": self._path_view(path),
            "phase": state["phase"] if state else "not_started",
            "practice_unlocked": unlocked,
            "review_unlocked": bool(unlocked and attempts),
            "legacy_access": legacy,
            "summary": state["summary"] if state and unlocked else "",
            "lock_reason": "请先完成本知识点的四阶段研讨。" if not unlocked else "",
            "history": [self._path_view(item) for item in history],
        }

    @staticmethod
    def _path_view(path):
        return {key: path[key] for key in ("id", "point_code", "session_id", "material_version")} if path else None

    def _group_view(self, student_id, group, *, answers):
        attempts = self._repository.attempts(student_id, group["id"])
        questions = [
            {"index": index, "point_code": item["point_code"], "prompt": item["prompt"], "options": item["options"]}
            for index, item in enumerate(group["questions"])
        ]
        result = {
            "id": group["id"],
            "path_id": group["path_id"],
            "cycle": group["cycle"],
            "status": group["status"],
            "failure": group["failure"],
            "questions": questions,
            "attempts": [],
            "due_indexes": [item["question_index"] for item in attempts if item["due_at"]],
            "can_retest": False,
            "exhausted": False,
        }
        if answers:
            result["attempts"] = [
                {
                    "id": item["id"],
                    "question_index": item["question_index"],
                    "selected_option": item["selected_option"],
                    "correct": item["correct"],
                    "due_at": item["due_at"],
                    "created_at": item["created_at"],
                }
                for item in attempts
            ]
        if group["cycle"] == 1 and group["status"] == "ready" and len(attempts) >= len(questions):
            result["can_retest"] = any(not item["correct"] for item in attempts)
        if group["cycle"] == 2 and group["status"] == "ready" and len(attempts) >= len(questions):
            result["exhausted"] = any(not item["correct"] for item in attempts)
        return result
