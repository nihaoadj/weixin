from sqlalchemy import text

from tests.test_pbl_api import _headers, _login


def test_retired_classroom_package_routes_are_empty_or_fail_closed(client, db) -> None:
    for table in (
        "classroom_final_reports",
        "classroom_package_items",
        "classroom_task_packages",
        "teaching_command_receipts",
    ):
        db.execute(text(f"DROP TABLE IF EXISTS {table}"))
    db.commit()

    student = _headers(_login(client, "student", "t43-retired-package-student"))
    teacher = _headers(_login(client, "teacher", "t43-retired-package-teacher"))

    packages = client.get("/student/classroom-task-packages", headers=student)
    assert packages.status_code == 200, packages.text
    assert packages.json()["items"] == []
    assert packages.json()["total"] == 0

    reports = client.get("/teacher/classroom-final-reports?class_id=999999", headers=teacher)
    assert reports.status_code == 200, reports.text
    assert reports.json()["items"] == []
    assert reports.json()["total"] == 0

    assert client.get("/student/classroom-task-packages/999999", headers=student).status_code == 404
    assert client.get("/student/classroom-final-reports/999999", headers=student).status_code == 404
    assert client.get("/teacher/classroom-final-reports/999999", headers=teacher).status_code == 404

    for path, payload in (
        ("/student/classroom-tasks/999999/start", None),
        (
            "/student/classroom-tasks/999999/submit",
            {"client_submission_id": "retired-submit", "answer": {"selected_option": 0}},
        ),
    ):
        response = client.post(path, headers=student, json=payload)
        assert response.status_code == 409, response.text
        assert response.json()["detail"]["reason"] == "RETIRED_FLOW"
