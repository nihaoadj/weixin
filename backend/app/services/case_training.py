import re
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import CaseAssessment, CaseAttempt, CaseAttemptMessage, LearningTask, Problem, StageSubmission, User
from app.schemas.case_training import CASE_STAGES, DIMENSION_SPECS, StageAnswer
from app.services.case_ai import ai_assessment, patient_reply
from app.services.case_seed import SAFETY_NOTICE


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case attempt not found")


def get_attempt(db: Session, attempt_id: int, student: User) -> CaseAttempt:
    attempt = db.scalar(
        select(CaseAttempt)
        .where(CaseAttempt.id == attempt_id, CaseAttempt.student_id == student.id)
        .options(
            selectinload(CaseAttempt.problem),
            selectinload(CaseAttempt.messages),
            selectinload(CaseAttempt.submissions),
            selectinload(CaseAttempt.assessment),
        )
    )
    if attempt is None:
        raise _not_found()
    return attempt


def create_attempt(db: Session, problem: Problem, student: User, retry_of_id: int | None = None) -> CaseAttempt:
    if retry_of_id is None:
        attempt = CaseAttempt(
            problem_id=problem.id,
            student_id=student.id,
            problem_version=problem.version,
            status="in_progress",
            current_stage="history",
        )
    else:
        original = get_attempt(db, retry_of_id, student)
        if original.status != "assessed" or original.assessment is None or original.problem.slug != problem.slug:
            raise HTTPException(status_code=409, detail="Retry requires your assessed attempt for this case")
        focus = original.assessment.focus_stage
        attempt = CaseAttempt(
            problem_id=problem.id,
            student_id=student.id,
            problem_version=problem.version,
            status="in_progress",
            current_stage=focus,
            retry_of_id=original.id,
            focus_stage=focus,
        )
        db.add(attempt)
        db.flush()
        for submission in original.submissions:
            if CASE_STAGES.index(submission.stage_id) < CASE_STAGES.index(focus):
                db.add(
                    StageSubmission(
                        attempt_id=attempt.id,
                        stage_id=submission.stage_id,
                        answer=submission.answer,
                        feedback="已从上次训练沿用",
                        inherited_from_id=submission.id,
                    )
                )
        db.commit()
        return get_attempt(db, attempt.id, student)
    db.add(attempt)
    db.commit()
    return get_attempt(db, attempt.id, student)


def add_patient_message(db: Session, attempt: CaseAttempt, content: str) -> tuple[CaseAttemptMessage, str]:
    if attempt.status != "in_progress" or attempt.current_stage != "history":
        raise HTTPException(status_code=409, detail="History conversation is locked")
    questions = sum(message.role == "user" for message in attempt.messages)
    if questions >= 30:
        raise HTTPException(status_code=409, detail="Maximum history questions reached; submit your summary")
    db.add(CaseAttemptMessage(attempt_id=attempt.id, stage_id="history", role="user", content=content.strip()))
    db.flush()
    reply, ids, response_mode = patient_reply(db, attempt, content)
    assistant_message = CaseAttemptMessage(
        attempt_id=attempt.id, stage_id="history", role="assistant", content=reply, revealed_fact_ids=ids
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    return assistant_message, response_mode


def submit_stage(db: Session, attempt: CaseAttempt, stage_id: str, answer: StageAnswer) -> StageSubmission:
    if attempt.status != "in_progress" or attempt.current_stage != stage_id:
        raise HTTPException(status_code=409, detail="Stage is not currently available")
    if answer.stage_id != stage_id:
        raise HTTPException(status_code=422, detail="Answer stage does not match path stage")
    exists = db.scalar(
        select(StageSubmission).where(StageSubmission.attempt_id == attempt.id, StageSubmission.stage_id == stage_id)
    )
    if exists:
        raise HTTPException(status_code=409, detail="Stage already submitted")
    submission = StageSubmission(
        attempt_id=attempt.id,
        stage_id=stage_id,
        answer=answer.model_dump(mode="json"),
        feedback="已保存。请继续下一阶段。",
    )
    db.add(submission)
    next_index = CASE_STAGES.index(stage_id) + 1
    if next_index == len(CASE_STAGES):
        attempt.status, attempt.current_stage, attempt.completed_at = "completed", "completed", datetime.now(UTC)
    else:
        attempt.current_stage = CASE_STAGES[next_index]
    db.commit()
    db.refresh(submission)
    return submission


def _answer_text(attempt: CaseAttempt, stage_ids: tuple[str, ...]) -> str:
    return "|".join(_normalize(source) for source in _answer_sources(attempt, stage_ids))


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value.lower())


