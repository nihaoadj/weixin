"""Mixed final-test generation, grading recovery, and one result tutor conversation."""

import pytest
from sqlalchemy import func, select

from app.modules.learning.domain.learning_routes import validate_mixed_answers, validate_questions
from app.modules.learning.infrastructure.route_models import RouteFinalTest, RouteLearningResult, RouteTestAttempt
from app.shared.errors import AppError
from tests.test_pbl_api import _classroom, _headers, _login, _session_payload
from tests.test_t44_learning_routes import POINT, RouteGateway, completed_route, learn_route


class MixedGateway(RouteGateway):
    def execute_task(self, envelope):
        kind, data = envelope["task_kind"], envelope["input"]
        if kind not in {"mixed_final_test_generation", "short_answer_grading", "test_result_tutor"}:
            return super().execute_task(envelope)
        self.tasks.append(kind)
        self.last_input = data
        if self.fail == kind:
            raise TimeoutError()
        if kind == "mixed_final_test_generation":
            code = data["goal_points"][0]["code"]
            source_id = data["allowed_sources"][0]["source_id"]
            common = {"primary_point_code": code, "linked_findings": [], "source_ids": [source_id]}
            questions = [
                {
                    **common,
                    "stable_key": f"single-{index}",
                    "question_type": "single_choice",
                    "prompt": f"单选题 {index}",
                    "options": ["正确依据", "错误依据一", "错误依据二", "错误依据三"],
                    "correct_option": 0,
                    "explanation": "应结合形态与机制。",
                }
                for index in range(1, 4)
            ]
            questions.extend(
                [
                    {
                        **common,
                        "stable_key": "multiple-4",
                        "question_type": "multiple_choice",
                        "prompt": "多选题 4",
                        "options": ["形态依据", "无关推断", "机制依据", "过度结论"],
                        "correct_options": [0, 2],
                        "explanation": "形态与机制都需要核对。",
                    },
                    {
                        **common,
                        "stable_key": "short-5",
                        "question_type": "short_answer",
                        "prompt": "简答题 5",
                        "reference_answer": "说明形态变化、发生机制与证据限制。",
                        "rubric": [
                            {"criterion_id": name, "description": label, "max_points": 10}
                            for name, label in (
                                ("morphology", "描述形态变化"),
                                ("mechanism", "解释发生机制"),
                                ("limits", "说明证据限制"),
                            )
                        ],
                        "explanation": "应完整串联形态、机制和证据限制。",
                    },
                ]
            )
            result = {"version": 2, "questions": questions, "safety_status": "educational"}
        elif kind == "short_answer_grading":
            result = {
                "version": 1,
                "question_id": data["question_id"],
                "criterion_results": [
                    {"criterion_id": item["criterion_id"], "earned_points": points, "evidence": "依据学生回答核对"}
                    for item, points in zip(data["rubric"], (8, 6, 9), strict=True)
                ],
                "feedback": "形态依据较充分，机制仍可细化。",
                "safety_status": "educational",
            }
        else:
            position = next(q["position"] for q in data["question_results"] if q["id"] == data["current_question_id"])
            result = {
                "version": 1,
                "current_question_id": data["current_question_id"],
                "reply": f"正在解释第 {position} 题。",
                "updated_summary": "学生在比较形态和机制。",
                "safety_status": "educational",
            }
        return {"task_kind": kind, "schema_version": 1, "request_id": envelope["request_id"], "result": result}


def configure_mixed(monkeypatch):
    gateway = MixedGateway()
    monkeypatch.setattr("app.modules.pbl.wiring._gateway", lambda: (gateway, "local_mock", "test"))
    return gateway


def _submitted_mixed_test(client, student):
    route_id, detail = completed_route(client, student)
    detail = learn_route(client, student, route_id, detail)
    test_id = detail["test_summary"]["id"]
    started = client.post(
        f"/learning/final-tests/{test_id}/start",
        headers=_headers(student),
        json={"client_request_id": "start-mixed"},
    )
    assert started.status_code == 200, started.text
    test = started.json()
    questions = test["questions"]
    assert test["format_version"] == "mixed_v2"
    assert [item["question_type"] for item in questions] == [
        "single_choice", "single_choice", "single_choice", "multiple_choice", "short_answer"
    ]
    assert all("correct_option" not in item and "reference_answer" not in item for item in questions)
    answers = {item["id"]: 0 for item in questions[:3]}
    answers[questions[3]["id"]] = [0, 2]
    answers[questions[4]["id"]] = "描述血管扩张与渗出，联系炎症机制，并注明证据限制。"
    payload = {
        "expected_version": test["attempt"]["version"],
        "released_digest": test["released_digest"],
        "answers": answers,
        "client_submission_id": "submit-mixed",
    }
    return route_id, test_id, questions, payload


