"""Actual simultaneous HTTP submission preserves one result and evidence event."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import func, select

from app.modules.content.infrastructure.models import KnowledgeCatalog
from app.modules.learning.infrastructure.evidence_models import LearningEvidenceEvent
from app.modules.learning.infrastructure.route_models import RouteLearningResult
from tests.test_pbl_api import _headers, _login
from tests.test_t44_learning_routes import completed_route, configure, learn_route


def test_concurrent_submission_has_one_result_and_retry_reads_same_result(client, db, monkeypatch):
    configure(monkeypatch)
    student = _login(client, "student", "t44-concurrent-submit")
    route_id, detail = completed_route(client, student)
    learn_route(client, student, route_id, detail)
    test_id = detail["test_summary"]["id"]
    started = client.post(
        f"/learning/final-tests/{test_id}/start",
        headers=_headers(student),
        json={"client_request_id": "concurrent-start"},
    )
    assert started.status_code == 200, started.text
    test = started.json()
    payload = {
        "client_submission_id": "same-concurrent-submission",
        "expected_version": test["attempt"]["version"],
        "released_digest": test["released_digest"],
        "answers": {question["id"]: 0 for question in test["questions"]},
    }
    # Grading and ledger validation use the frozen goals even when the live
    # catalog becomes unavailable after the test was released.
    catalog = db.scalar(select(KnowledgeCatalog).where(KnowledgeCatalog.status == "active"))
    catalog.status = "archived"
    db.commit()
    path = f"/learning/final-tests/{test_id}/submit"
    barrier = Barrier(2)

    def submit():
        barrier.wait(timeout=10)
        return client.post(path, headers=_headers(student), json=payload)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(submit) for _ in range(2)]
        responses = [future.result(timeout=20) for future in futures]
    assert any(response.status_code == 200 for response in responses)
    assert all(response.status_code in {200, 409} for response in responses), [response.text for response in responses]
    replay = client.post(path, headers=_headers(student), json=payload)
    assert replay.status_code == 200, replay.text
    for response in responses:
        if response.status_code == 200:
            assert response.json() == replay.json()
    db.expire_all()
    assert db.scalar(select(func.count(RouteLearningResult.id))) == 1
    assert (
        db.scalar(
            select(func.count(LearningEvidenceEvent.id)).where(
                LearningEvidenceEvent.source_type == "private_final_test"
            )
        )
        == 1
    )