def _evidence_for_keyword(sources: list[str], keyword: str) -> str | None:
    needle = _normalize(keyword)
    candidates = [
        part.strip()
        for source in sources
        for part in re.split(r"[。！？；\n]", source)
        if part.strip() and needle in _normalize(part)
    ]
    return min(candidates, key=len)[:160] if candidates else None


def _answer_sources(attempt: CaseAttempt, stage_ids: tuple[str, ...]) -> list[str]:
    text: list[str] = []
    if "history" in stage_ids:
        text.extend(message.content for message in attempt.messages if message.role == "user")
    for submission in attempt.submissions:
        if submission.stage_id in stage_ids:

            def collect(value: object) -> None:
                if (
                    isinstance(value, str)
                    and value.strip()
                    and value not in {"history", "differential", "tests", "management", "problem_representation"}
                ):
                    text.append(value.strip())
                elif isinstance(value, list):
                    for item in value:
                        collect(item)
                elif isinstance(value, dict):
                    for key, item in value.items():
                        if key not in {"stage_id", "priority"}:
                            collect(item)

            collect(submission.answer)
    return text


def assess_attempt(db: Session, attempt: CaseAttempt) -> CaseAssessment:
    if attempt.assessment:
        return attempt.assessment
    if attempt.status != "completed":
        raise HTTPException(status_code=409, detail="All stages must be completed before assessment")
    dimensions = []
    for dimension in (attempt.problem.rubric or {}).get("dimensions", []):
        text = _answer_text(attempt, tuple(dimension["stage_ids"]))
        criteria = dimension["criteria"]
        hits = [
            criterion for criterion in criteria if any(_normalize(keyword) in text for keyword in criterion["keywords"])
        ]
        raw = round(100 * len(hits) / len(criteria), 1) if criteria else 0
        if any(item.get("critical") for item in criteria) and any(
            item.get("critical") and item not in hits for item in criteria
        ):
            raw = min(raw, 69)
        sources = _answer_sources(attempt, tuple(dimension["stage_ids"]))
        evidence = []
        for criterion in hits:
            snippet = next((_evidence_for_keyword(sources, keyword) for keyword in criterion["keywords"]), None)
            if snippet and snippet not in evidence:
                evidence.append(snippet)
        evidence = evidence[:3] or ["尚未发现对应的学生原文证据"]
        missed = next((item for item in criteria if item not in hits), None)
        dimensions.append(
            {
                "dimension_id": dimension["id"],
                "label": dimension["label"],
                "score": raw,
                "weighted_score": round(raw * dimension["weight"] / 100, 1),
                "evidence": evidence,
                "feedback": "证据较完整。" if missed is None else missed["feedback"],
                "next_step": "继续保持结构化推理。" if missed is None else missed["feedback"],
            }
        )
    ai_result = ai_assessment(db, attempt)
    if ai_result is not None:
        deterministic = {item["dimension_id"]: item for item in dimensions}
        for candidate in ai_result.dimensions:
            target = deterministic.get(candidate.dimension_id)
            dimension_config = next(
                (
                    item
                    for item in (attempt.problem.rubric or {}).get("dimensions", [])
                    if item["id"] == candidate.dimension_id
                ),
                None,
            )
            if target is None or dimension_config is None:
                continue
            sources = _answer_sources(attempt, tuple(dimension_config["stage_ids"]))
            safe_evidence = [
                evidence[:160]
                for evidence in candidate.evidence[:3]
                if evidence and any(evidence in source for source in sources)
            ]
            if candidate.evidence and len(safe_evidence) != len(candidate.evidence[:3]):
                continue
            score = min(candidate.score, 100)
            if any(
                item.get("critical")
                and item
                not in [
                    criterion
                    for criterion in dimension_config["criteria"]
                    if any(
                        _normalize(keyword) in _answer_text(attempt, tuple(dimension_config["stage_ids"]))
                        for keyword in criterion["keywords"]
                    )
                ]
                for item in dimension_config["criteria"]
            ):
                score = min(score, 69)
            target["score"] = score
            target["weighted_score"] = round(score * dimension_config["weight"] / 100, 1)
            target["evidence"] = safe_evidence or ["尚未发现对应的学生原文证据"]
            target["feedback"] = candidate.feedback
            target["next_step"] = candidate.next_step
    expected_ids = {spec[0] for spec in DIMENSION_SPECS}
    if {item["dimension_id"] for item in dimensions} != expected_ids:
        raise HTTPException(status_code=422, detail="Case rubric is invalid")
    total = round(sum(item["weighted_score"] for item in dimensions))
    order = {stage: index for index, stage in enumerate(CASE_STAGES)}
    by_id = {item["dimension_id"]: item for item in dimensions}
    focus_dimension = min(
        dimensions,
        key=lambda item: (
            item["score"],
            order[next(spec[3][0] for spec in DIMENSION_SPECS if spec[0] == item["dimension_id"])],
        ),
    )
    focus_stage = next(spec[3][0] for spec in DIMENSION_SPECS if spec[0] == focus_dimension["dimension_id"])
    strengths = [item["label"] for item in dimensions if item["score"] >= 70]
    weaknesses = [item["label"] for item in dimensions if item["score"] < 70]
    assessment = CaseAssessment(
        attempt_id=attempt.id,
        total_score=total,
        dimensions=dimensions,
        strengths=strengths,
        weaknesses=weaknesses,
        next_steps=[by_id[focus_dimension["dimension_id"]]["next_step"]],
        summary=f"总分 {total}。{SAFETY_NOTICE}",
        focus_stage=focus_stage,
        fallback_used=ai_result is None,
        failure_reason=None if ai_result is not None else "AI disabled or unavailable",
        model_name="configured-model" if ai_result is not None else "deterministic-fallback",
    )
    attempt.status, attempt.current_stage, attempt.assessed_at = "assessed", "completed", datetime.now(UTC)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    if attempt.learning_task_id:
        task = db.get(LearningTask, attempt.learning_task_id)
        if task is not None:
            task.status = "completed"
            task.completed_at = datetime.now(UTC)
            db.commit()
    else:
        from app.services.personalized import ensure_learning_plan

        ensure_learning_plan(db, assessment)
    return assessment