def test_mixed_test_grades_and_tutor_remembers_across_questions(client, db, monkeypatch):
    gateway = configure_mixed(monkeypatch)
    student = _login(client, "student", "t48-student")
    outsider = _login(client, "student", "t48-outsider")
    route_id, test_id, questions, payload = _submitted_mixed_test(client, student)
    test_row = db.scalar(select(RouteFinalTest).where(RouteFinalTest.public_id == test_id))
    assert test_row.format_version == "mixed_v2"
    submitted = client.post(f"/learning/final-tests/{test_id}/submit", headers=_headers(student), json=payload)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "grading"
    status = client.get(f"/learning/final-tests/{test_id}/grading", headers=_headers(student))
    assert status.json()["status"] == "completed", status.text
    result_id = status.json()["result_id"]
    result = client.get(f"/learning/routes/{route_id}/result", headers=_headers(student))
    assert result.status_code == 200, result.text
    assert result.json()["score"] == 93
    assert [item["points_awarded"] for item in result.json()["questions"]] == [15, 15, 15, 25, 23]
    assert result.json()["questions"][4]["reference_answer"]
    assert db.scalar(select(func.count(RouteLearningResult.id))) == 1
    assert client.get(f"/learning/results/{result_id}/tutor", headers=_headers(outsider)).status_code == 404

    first = client.post(
        f"/learning/results/{result_id}/tutor/messages",
        headers=_headers(student),
        json={
            "client_message_id": "about-one",
            "question_id": questions[0]["id"],
            "expected_revision": 0,
            "content": "这题为何选A？",
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["revision"] == 2
    second = client.post(
        f"/learning/results/{result_id}/tutor/messages",
        headers=_headers(student),
        json={
            "client_message_id": "about-four",
            "question_id": questions[3]["id"],
            "expected_revision": 2,
            "content": "与第1题的依据有什么联系？",
        },
    )
    assert second.status_code == 200, second.text
    assert second.json()["revision"] == 4
    assert [item["question_id"] for item in second.json()["messages"]] == [
        questions[0]["id"], questions[0]["id"], questions[3]["id"], questions[3]["id"]
    ]
    assert gateway.last_input["history"][0]["question_id"] == questions[0]["id"]
    assert client.get(f"/learning/results/{result_id}/tutor", headers=_headers(student)).json() == second.json()


def test_grading_failure_preserves_answer_and_retries_without_duplicate_result(client, db, monkeypatch):
    gateway = configure_mixed(monkeypatch)
    gateway.fail = "short_answer_grading"
    student = _login(client, "student", "t48-retry")
    route_id, test_id, _, payload = _submitted_mixed_test(client, student)
    submitted = client.post(f"/learning/final-tests/{test_id}/submit", headers=_headers(student), json=payload)
    assert submitted.status_code == 200, submitted.text
    status = client.get(f"/learning/final-tests/{test_id}/grading", headers=_headers(student)).json()
    assert status["status"] == "grading" and status["retry_allowed"]
    assert client.get(f"/learning/routes/{route_id}/result", headers=_headers(student)).status_code == 404
    attempt = db.scalar(select(RouteTestAttempt).where(RouteTestAttempt.submission_id == "submit-mixed"))
    assert attempt.status == "grading" and attempt.answers == payload["answers"] and attempt.score is None
    gateway.fail = None
    retried = client.post(
        f"/learning/final-tests/{test_id}/retry-grading",
        headers=_headers(student),
        json={"client_request_id": "retry-once"},
    )
    assert retried.status_code == 202, retried.text
    completed = client.get(f"/learning/final-tests/{test_id}/grading", headers=_headers(student))
    assert completed.json()["status"] == "completed"
    assert db.scalar(select(func.count(RouteLearningResult.id))) == 1
    replay = client.post(f"/learning/final-tests/{test_id}/submit", headers=_headers(student), json=payload)
    assert replay.status_code == 200 and replay.json()["score"] == 93


def test_classroom_uses_teacher_edited_frozen_reference_for_short_grading(client, db, monkeypatch):
    gateway = configure_mixed(monkeypatch)
    teacher = _login(client, "teacher", "t48-owner")
    student = _login(client, "student", "t48-class-member")
    class_id = _classroom(client, teacher, "t48-class-member")
    created = client.post(f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db))
    assert created.status_code == 201, created.text
    route_id, detail = completed_route(client, student, session_id=created.json()["id"])
    test_id = detail["test_summary"]["id"]
    detail = learn_route(client, student, route_id, detail)
    assert detail["test_summary"]["review_state"] == "pending_review"
    teacher_test = client.get(f"/learning/teacher/final-tests/{test_id}", headers=_headers(teacher)).json()
    assert teacher_test["format_version"] == "mixed_v2"
    questions = [
        {key: value for key, value in question.items() if key != "source_digest"}
        for question in teacher_test["questions"]
    ]
    questions[4]["reference_answer"] = "教师审核：从血管反应、渗出和证据边界解释。"
    questions[4]["rubric"][0]["description"] = "教师审核：说明血管反应"
    saved = client.put(
        f"/learning/teacher/final-tests/{test_id}",
        headers=_headers(teacher),
        json={
            "client_request_id": "teacher-mixed-save",
            "expected_version": teacher_test["version"],
            "questions": questions,
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["questions"][4]["reference_answer"] == questions[4]["reference_answer"]
    released = client.post(
        f"/learning/teacher/final-tests/{test_id}/release",
        headers=_headers(teacher),
        json={
            "client_request_id": "teacher-mixed-release",
            "expected_version": saved.json()["version"],
            "draft_digest": saved.json()["draft_digest"],
        },
    )
    assert released.status_code == 200, released.text
    started = client.post(
        f"/learning/final-tests/{test_id}/start",
        headers=_headers(student),
        json={"client_request_id": "classroom-mixed-start"},
    )
    assert started.status_code == 200, started.text
    test = started.json()
    assert all("reference_answer" not in item and "rubric" not in item for item in test["questions"])
    answers = {item["id"]: 0 for item in test["questions"][:3]}
    answers[test["questions"][3]["id"]] = [0, 2]
    answers[test["questions"][4]["id"]] = "血管扩张伴渗出，也要说明证据边界。"
    submitted = client.post(
        f"/learning/final-tests/{test_id}/submit",
        headers=_headers(student),
        json={
            "client_submission_id": "classroom-mixed-submit",
            "expected_version": test["attempt"]["version"],
            "released_digest": test["released_digest"],
            "answers": answers,
        },
    )
    assert submitted.status_code == 200, submitted.text
    assert gateway.last_input["reference_answer"] == questions[4]["reference_answer"]
    assert gateway.last_input["rubric"][0]["description"] == questions[4]["rubric"][0]["description"]
    result = client.get(f"/learning/routes/{route_id}/result", headers=_headers(student))
    assert result.status_code == 200, result.text
    assert result.json()["review_kind"] == "teacher"
    assert result.json()["questions"][4]["reference_answer"] == questions[4]["reference_answer"]


def test_mixed_answer_and_question_validation_rejects_wrong_types():
    questions = [
        {"id": "a", "question_type": "single_choice"},
        {"id": "b", "question_type": "multiple_choice"},
        {"id": "c", "question_type": "short_answer"},
    ]
    validate_mixed_answers({"a": 0, "b": [0, 2], "c": "说明机制"}, questions, complete=True)
    with pytest.raises(AppError):
        validate_mixed_answers({"a": True, "b": [0, 0], "c": "  "}, questions, complete=True)
    with pytest.raises(AppError):
        validate_questions([], [POINT], "mixed_v2")


def test_new_teacher_and_student_dialogues_reject_multiple_goals(client, db, monkeypatch):
    configure_mixed(monkeypatch)
    teacher = _login(client, "teacher", "t48-goal-owner")
    student = _login(client, "student", "t48-goal-student")
    class_id = _classroom(client, teacher, "t48-goal-student")
    teacher_payload = _session_payload(db)
    teacher_payload["goal_point_codes"] = [POINT, "pathology.inflammation.acute"]
    assert (
        client.post(f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=teacher_payload).status_code
        == 422
    )
    assert (
        client.post(
            "/student/learning-dialogues",
            headers=_headers(student),
            json={
                "client_session_id": "too-many-goals",
                "interaction_style": "guided",
                "goal_point_codes": [POINT, "pathology.inflammation.acute"],
            },
        ).status_code
        == 422
    )
