"""Explicit opt-in synthetic live test. Never run from pytest, CI, or contract export."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-calls", type=int, default=6, choices=range(1, 13))
    args = parser.parse_args()
    from app.testing_resources import assert_owned_resource, cleanup_managed_database, create_managed_database

    resource = create_managed_database("t11-live-deepseek")
    assert_owned_resource(resource)
    # Dev dotenv supplies only the approved backend provider; all persistence is temporary.
    os.environ.update(
        APP_ENV="development",
        DATABASE_URL=resource.url,
        ENABLE_DEMO_AUTH="true",
        SEED_SHOWCASE_CASE="false",
        PBL_MOCK_ENABLED="false",
        AI_ENABLED="false",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    from app.core.config import get_settings

    settings = get_settings()
    if settings.pbl_openai_model != "deepseek-v4-flash" or settings.pbl_openai_base_url != "https://api.deepseek.com":
        raise RuntimeError("Approved development model configuration is missing")
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.bootstrap.seed import seed_showcase_case
    from app.db import SessionLocal, engine, init_db
    from app.main import app
    from app.modules.content.infrastructure.models import Problem
    from app.modules.pbl import wiring
    from app.modules.pbl.infrastructure.models import PblDiagnosticSnapshot

    calls = 0
    original_gateway = wiring._gateway

    class LimitedGateway:
        def __init__(self, gateway):
            self.gateway = gateway

        def infer(self, request):
            nonlocal calls
            if calls >= args.max_calls:
                raise RuntimeError("Live call limit reached")
            calls += 1
            return self.gateway.infer(request)

    def gateway():
        provider, name, mode = original_gateway()
        return LimitedGateway(provider), name, mode

    wiring._gateway = gateway
    result = {"model": "deepseek-v4-flash", "provider": "openai_compatible", "calls": [], "published": False}
    try:
        init_db()
        with SessionLocal() as db:
            seed_showcase_case(db)
            case_id = db.scalar(select(Problem.id).where(Problem.slug == "pathology.inflammation-showcase"))
        with TestClient(app) as client:

            def login(role, identifier):
                response = client.post(
                    "/auth/demo-login",
                    json={"role": role, "external_id": identifier, "nickname": "合成教学测试", "avatar_url": ""},
                )
                if response.status_code != 200:
                    raise RuntimeError("Synthetic login failed")
                return {"Authorization": "Bearer " + response.json()["access_token"]}

            teacher, student = login("teacher", "demo_teacher"), login("student", "demo_student")
            classroom = client.get("/classes", headers=teacher).json()[0]
            created = client.post(
                f"/classes/{classroom['id']}/pbl-sessions",
                headers=teacher,
                json={
                    "topic_code": "pathology.inflammation",
                    "case_id": case_id,
                    "goal_point_codes": ["pathology.inflammation.vascular"],
                },
            )
            if created.status_code != 201:
                raise RuntimeError("Synthetic classroom creation failed")
            session_id = created.json()["id"]
            answers = [
                "在合成皮肤损伤的 PBL 病例里，局部红肿是怎样形成的？我不理解血管反应。",
                "我认为红和肿都是因为血管通透性增加，红色可能只是液体漏到组织里。我不知道血流增加的作用。",
                "我的依据只有局部红和肿，没有比较血管扩张与蛋白性渗出。我会直接从红肿判断一定存在细菌。",
                "目前仍不能区分血流改变与通透性改变，也没有找到支持细菌感染的直接证据。请依据已有回答评估学习困难。",
            ]
            for index in range(min(args.max_calls, len(answers))):
                response = client.post(
                    f"/student/pbl-sessions/{session_id}/messages",
                    headers=student,
                    json={"client_message_id": f"live-{index}", "content": answers[index]},
                )
                if response.status_code != 200:
                    result["calls"].append({"http_status": response.status_code})
                    break
                diagnostic = response.json()["diagnostic"]
                with SessionLocal() as db:
                    snapshot = db.get(PblDiagnosticSnapshot, diagnostic["id"])
                    failure = snapshot.failure_reason
                    validation_issues = snapshot.provider_metadata.get("validation_issues", [])
                result["calls"].append(
                    {
                        "http_status": 200,
                        "status": diagnostic["diagnostic_status"],
                        "knowledge_gap_count": len(diagnostic["knowledge_gaps"]),
                        "reasoning_issue_count": len(diagnostic["reasoning_issues"]),
                        "failure_reason": failure, "validation_issues": validation_issues,
                    }
                )
                print(json.dumps({"live_call": calls, **result["calls"][-1]}, ensure_ascii=True), flush=True)
                if diagnostic["diagnostic_status"] == "unavailable":
                    break
                if diagnostic["diagnostic_status"] == "ready":
                    queue = client.get("/teacher/pbl-diagnostics", headers=teacher).json()["items"]
                    if queue and queue[0]["recommended_questions"]:
                        suggestion = queue[0]["recommended_questions"][0]
                        payload = {key: suggestion[key] for key in ("version", "title", "prompt")}
                        path = f"/teacher/pbl-question-suggestions/{suggestion['id']}/adopt-and-publish"
                        adopted = client.post(path, headers=teacher, json=payload)
                        repeated = client.post(path, headers=teacher, json=payload)
                        result["published"] = (
                            adopted.status_code == repeated.status_code == 200 and adopted.json() == repeated.json()
                        )
                        result["student_plan_count"] = len(
                            client.get("/student/pbl-learning-plans", headers=student).json()
                        )
                    break
        print(
            json.dumps(
                {"result": result, "total_external_calls": calls, "database": "owned temporary resource"},
                ensure_ascii=True,
            )
        )
        if not result["published"]:
            raise SystemExit(2)
    finally:
        wiring._gateway = original_gateway
        engine.dispose()
        cleanup_managed_database(resource)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Never emit exception text, credentials, provider bodies or synthetic answers.
        print(json.dumps({"error_type": type(error).__name__, "details": "not logged"}))
        raise SystemExit(1) from None