def serialize_assessment(db: Session, assessment: CaseAssessment) -> dict:
    comparison = None
    attempt = assessment.attempt
    if attempt.retry_of_id:
        previous = db.scalar(
            select(CaseAssessment).join(CaseAttempt).where(CaseAssessment.attempt_id == attempt.retry_of_id)
        )
        if previous:
            old = {item["dimension_id"]: item for item in previous.dimensions}
            comparison = {
                "total_delta": round(assessment.total_score - previous.total_score, 1),
                "dimensions": [
                    {
                        "dimension_id": item["dimension_id"],
                        "previous_score": old.get(item["dimension_id"], {"score": 0})["score"],
                        "current_score": item["score"],
                        "delta": round(item["score"] - old.get(item["dimension_id"], {"score": 0})["score"], 1),
                    }
                    for item in assessment.dimensions
                ],
            }
    return {
        "attempt_id": assessment.attempt_id,
        "total_score": assessment.total_score,
        "dimensions": assessment.dimensions,
        "strengths": assessment.strengths,
        "weaknesses": assessment.weaknesses,
        "next_steps": assessment.next_steps,
        "summary": assessment.summary,
        "focus_stage": assessment.focus_stage,
        "model_name": assessment.model_name,
        "prompt_version": assessment.prompt_version,
        "fallback_used": assessment.fallback_used,
        "comparison": comparison,
    }
