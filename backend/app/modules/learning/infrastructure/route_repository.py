"""SQL persistence for learning routes. Transaction ownership stays in application."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError

from app.modules.learning.domain.learning_routes import (
    CASE_PHASES,
    REFLECTION_GOALS,
    case_transition,
    conflict,
    digest,
    mixed_objective_scores,
    percentage,
    validate_answers,
    validate_mixed_answers,
    validate_questions,
)
from app.modules.learning.infrastructure.models import StudentNotification
from app.modules.learning.infrastructure.route_models import (
    LearningRoute,
    LearningRouteStep,
    RouteCaseMessage,
    RouteCasePhaseDecision,
    RouteCaseSession,
    RouteCommandReceipt,
    RouteFinalTest,
    RouteLearningResult,
    RouteReadingProgress,
    RouteTestAttempt,
    RouteTestQuestion,
    RouteTestReviewEvent,
    RouteTestTutorMessage,
    RouteTestTutorSession,
)
from app.modules.learning.public import (
    StudentInsightQuestionScore,
    StudentInsightRouteRecord,
    StudentInsightTestResult,
)
from app.shared.errors import AppError


def now():
    return datetime.now(UTC)


def utc(value):
    return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


def uid():
    return str(uuid4())


class SqlLearningRouteStore:
    def __init__(self, session, timeout_seconds=60):
        self.db = session
        self.claim_seconds = timeout_seconds + 30

    def _execute(self, statement):
        try:
            return self.db.execute(statement.execution_options(synchronize_session=False))
        except IntegrityError:
            conflict("VERSION_CONFLICT")

    def _flush(self):
        try:
            self.db.flush()
        except IntegrityError:
            conflict("VERSION_CONFLICT")

    def _get(self, model, public_id):
        row = self.db.scalar(select(model).where(model.public_id == public_id))
        if row is None:
            raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)
        return row

    def _test(self, route):
        return self.db.scalar(select(RouteFinalTest).where(RouteFinalTest.route_id == route.id))

    def _steps(self, route):
        return list(
            self.db.scalars(
                select(LearningRouteStep)
                .where(LearningRouteStep.route_id == route.id)
                .order_by(LearningRouteStep.position)
            )
        )

    def _questions(self, test):
        return list(
            self.db.scalars(
                select(RouteTestQuestion)
                .where(RouteTestQuestion.test_id == test.id)
                .order_by(RouteTestQuestion.position)
            )
        )

    def _attempt(self, test):
        return self.db.scalar(select(RouteTestAttempt).where(RouteTestAttempt.test_id == test.id))

    def _receipt(self, actor, operation, request_id, payload, resource_id):
        fingerprint = digest({"resource_id": resource_id, "payload": payload})
        existing = self.db.scalar(
            select(RouteCommandReceipt).where(
                RouteCommandReceipt.actor_id == actor,
                RouteCommandReceipt.operation == operation,
                RouteCommandReceipt.client_request_id == request_id,
            )
        )
        if existing:
            if existing.payload_digest != fingerprint:
                conflict("IDEMPOTENCY_MISMATCH")
            return existing
        self.db.add(
            RouteCommandReceipt(
                actor_id=actor,
                operation=operation,
                client_request_id=request_id,
                payload_digest=fingerprint,
                resource_kind="learning_route",
                resource_public_id=resource_id,
                result_version=1,
            )
        )
        self._flush()
        return None

    def _record_response(self, actor, operation, request_id, response):
        receipt = self.db.scalar(
            select(RouteCommandReceipt).where(
                RouteCommandReceipt.actor_id == actor,
                RouteCommandReceipt.operation == operation,
                RouteCommandReceipt.client_request_id == request_id,
            )
        )
        receipt.response_snapshot = json.loads(json.dumps(response, default=lambda value: value.isoformat()))
        self._flush()
        return response

    def ensure_shell(self, context):
        existing = self.db.scalar(
            select(LearningRoute).where(LearningRoute.source_participation_id == context["source_participation_id"])
        )
        if existing:
            test = self._test(existing)
            return {"route_id": existing.public_id, "test_id": test.public_id, "created": False}
        private = context["source_kind"] == "autonomous"
        row = LearningRoute(
            public_id=uid(),
            student_id=context["student_id"],
            source_participation_id=context["source_participation_id"],
            session_id=context["session_id"],
            completion_snapshot_id=context["completion_snapshot_id"],
            source_kind=context["source_kind"],
            class_id=None if private else context["class_id"],
            teacher_id=None if private else context["teacher_id"],
            title="研讨后的学习计划",
            goal_point_codes=list(context["goal_point_codes"]),
            diagnosis_summary=context["diagnosis_summary"],
            generation_context={"materials": context["materials"], "goal_points": context["goal_points"]},
            generation_state="pending",
        )
        self.db.add(row)
        self._flush()
        test = RouteFinalTest(
            public_id=uid(),
            route_id=row.id,
            format_version="mixed_v2" if len(context["goal_point_codes"]) == 1 else "single_choice_v1",
            generation_state="pending",
            review_state="pending_review",
            review_kind="teacher",
        )
        self.db.add(test)
        self._flush()
        return {"route_id": row.public_id, "test_id": test.public_id, "created": True}

    def route(self, public_id):
        row = self.db.scalar(select(LearningRoute).where(LearningRoute.public_id == public_id))
        if row is None:
            return None
        return {
            "id": row.public_id,
            "student_id": row.student_id,
            "class_id": row.class_id,
            "teacher_id": row.teacher_id,
            "source_kind": row.source_kind,
            "goal_point_codes": row.goal_point_codes,
            "session_id": row.session_id,
        }

    def completion_locator(self, participation_id):
        route = self.db.scalar(select(LearningRoute).where(LearningRoute.source_participation_id == participation_id))
        if route is None:
            return {
                "learning_route_id": None,
                "final_test_id": None,
                "route_generation_state": None,
                "test_generation_state": None,
            }
        test = self._test(route)
        return {
            "learning_route_id": route.public_id,
            "final_test_id": test.public_id,
            "route_generation_state": route.generation_state,
            "test_generation_state": test.generation_state,
        }

    def review_locator(self, teacher_id, participation_id):
        route = self.db.scalar(
            select(LearningRoute).where(
                LearningRoute.source_participation_id == participation_id,
                LearningRoute.source_kind == "classroom",
                LearningRoute.teacher_id == teacher_id,
            )
        )
        if route is None:
            return None
        test = self._test(route)
        return {
            "learning_route_id": route.public_id,
            "final_test_id": test.public_id,
            "review_state": test.review_state,
            "generation_state": test.generation_state,
            "updated_at": test.updated_at,
        }

    def classroom_progress(self, teacher_id, class_id, session_id):
        rows = self.db.scalars(
            select(LearningRoute).where(
                LearningRoute.teacher_id == teacher_id,
                LearningRoute.class_id == class_id,
                LearningRoute.session_id == session_id,
                LearningRoute.source_kind == "classroom",
            )
        )
        result = []
        for route in rows:
            summary = self._summary(route)
            outcome = self.result(route.public_id)
            result.append(
                {
                    "student_id": route.student_id,
                    "learning_route_id": route.public_id,
                    "final_test_id": summary["test_summary"]["id"],
                    "result_id": summary["result_id"],
                    "route_status": summary["status"],
                    "generation_state": route.generation_state,
                    "work_item_status": "task_published"
                    if summary["test_summary"]["review_state"] == "released"
                    else "pending",
                    "task_progress": {
                        "completed": summary["progress"]["completed_steps"],
                        "total": summary["progress"]["total_steps"],
                    },
                    "score": outcome["score"] if outcome else None,
                }
            )
        return result

    def _retry_allowed(self, row, success):
        return row.generation_state != success and (
            row.generation_claim_expires_at is None or utc(row.generation_claim_expires_at) <= now()
        )

    def _locks(self, route, test):
        reasons = []
        if route.generation_state != "published" or route.route_completed_at is None:
            reasons.append("ROUTE_INCOMPLETE")
        if test.generation_state != "ready":
            reasons.append("TEST_NOT_GENERATED")
        if test.review_state != "released" or (route.source_kind == "classroom" and test.reviewer_id is None):
            reasons.append("TEST_NOT_RELEASED")
        return reasons

    def _test_summary(self, route, test):
        attempt = self._attempt(test)
        locks = self._locks(route, test)
        submitted = attempt is not None and attempt.status in {"grading", "submitted"}
        return {
            "id": test.public_id,
            "title": test.title,
            "question_count": len(self._questions(test)),
            "generation_state": test.generation_state,
            "review_state": test.review_state,
            "review_kind": test.review_kind if test.generation_state == "ready" else None,
            "can_start": not locks and not submitted,
            "lock_reason": (
                "GRADING_IN_PROGRESS" if attempt is not None and attempt.status == "grading" else "ALREADY_SUBMITTED"
            )
            if submitted
            else (locks[0] if locks else None),
            "claim_expires_at": test.generation_claim_expires_at,
            "retry_allowed": route.generation_state == "published" and self._retry_allowed(test, "ready"),
        }

    def _summary(self, route):
        test = self._test(route)
        steps = self._steps(route)
        attempt = self._attempt(test)
        result = self.db.scalar(select(RouteLearningResult).where(RouteLearningResult.route_id == route.id))
        if result:
            status, action = "completed", "view_result"
        elif attempt is not None and attempt.status == "grading":
            status, action = "grading", "wait_grade"
        elif route.generation_state != "published":
            failed = route.generation_state == "generation_failed"
            status, action = (
                ("generation_failed" if failed else "generating"),
                ("retry_route" if self._retry_allowed(route, "published") else "wait_generation"),
            )
        elif route.route_completed_at is None:
            step = next((x for x in steps if x.status != "completed"), None)
            status, action = "learning", step.kind if step else "wait_generation"
        elif test.generation_state != "ready":
            status, action = (
                "waiting_test_generation",
                "retry_test" if self._retry_allowed(test, "ready") else "wait_generation",
            )
        elif test.review_state != "released":
            status, action = "waiting_teacher", "wait_teacher"
        else:
            status, action = ("testing" if attempt else "ready_for_test"), "test"
        return {
            "id": route.public_id,
            "title": route.title,
            "source_kind": route.source_kind,
            "session_locator": str(route.session_id),
            "goal_point_codes": route.goal_point_codes,
            "status": status,
            "next_action": action,
            "progress": {"completed_steps": sum(x.status == "completed" for x in steps), "total_steps": len(steps)},
            "updated_at": route.updated_at,
            "test_summary": self._test_summary(route, test),
            "result_id": result.public_id if result else None,
            "generation_state": route.generation_state,
            "claim_expires_at": route.generation_claim_expires_at,
            "retry_allowed": self._retry_allowed(route, "published"),
        }

    def list_routes(self, student_id, status, limit, offset):
        completed = select(RouteLearningResult.route_id)
        query = select(LearningRoute).where(
            LearningRoute.student_id == student_id,
            LearningRoute.id.in_(completed) if status == "completed" else LearningRoute.id.not_in(completed),
        )
        total = self.db.scalar(select(func.count()).select_from(query.subquery()))
        rows = self.db.scalars(
            query.order_by(LearningRoute.updated_at.desc(), LearningRoute.id.desc()).limit(limit).offset(offset)
        )
        return {"items": [self._summary(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    @staticmethod
    def _insight_question_scores(snapshot):
        scores = []
        questions = snapshot.get("questions", []) if isinstance(snapshot, dict) else []
        for item in questions:
            if not isinstance(item, dict):
                continue
            code = item.get("point_code")
            earned = item.get("points_awarded")
            possible = item.get("points_possible")
            if (
                isinstance(code, str)
                and code.strip()
                and isinstance(earned, int | float)
                and isinstance(possible, int | float)
                and not isinstance(earned, bool)
                and not isinstance(possible, bool)
                and possible > 0
            ):
                scores.append(StudentInsightQuestionScore(code, float(earned), float(possible)))
                continue
            selected = item.get("selected_option")
            correct = item.get("correct_option")
            if (
                isinstance(code, str)
                and code.strip()
                and isinstance(selected, int)
                and not isinstance(selected, bool)
                and isinstance(correct, int)
                and not isinstance(correct, bool)
            ):
                scores.append(StudentInsightQuestionScore(code, float(selected == correct), 1.0))
        return tuple(scores)

    def student_insight_routes(self, student_id):
        routes = self.db.scalars(
            select(LearningRoute)
            .where(LearningRoute.student_id == student_id)
            .order_by(LearningRoute.updated_at.desc(), LearningRoute.id.desc())
        ).all()
        if not routes:
            return ()
        route_ids = tuple(route.id for route in routes)
        step_rows = self.db.execute(
            select(
                LearningRouteStep,
                RouteReadingProgress.accumulated_seconds,
                RouteReadingProgress.updated_at,
                RouteCaseSession.phase,
                RouteCaseSession.updated_at,
            )
            .outerjoin(
                RouteReadingProgress,
                and_(
                    RouteReadingProgress.step_id == LearningRouteStep.id,
                    RouteReadingProgress.student_id == student_id,
                ),
            )
            .outerjoin(
                RouteCaseSession,
                and_(
                    RouteCaseSession.step_id == LearningRouteStep.id,
                    RouteCaseSession.student_id == student_id,
                ),
            )
            .where(LearningRouteStep.route_id.in_(route_ids))
            .order_by(LearningRouteStep.route_id, LearningRouteStep.position)
        ).all()
        steps_by_route = {}
        reading_seconds_by_route = {}
        activity_by_route = {route_id: [] for route_id in route_ids}
        case_phase_by_step = {}
        for step, seconds, reading_updated_at, case_phase, case_updated_at in step_rows:
            steps_by_route.setdefault(step.route_id, []).append(step)
            activity_by_route[step.route_id].append(step.updated_at)
            if reading_updated_at is not None:
                activity_by_route[step.route_id].append(reading_updated_at)
            if case_phase is not None:
                case_phase_by_step[step.id] = case_phase
            if case_updated_at is not None:
                activity_by_route[step.route_id].append(case_updated_at)
            if step.kind == "reading":
                reading_seconds_by_route[step.route_id] = reading_seconds_by_route.get(step.route_id, 0) + int(
                    seconds or 0
                )
        test_rows = self.db.execute(
            select(
                LearningRoute.id,
                RouteFinalTest,
                RouteFinalTest.updated_at,
                RouteTestAttempt.id,
                RouteTestAttempt.status,
                RouteTestAttempt.submitted_at,
                RouteTestAttempt.updated_at,
                RouteLearningResult,
            )
            .join(RouteFinalTest, RouteFinalTest.route_id == LearningRoute.id)
            .outerjoin(
                RouteTestAttempt,
                and_(RouteTestAttempt.test_id == RouteFinalTest.id, RouteTestAttempt.student_id == student_id),
            )
            .outerjoin(
                RouteLearningResult,
                and_(
                    RouteLearningResult.route_id == LearningRoute.id,
                    RouteLearningResult.student_id == student_id,
                ),
            )
            .where(LearningRoute.id.in_(route_ids))
        ).all()
        tests_by_route = {
            route_id: (test, test_updated_at, attempt_id, attempt_status, submitted_at, attempt_updated_at, result)
            for (
                route_id,
                test,
                test_updated_at,
                attempt_id,
                attempt_status,
                submitted_at,
                attempt_updated_at,
                result,
            ) in test_rows
        }
        records = []
        for route in routes:
            steps = steps_by_route.get(route.id, [])
            (
                test,
                test_updated_at,
                attempt_id,
                attempt_status,
                submitted_at,
                attempt_updated_at,
                result,
            ) = tests_by_route.get(route.id, (None, None, None, None, None, None, None))
            valid_result = (
                result
                if result is not None and attempt_status == "submitted" and attempt_id == result.attempt_id
                else None
            )
            if valid_result is not None:
                status = "completed"
                result_record = StudentInsightTestResult(
                    result_id=valid_result.public_id,
                    score=float(valid_result.score),
                    correct_count=valid_result.correct_count,
                    question_count=valid_result.question_count,
                    completed_at=valid_result.completed_at,
                    question_scores=self._insight_question_scores(valid_result.result_snapshot),
                )
                activity_by_route[route.id].extend((valid_result.completed_at, submitted_at, attempt_updated_at))
            else:
                result_record = None
                if attempt_status == "grading":
                    status = "grading"
                elif route.generation_state != "published":
                    status = "generation_failed" if route.generation_state == "generation_failed" else "generating"
                elif route.route_completed_at is None:
                    status = "learning"
                elif test is None or test.generation_state != "ready":
                    status = "waiting_test_generation"
                elif test.review_state != "released":
                    status = "waiting_teacher"
                else:
                    status = "testing" if attempt_status else "ready_for_test"
            if test_updated_at is not None:
                activity_by_route[route.id].append(test_updated_at)
            if submitted_at is not None:
                activity_by_route[route.id].append(submitted_at)
            if attempt_updated_at is not None:
                activity_by_route[route.id].append(attempt_updated_at)
            current_step = next((step for step in steps if step.status != "completed"), None)
            records.append(
                StudentInsightRouteRecord(
                    route_id=route.public_id,
                    session_id=route.session_id,
                    source_kind=route.source_kind,
                    goal_point_codes=tuple(route.goal_point_codes or ()),
                    created_at=route.created_at,
                    updated_at=max([route.updated_at, *activity_by_route[route.id]]),
                    route_generation_state=route.generation_state,
                    status=status,
                    completed_steps=sum(step.status == "completed" for step in steps),
                    total_steps=len(steps),
                    reading_seconds=reading_seconds_by_route.get(route.id, 0),
                    current_step_kind=current_step.kind if current_step else None,
                    current_case_phase=case_phase_by_step.get(current_step.id) if current_step else None,
                    result=result_record,
                    title=route.title,
                )
            )
        return tuple(records)

    def _step_summary(self, step):
        case = (
            self.db.scalar(select(RouteCaseSession).where(RouteCaseSession.step_id == step.id))
            if step.kind == "case"
            else None
        )
        return {
            "id": step.public_id,
            "position": step.position,
            "kind": step.kind,
            "title": step.title,
            "goal_point_codes": step.goal_point_codes,
            "status": step.status,
            "case_id": case.public_id if case else None,
            "completed_at": step.completed_at,
        }

    def detail(self, public_id):
        row = self._get(LearningRoute, public_id)
        test = self._test(row)
        summary = self._summary(row)
        return {
            "summary": summary,
            "diagnosis_summary": row.diagnosis_summary,
            "steps": [self._step_summary(x) for x in self._steps(row)],
            "test_summary": summary["test_summary"],
            "can_start_test": summary["test_summary"]["can_start"],
            "lock_reasons": self._locks(row, test),
            "route_version": row.content_version or 1,
        }

    def _progress(self, row):
        return {
            "lease_token": row.active_lease_token if row else None,
            "accumulated_seconds": row.accumulated_seconds if row else 0,
            "last_seen_at": row.last_seen_at if row else None,
        }

    def step(self, public_id):
        row = self.db.scalar(select(LearningRouteStep).where(LearningRouteStep.public_id == public_id))
        if row is None:
            return None
        route = self.db.get(LearningRoute, row.route_id)
        data = {**self._step_summary(row), "route_id": route.public_id}
        if row.kind == "reading" and row.status != "locked":
            progress = self.db.scalar(select(RouteReadingProgress).where(RouteReadingProgress.step_id == row.id))
            data.update(
                sources=row.source_snapshot.get("sources", []),
                ai_guide=row.public_definition.get("ai_guide", ""),
                sections=[
                    {"title": f"讲解 {i}", "text": text}
                    for i, text in enumerate(row.public_definition.get("explanation_segments", []), 1)
                ],
                learning_points=row.public_definition.get("learning_points", []),
                reading_progress=self._progress(progress),
            )
        return data

    def reading_progress(self, step_id, action, lease, request_id):
        step = self._get(LearningRouteStep, step_id)
        route = self.db.get(LearningRoute, step.route_id)
        if step.kind != "reading" or step.status == "locked":
            conflict("STEP_LOCKED")
        replay = self._receipt(route.student_id, "reading_" + action, request_id, {"lease": lease}, step_id)
        progress = self.db.scalar(select(RouteReadingProgress).where(RouteReadingProgress.step_id == step.id))
        if replay:
            return replay.response_snapshot or self._progress(progress)
        if progress is None:
            progress = RouteReadingProgress(step_id=step.id, student_id=route.student_id, accumulated_seconds=0)
            self.db.add(progress)
        self._flush()
        timestamp = now()
        expected_seen = progress.last_seen_at
        expected_lease = progress.active_lease_token
        if action == "start":
            values = {
                "active_lease_token": uid(),
                "active_lease_expires_at": timestamp + timedelta(seconds=30),
                "last_seen_at": timestamp,
            }
            if step.status == "available":
                step.status = "in_progress"
        else:
            if not lease or lease != expected_lease:
                conflict("READING_LEASE_INVALID")
            elapsed = 0
            if expected_seen and utc(progress.active_lease_expires_at) >= timestamp:
                elapsed = max(0, min(30, int((timestamp - utc(expected_seen)).total_seconds())))
            values = {
                "accumulated_seconds": RouteReadingProgress.accumulated_seconds + elapsed,
                "last_seen_at": timestamp,
                "active_lease_expires_at": timestamp + timedelta(seconds=30),
            }
            if action == "pause":
                values.update(active_lease_token=None, active_lease_expires_at=None)
        changed = self._execute(
            update(RouteReadingProgress)
            .where(
                RouteReadingProgress.id == progress.id,
                RouteReadingProgress.last_seen_at == expected_seen,
                RouteReadingProgress.active_lease_token == expected_lease,
            )
            .values(**values)
        )
        if changed.rowcount != 1:
            conflict("READING_LEASE_INVALID")
        self._flush()
        self.db.refresh(progress)
        return self._record_response(route.student_id, "reading_" + action, request_id, self._progress(progress))

    def _complete_step(self, step):
        if step.status == "completed":
            return
        step.status, step.completed_at = "completed", now()
        route = self.db.get(LearningRoute, step.route_id)
        following = self.db.scalar(
            select(LearningRouteStep).where(
                LearningRouteStep.route_id == step.route_id, LearningRouteStep.position == step.position + 1
            )
        )
        if following:
            following.status = "available"
        else:
            route.route_completed_at = now()
        route.updated_at = now()
        self._flush()

    def complete_reading(self, step_id, request_id):
        step = self._get(LearningRouteStep, step_id)
        route = self.db.get(LearningRoute, step.route_id)
        if step.kind != "reading" or step.status == "locked":
            conflict("STEP_LOCKED")
        self._receipt(route.student_id, "complete_reading", request_id, {}, step_id)
        self._complete_step(step)
        return self.detail(route.public_id)

    def test(self, public_id):
        test = self.db.scalar(select(RouteFinalTest).where(RouteFinalTest.public_id == public_id))
        if test is None:
            return None
        return {"id": test.public_id, "route_id": self.db.get(LearningRoute, test.route_id).public_id}

    def _accessible_test(self, test):
        route = self.db.get(LearningRoute, test.route_id)
        locks = self._locks(route, test)
        if locks:
            conflict(locks[0])
        return route

    def _attempt_read(self, attempt):
        return {
            "id": attempt.public_id,
            "status": attempt.status,
            "version": attempt.draft_version,
            "answers": attempt.answers,
            "saved_at": attempt.updated_at,
            "submitted_at": attempt.submitted_at,
        }

    def student_test(self, route_id):
        route = self._get(LearningRoute, route_id)
        test = self._test(route)
        self._accessible_test(test)
        attempt = self._attempt(test)
        return {
            "id": test.public_id,
            "title": test.title,
            "review_kind": test.review_kind,
            "format_version": test.format_version,
            "released_version": test.released_version,
            "released_digest": test.released_digest,
            "questions": [
                {
                    "id": q.public_id,
                    "source_digest": digest(self._bank_payload(q)),
                    "position": q.position,
                    "point_code": q.primary_point_code,
                    "prompt": q.prompt,
                    "question_type": q.question_type,
                    "options": q.options,
                }
                for q in self._questions(test)
            ],
            "attempt": self._attempt_read(attempt) if attempt else None,
        }

    def start_test(self, public_id, request_id):
        test = self._get(RouteFinalTest, public_id)
        route = self._accessible_test(test)
        attempt = self._attempt(test)
        if attempt and attempt.status in {"grading", "submitted"}:
            conflict("ALREADY_SUBMITTED")
        self._receipt(route.student_id, "start_test", request_id, {}, public_id)
        if attempt is None:
            attempt = RouteTestAttempt(
                public_id=uid(),
                test_id=test.id,
                student_id=route.student_id,
                test_version=test.released_version,
                test_digest=test.released_digest,
                draft_version=1,
                answers={},
                status="in_progress",
            )
            self.db.add(attempt)
            self._flush()
        return self.student_test(route.public_id)

    def _draft_check(self, test, attempt, payload):
        if attempt is None:
            conflict("TEST_NOT_STARTED")
        if attempt.status != "in_progress":
            conflict("ALREADY_SUBMITTED")
        if (
            attempt.draft_version != payload["expected_version"]
            or test.released_digest != payload["released_digest"]
            or attempt.test_digest != test.released_digest
        ):
            conflict("VERSION_CONFLICT")

    def save_draft(self, test_id, payload):
        test = self._get(RouteFinalTest, test_id)
        route = self._accessible_test(test)
        attempt = self._attempt(test)
        replay = self._receipt(route.student_id, "save_test_draft", payload["client_request_id"], payload, test_id)
        if replay:
            return replay.response_snapshot or self._attempt_read(attempt)
        self._draft_check(test, attempt, payload)
        questions = self._questions(test)
        if test.format_version == "mixed_v2":
            validate_mixed_answers(
                payload["answers"],
                [{"id": q.public_id, "question_type": q.question_type} for q in questions],
            )
        else:
            validate_answers(payload["answers"], {q.public_id for q in questions})
        changed = self._execute(
            update(RouteTestAttempt)
            .where(
                RouteTestAttempt.id == attempt.id,
                RouteTestAttempt.draft_version == payload["expected_version"],
                RouteTestAttempt.status == "in_progress",
            )
            .values(answers=payload["answers"], draft_version=attempt.draft_version + 1, updated_at=now())
        )
        if changed.rowcount != 1:
            conflict("VERSION_CONFLICT")
        self.db.refresh(attempt)
        return self._record_response(
            route.student_id, "save_test_draft", payload["client_request_id"], self._attempt_read(attempt)
        )

    def prepare_submission(self, test_id, payload):
        test = self._get(RouteFinalTest, test_id)
        route = self._accessible_test(test)
        attempt = self._attempt(test)
        fingerprint = digest(payload)
        if test.format_version == "mixed_v2":
            return self._prepare_mixed_submission(test, route, attempt, payload, fingerprint)
        if attempt and attempt.status == "submitted":
            if attempt.submission_id == payload["client_submission_id"] and attempt.submission_digest == fingerprint:
                return {"created": False, "result": self.result(route.public_id)}
            conflict("ALREADY_SUBMITTED")
        self._draft_check(test, attempt, payload)
        questions = self._questions(test)
        answers = payload["answers"]
        validate_answers(answers, {q.public_id for q in questions}, complete=True)
        correct = sum(answers[q.public_id] == q.correct_option for q in questions)
        score, timestamp = percentage(correct, len(questions)), now()
        changed = self._execute(
            update(RouteTestAttempt)
            .where(
                RouteTestAttempt.id == attempt.id,
                RouteTestAttempt.draft_version == payload["expected_version"],
                RouteTestAttempt.status == "in_progress",
            )
            .values(
                answers=answers,
                status="submitted",
                submission_id=payload["client_submission_id"],
                submission_digest=fingerprint,
                correct_count=correct,
                question_count=len(questions),
                score=Decimal(str(score)),
                submitted_at=timestamp,
            )
        )
        if changed.rowcount != 1:
            conflict("VERSION_CONFLICT")
        result_id = uid()
        snapshot = {
            "id": result_id,
            "route_id": route.public_id,
            "source_kind": route.source_kind,
            "goal_point_codes": route.goal_point_codes,
            "route_summary": {
                "title": route.title,
                "diagnosis_summary": route.diagnosis_summary,
                "steps": [
                    {
                        "title": s.title,
                        "kind": s.kind,
                        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    }
                    for s in self._steps(route)
                ],
            },
            "correct_count": correct,
            "question_count": len(questions),
            "score": score,
            "submitted_at": timestamp.isoformat(),
            "review_kind": test.review_kind,
            "questions": [
                {
                    "id": q.public_id,
                    "position": q.position,
                    "point_code": q.primary_point_code,
                    "prompt": q.prompt,
                    "options": q.options,
                    "selected_option": answers[q.public_id],
                    "correct_option": q.correct_option,
                    "explanation": q.explanation,
                }
                for q in questions
            ],
        }
        self.db.add(
            RouteLearningResult(
                public_id=result_id,
                route_id=route.id,
                attempt_id=attempt.id,
                student_id=route.student_id,
                source_kind=route.source_kind,
                class_id=route.class_id,
                teacher_id=route.teacher_id,
                policy_version="single-final-test-v1",
                source_digest=test.released_digest,
                result_snapshot=snapshot,
                correct_count=correct,
                question_count=len(questions),
                score=Decimal(str(score)),
                completed_at=timestamp,
            )
        )
        self._notify(route, "learning_route_completed", "学习结果已生成", "本次最终测试已提交，可查看成绩与解析。")
        route.updated_at = timestamp
        self._flush()
        metrics = [
            (
                code,
                sum(answers[q.public_id] == q.correct_option for q in questions if q.primary_point_code == code),
                sum(q.primary_point_code == code for q in questions),
            )
            for code in route.goal_point_codes
        ]
        return {
            "created": True,
            "result": snapshot,
            "route": self.route(route.public_id),
            "metrics": metrics,
            "occurred_at": timestamp,
        }

    def _prepare_mixed_submission(self, test, route, attempt, payload, fingerprint):
        if attempt is not None and attempt.status in {"grading", "submitted"}:
            if attempt.submission_id != payload["client_submission_id"] or attempt.submission_digest != fingerprint:
                conflict("ALREADY_SUBMITTED")
            if attempt.status == "submitted":
                return {"created": False, "result": self.result(route.public_id)}
            return {"created": False, "grading": True, "test_id": test.public_id, "route_id": route.public_id}
        self._draft_check(test, attempt, payload)
        questions = self._questions(test)
        answers = payload["answers"]
        question_data = [
            {
                "id": q.public_id,
                "question_type": q.question_type,
                "correct_option": q.correct_option,
                "correct_options": q.private_grading.get("correct_options"),
            }
            for q in questions
        ]
        validate_mixed_answers(answers, question_data, complete=True)
        _, correct = mixed_objective_scores(answers, question_data)
        timestamp = now()
        changed = self._execute(
            update(RouteTestAttempt)
            .where(
                RouteTestAttempt.id == attempt.id,
                RouteTestAttempt.draft_version == payload["expected_version"],
                RouteTestAttempt.status == "in_progress",
            )
            .values(
                answers=answers,
                status="grading",
                submission_id=payload["client_submission_id"],
                submission_digest=fingerprint,
                correct_count=correct,
                question_count=5,
                submitted_at=timestamp,
                grading_error_code=None,
            )
        )
        if changed.rowcount != 1:
            conflict("VERSION_CONFLICT")
        self.db.refresh(attempt)
        return {"created": True, "grading": True, "test_id": test.public_id, "route_id": route.public_id}

    def grading_status(self, test_id):
        test = self._get(RouteFinalTest, test_id)
        route = self.db.get(LearningRoute, test.route_id)
        attempt = self._attempt(test)
        if attempt is None or attempt.status == "in_progress":
            conflict("TEST_NOT_SUBMITTED")
        result = self.db.scalar(select(RouteLearningResult).where(RouteLearningResult.attempt_id == attempt.id))
        return {
            "status": "completed" if result is not None else "grading",
            "test_id": test.public_id,
            "route_id": route.public_id,
            "result_id": result.public_id if result is not None else None,
            "retry_allowed": (
                result is None
                and (attempt.grading_claim_expires_at is None or utc(attempt.grading_claim_expires_at) <= now())
            ),
            "error_code": attempt.grading_error_code if result is None else None,
        }

    def claim_grading(self, test_id):
        test = self._get(RouteFinalTest, test_id)
        attempt = self._attempt(test)
        if test.format_version != "mixed_v2" or attempt is None or attempt.status != "grading":
            return {"execute": False}
        timestamp, token = now(), uid()
        changed = self._execute(
            update(RouteTestAttempt)
            .where(
                RouteTestAttempt.id == attempt.id,
                RouteTestAttempt.status == "grading",
                or_(
                    RouteTestAttempt.grading_claim_expires_at.is_(None),
                    RouteTestAttempt.grading_claim_expires_at <= timestamp,
                ),
            )
            .values(
                grading_claim_token=token,
                grading_claim_expires_at=timestamp + timedelta(seconds=self.claim_seconds),
                grading_error_code=None,
            )
        )
        if changed.rowcount != 1:
            return {"execute": False}
        question = next(q for q in self._questions(test) if q.question_type == "short_answer")
        self._flush()
        return {
            "execute": True,
            "token": token,
            "input": {
                "question_id": question.public_id,
                "question_prompt": question.prompt,
                "reference_answer": question.private_grading["reference_answer"],
                "rubric": question.private_grading["rubric"],
                "student_answer": attempt.answers[question.public_id],
            },
        }

    def finish_grading(self, test_id, claim, grade):
        test = self._get(RouteFinalTest, test_id)
        route = self.db.get(LearningRoute, test.route_id)
        attempt = self._attempt(test)
        timestamp = now()
        if (
            attempt.status != "grading"
            or attempt.grading_claim_token != claim["token"]
            or utc(attempt.grading_claim_expires_at) <= timestamp
        ):
            conflict("GRADING_CLAIM_EXPIRED")
        questions = self._questions(test)
        question_data = [
            {
                "id": q.public_id,
                "question_type": q.question_type,
                "correct_option": q.correct_option,
                "correct_options": q.private_grading.get("correct_options"),
            }
            for q in questions
        ]
        objective_scores, correct = mixed_objective_scores(attempt.answers, question_data)
        short = next(q for q in questions if q.question_type == "short_answer")
        if grade["question_id"] != short.public_id:
            conflict("GRADING_QUESTION_MISMATCH")
        criterion_scores = {item["criterion_id"]: item for item in grade["criterion_results"]}
        if set(criterion_scores) != {item["criterion_id"] for item in short.private_grading["rubric"]}:
            conflict("GRADING_RUBRIC_MISMATCH")
        short_score = sum(item["earned_points"] for item in criterion_scores.values())
        score = sum(objective_scores.values()) + short_score
        changed = self._execute(
            update(RouteTestAttempt)
            .where(
                RouteTestAttempt.id == attempt.id,
                RouteTestAttempt.status == "grading",
                RouteTestAttempt.grading_claim_token == claim["token"],
                RouteTestAttempt.grading_claim_expires_at > timestamp,
            )
            .values(
                status="submitted",
                score=Decimal(score),
                correct_count=correct,
                grading_claim_token=None,
                grading_claim_expires_at=None,
                grading_error_code=None,
            )
        )
        if changed.rowcount != 1:
            conflict("GRADING_CLAIM_EXPIRED")
        result_id = uid()
        snapshot = {
            "id": result_id,
            "route_id": route.public_id,
            "source_kind": route.source_kind,
            "goal_point_codes": route.goal_point_codes,
            "route_summary": {
                "title": route.title,
                "diagnosis_summary": route.diagnosis_summary,
                "steps": [
                    {
                        "title": step.title,
                        "kind": step.kind,
                        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                    }
                    for step in self._steps(route)
                ],
            },
            "correct_count": correct,
            "question_count": 5,
            "score": score,
            "submitted_at": attempt.submitted_at.isoformat(),
            "review_kind": test.review_kind,
            "format_version": "mixed_v2",
            "questions": [],
        }
        for q in questions:
            item = {
                "id": q.public_id,
                "position": q.position,
                "point_code": q.primary_point_code,
                "prompt": q.prompt,
                "question_type": q.question_type,
                "options": q.options,
                "explanation": q.explanation,
                "points_possible": {
                    "single_choice": 15,
                    "multiple_choice": 25,
                    "short_answer": 30,
                }[q.question_type],
                "points_awarded": short_score if q.question_type == "short_answer" else objective_scores[q.public_id],
            }
            if q.question_type == "single_choice":
                item.update(selected_option=attempt.answers[q.public_id], correct_option=q.correct_option)
            elif q.question_type == "multiple_choice":
                item.update(
                    selected_options=attempt.answers[q.public_id],
                    correct_options=q.private_grading["correct_options"],
                )
            else:
                item.update(
                    selected_text=attempt.answers[q.public_id],
                    reference_answer=q.private_grading["reference_answer"],
                    rubric_results=grade["criterion_results"],
                    grading_feedback=grade["feedback"],
                )
            snapshot["questions"].append(item)
        self.db.add(
            RouteLearningResult(
                public_id=result_id,
                route_id=route.id,
                attempt_id=attempt.id,
                student_id=route.student_id,
                source_kind=route.source_kind,
                class_id=route.class_id,
                teacher_id=route.teacher_id,
                policy_version="mixed-final-test-v2",
                source_digest=test.released_digest,
                result_snapshot=snapshot,
                correct_count=correct,
                question_count=5,
                score=Decimal(score),
                completed_at=timestamp,
            )
        )
        self._notify(route, "learning_route_completed", "学习结果已生成", "本次最终测试已完成判分，可查看成绩与解析。")
        route.updated_at = timestamp
        self._flush()
        return {"result": snapshot, "route": self.route(route.public_id), "score": score, "occurred_at": timestamp}

    def fail_grading(self, test_id, claim):
        test = self._get(RouteFinalTest, test_id)
        attempt = self._attempt(test)
        if attempt is not None and attempt.status == "grading" and attempt.grading_claim_token == claim["token"]:
            attempt.grading_claim_token = None
            attempt.grading_claim_expires_at = None
            attempt.grading_error_code = "grading_unavailable"
            self._flush()

    def result(self, route_id):
        route = self._get(LearningRoute, route_id)
        result = self.db.scalar(select(RouteLearningResult).where(RouteLearningResult.route_id == route.id))
        return result.result_snapshot if result else None

    def result_locator(self, result_id):
        result = self.db.scalar(select(RouteLearningResult).where(RouteLearningResult.public_id == result_id))
        if result is None:
            return None
        return {"route_id": self.db.get(LearningRoute, result.route_id).public_id, "student_id": result.student_id}

    def _tutor_session(self, result):
        return self.db.scalar(select(RouteTestTutorSession).where(RouteTestTutorSession.result_id == result.id))

    def _tutor_messages(self, session):
        if session is None:
            return []
        return list(
            self.db.scalars(
                select(RouteTestTutorMessage)
                .where(RouteTestTutorMessage.session_id == session.id)
                .order_by(RouteTestTutorMessage.sequence)
            )
        )

    def tutor_read(self, result_id):
        result = self._get(RouteLearningResult, result_id)
        session = self._tutor_session(result)
        messages = self._tutor_messages(session)
        answered = {message.turn_id for message in messages if message.role == "assistant"}
        pending = next(
            (
                message
                for message in reversed(messages)
                if message.role == "student" and message.turn_id not in answered
            ),
            None,
        )
        processing = (
            pending is not None and session.claim_expires_at is not None and utc(session.claim_expires_at) > now()
        )
        return {
            "result_id": result_id,
            "revision": session.revision if session is not None else 0,
            "processing_state": "processing" if processing else "retry_allowed" if pending is not None else "idle",
            "pending_message_id": pending.turn_id if pending is not None else None,
            "messages": [
                {
                    "id": item.public_id,
                    "role": item.role,
                    "question_id": self.db.get(RouteTestQuestion, item.question_id).public_id,
                    "content": item.content,
                    "sequence": item.sequence,
                    "created_at": item.created_at,
                }
                for item in messages
            ],
        }

    def claim_tutor_message(self, result_id, payload):
        result = self._get(RouteLearningResult, result_id)
        question_ids = {item["id"] for item in result.result_snapshot["questions"]}
        if payload["question_id"] not in question_ids:
            raise AppError("VALIDATION_ERROR", "题目不属于本次结果", 422)
        session = self._tutor_session(result)
        if session is None:
            session = RouteTestTutorSession(public_id=uid(), result_id=result.id, revision=0)
            self.db.add(session)
            self._flush()
        messages = self._tutor_messages(session)
        existing = next(
            (item for item in messages if item.turn_id == payload["client_message_id"] and item.role == "student"),
            None,
        )
        answered = {item.turn_id for item in messages if item.role == "assistant"}
        pending = next(
            (item for item in reversed(messages) if item.role == "student" and item.turn_id not in answered),
            None,
        )
        if existing is not None:
            existing_question_id = self.db.get(RouteTestQuestion, existing.question_id).public_id
            if existing.content != payload["content"] or existing_question_id != payload["question_id"]:
                conflict("IDEMPOTENCY_MISMATCH")
            if existing.turn_id in answered:
                return {"execute": False, "response": self.tutor_read(result_id)}
            if session.claim_expires_at is not None and utc(session.claim_expires_at) > now():
                return {"execute": False, "response": self.tutor_read(result_id)}
        else:
            if pending is not None:
                conflict("PENDING_TUTOR_MESSAGE")
            if session.revision != payload["expected_revision"]:
                conflict("VERSION_CONFLICT")
            question = self._get(RouteTestQuestion, payload["question_id"])
            session.revision += 1
            existing = RouteTestTutorMessage(
                public_id=uid(),
                session_id=session.id,
                question_id=question.id,
                turn_id=payload["client_message_id"],
                sequence=session.revision,
                role="student",
                content=payload["content"],
            )
            self.db.add(existing)
        token = uid()
        session.claim_token = token
        session.claim_expires_at = now() + timedelta(seconds=self.claim_seconds)
        self._flush()
        selected = [item for item in messages if item.sequence < existing.sequence][-30:]
        bounded: list[RouteTestTutorMessage] = []
        used = 0
        for item in reversed(selected):
            if bounded and used + len(item.content) > 12000:
                break
            bounded.append(item)
            used += len(item.content)
        history = [
            {
                "role": item.role,
                "question_id": self.db.get(RouteTestQuestion, item.question_id).public_id,
                "text": item.content,
            }
            for item in reversed(bounded)
        ]
        return {
            "execute": True,
            "token": token,
            "turn_id": payload["client_message_id"],
            "input": {
                "current_question_id": payload["question_id"],
                "question_results": result.result_snapshot["questions"],
                "conversation_summary": session.summary,
                "history": history,
                "student_message": payload["content"],
            },
        }

    def save_tutor_reply(self, result_id, claim, reply):
        result = self._get(RouteLearningResult, result_id)
        session = self._tutor_session(result)
        if (
            session is None
            or session.claim_token != claim["token"]
            or utc(session.claim_expires_at) <= now()
            or reply["current_question_id"] != claim["input"]["current_question_id"]
        ):
            conflict("TUTOR_CLAIM_EXPIRED")
        question = self._get(RouteTestQuestion, reply["current_question_id"])
        session.revision += 1
        self.db.add(
            RouteTestTutorMessage(
                public_id=uid(),
                session_id=session.id,
                question_id=question.id,
                turn_id=claim["turn_id"],
                sequence=session.revision,
                role="assistant",
                content=reply["reply"],
            )
        )
        session.summary = reply["updated_summary"]
        session.claim_token = None
        session.claim_expires_at = None
        self._flush()
        return self.tutor_read(result_id)

    def fail_tutor_reply(self, result_id, claim):
        result = self._get(RouteLearningResult, result_id)
        session = self._tutor_session(result)
        if session is not None and session.claim_token == claim["token"]:
            session.claim_token = None
            session.claim_expires_at = None
            self._flush()

    def _case_goals(self, step, phase):
        if phase == "summary_reflection":
            return REFLECTION_GOALS
        return next((p["goals"] for p in step.private_definition.get("phases", []) if p["phase"] == phase), [])

    def _case_stages(self, step):
        return [
            {
                "phase": phase,
                "goals": [{"goal_id": goal["goal_id"], "objective": goal["objective"]} for goal in goals],
                "prompt": next((prompt for goal in goals for prompt in goal.get("guidance_prompts", [])), ""),
            }
            for phase in CASE_PHASES
            for goals in [self._case_goals(step, phase)]
        ]

    def _case_message_phases(self, case, messages):
        decisions = list(
            self.db.scalars(
                select(RouteCasePhaseDecision)
                .where(RouteCasePhaseDecision.case_session_id == case.id)
                .order_by(RouteCasePhaseDecision.revision)
            )
        )
        phases = {}
        for message in messages:
            phase = CASE_PHASES[0]
            for decision in decisions:
                if message.request_revision <= decision.revision:
                    phase = decision.phase
                    break
                if decision.decision == "advance":
                    phase = CASE_PHASES[CASE_PHASES.index(decision.phase) + 1]
                else:
                    phase = decision.phase
            phases[message.id] = phase
        return phases

    def _case_messages(self, case):
        return list(
            self.db.scalars(
                select(RouteCaseMessage)
                .where(RouteCaseMessage.case_session_id == case.id)
                .order_by(RouteCaseMessage.sequence)
            )
        )

    def case(self, public_id):
        case = self.db.scalar(select(RouteCaseSession).where(RouteCaseSession.public_id == public_id))
        if case is None:
            return None
        step = self.db.get(LearningRouteStep, case.step_id)
        if step.status == "locked":
            conflict("STEP_LOCKED")
        route = self.db.get(LearningRoute, step.route_id)
        stages = self._case_stages(step)
        messages = self._case_messages(case)
        message_phases = self._case_message_phases(case, messages)
        pending = next(
            (
                m
                for m in reversed(messages)
                if m.role == "student" and m.processing_status in {"processing", "failed", "pending"}
            ),
            None,
        )
        return {
            "id": case.public_id,
            "route_id": route.public_id,
            "step_id": step.public_id,
            "synthetic_case": {
                **step.public_definition,
                "case_facts": [
                    fact["text"] if isinstance(fact, dict) else fact for fact in step.public_definition["case_facts"]
                ],
            },
            "phase": case.phase,
            "revision": case.revision,
            "status": case.status,
            "goals": next((stage["goals"] for stage in stages if stage["phase"] == case.phase), []),
            "stages": stages,
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "revision": m.request_revision,
                    "phase": message_phases[m.id],
                }
                for m in messages
            ],
            "next_prompt": next((stage["prompt"] for stage in stages if stage["phase"] == case.phase), ""),
            "safety_notice": "AI 合成教学病例，未经教师审核，仅供病理学学习。",
            "pending_message": {
                "client_message_id": pending.client_message_id,
                "request_revision": pending.request_revision,
                "processing_state": pending.processing_status,
                "retry_allowed": pending.processing_expires_at is None or utc(pending.processing_expires_at) <= now(),
                "claim_expires_at": pending.processing_expires_at,
            }
            if pending
            else None,
        }

    def _message_result(self, case, message):
        decision = self.db.scalar(select(RouteCasePhaseDecision).where(RouteCasePhaseDecision.message_id == message.id))
        reply = self.db.scalar(
            select(RouteCaseMessage).where(
                RouteCaseMessage.case_session_id == case.id,
                RouteCaseMessage.sequence == message.sequence + 1,
                RouteCaseMessage.role == "assistant",
            )
        )
        return {
            "client_message_id": message.client_message_id,
            "request_revision": message.request_revision,
            "processing_state": message.processing_status,
            "retry_allowed": message.processing_status == "failed"
            or (message.processing_status == "processing" and utc(message.processing_expires_at) <= now()),
            "reply": reply.content if reply else None,
            "phase": case.phase,
            "revision": case.revision,
            "decision": decision.decision if decision else None,
            "missing_elements": decision.missing_goal_codes if decision else [],
            "status": case.status,
        }

    def claim_case_message(self, public_id, message_id, content, revision):
        case = self._get(RouteCaseSession, public_id)
        step = self.db.get(LearningRouteStep, case.step_id)
        if step.status == "locked":
            conflict("STEP_LOCKED")
        messages = self._case_messages(case)
        existing = next((m for m in messages if m.client_message_id == message_id), None)
        fingerprint = digest(content)
        if existing:
            if existing.payload_digest != fingerprint:
                conflict("IDEMPOTENCY_MISMATCH")
            if existing.processing_status in {"completed", "blocked"} or (
                existing.processing_status == "processing" and utc(existing.processing_expires_at) > now()
            ):
                return {"execute": False, "response": self._message_result(case, existing)}
            if existing.request_revision != case.revision:
                conflict("VERSION_CONFLICT")
        else:
            if case.phase == "completed":
                conflict("CASE_COMPLETED")
            if any(m.processing_status == "processing" and utc(m.processing_expires_at) > now() for m in messages):
                conflict("MESSAGE_IN_PROGRESS")
            if revision != case.revision:
                conflict("VERSION_CONFLICT")
            changed = self._execute(
                update(RouteCaseSession)
                .where(RouteCaseSession.id == case.id, RouteCaseSession.revision == revision)
                .values(revision=revision + 1)
            )
            if changed.rowcount != 1:
                conflict("VERSION_CONFLICT")
            self.db.refresh(case)
            existing = RouteCaseMessage(
                case_session_id=case.id,
                sequence=max((m.sequence for m in messages), default=0) + 1,
                role="student",
                content=content,
                client_message_id=message_id,
                request_revision=case.revision,
                processing_status="pending",
                payload_digest=fingerprint,
            )
            self.db.add(existing)
            self._flush()
        token = uid()
        changed = self._execute(
            update(RouteCaseMessage)
            .where(
                RouteCaseMessage.id == existing.id,
                or_(
                    RouteCaseMessage.processing_status.in_(["failed", "pending"]),
                    RouteCaseMessage.processing_expires_at <= now(),
                ),
            )
            .values(
                processing_status="processing",
                processing_token=token,
                processing_expires_at=now() + timedelta(seconds=self.claim_seconds),
                error_code=None,
            )
        )
        if changed.rowcount != 1:
            conflict("MESSAGE_IN_PROGRESS")
        self.db.refresh(existing)
        phase_goals = self._case_goals(step, case.phase)
        blocked_ids = set(
            self.db.scalars(
                select(RouteCasePhaseDecision.message_id).where(
                    RouteCasePhaseDecision.case_session_id == case.id, RouteCasePhaseDecision.safety_status == "unsafe"
                )
            )
        )
        evidence = [
            str(m.id)
            for m in messages
            if m.role == "student" and m.request_revision > case.phase_started_revision and m.id not in blocked_ids
        ]
        if str(existing.id) not in evidence:
            evidence.append(str(existing.id))
        message_phases = self._case_message_phases(case, messages)
        eligible_history = [m for m in messages if m.id not in blocked_ids and m.id != existing.id]
        # Preserve the latest student/assistant pair from each earlier stage as well as recent turns.
        anchors = []
        for phase in CASE_PHASES[: CASE_PHASES.index(case.phase)]:
            anchors.extend([m for m in eligible_history if message_phases[m.id] == phase][-2:])
        history = {m.id: m for m in [*anchors, *eligible_history[-(19 - len(anchors)) :]]}
        return {
            "execute": True,
            "token": token,
            "message_id": existing.id,
            "revision": case.revision,
            "phase": case.phase,
            "phase_started_revision": case.phase_started_revision,
            "input": {
                "phase": case.phase,
                "phase_started_revision": case.phase_started_revision,
                "current_revision": case.revision,
                "public_case_scenario": step.public_definition["public_scenario"],
                "public_case_facts": [
                    fact["text"] if isinstance(fact, dict) else fact for fact in step.public_definition["case_facts"]
                ],
                "phase_goals": [
                    {
                        "goal_id": g["goal_id"],
                        "objective": g["objective"],
                        "completion_requirements": g["completion_requirements"],
                    }
                    for g in phase_goals
                ],
                "current_student_message": {"message_id": str(existing.id), "text": content},
                "history": [
                    {
                        "role": m.role,
                        "message_id": str(m.id),
                        "text": m.content,
                        "revision": m.request_revision,
                        "phase": message_phases[m.id],
                    }
                    for m in sorted(history.values(), key=lambda m: m.sequence)
                ],
                "current_phase_evidence_message_ids": evidence[-20:],
            },
        }

    def save_case_reply(self, public_id, claim, result):
        case = self._get(RouteCaseSession, public_id)
        message = self.db.get(RouteCaseMessage, claim["message_id"])
        if (
            message.processing_token != claim["token"]
            or message.processing_status != "processing"
            or utc(message.processing_expires_at) <= now()
            or case.revision != claim["revision"]
            or case.phase != claim["phase"]
            or case.phase_started_revision != claim["phase_started_revision"]
        ):
            conflict("VERSION_CONFLICT")
        step = self.db.get(LearningRouteStep, case.step_id)
        assessment = result["phase_assessment"]
        unsafe = result["safety_status"] != "educational"
        if unsafe:
            new_phase = case.phase
            assessment = {**assessment, "decision": "stay"}
        else:
            new_phase = case_transition(
                case.phase,
                assessment,
                [g["goal_id"] for g in self._case_goals(step, case.phase)],
                set(claim["input"]["current_phase_evidence_message_ids"]),
            )
        changed = self._execute(
            update(RouteCaseMessage)
            .where(
                RouteCaseMessage.id == message.id,
                RouteCaseMessage.processing_token == claim["token"],
                RouteCaseMessage.processing_status == "processing",
                RouteCaseMessage.processing_expires_at > now(),
            )
            .values(processing_status="blocked" if unsafe else "completed", processing_expires_at=None)
        )
        if changed.rowcount != 1:
            conflict("VERSION_CONFLICT")
        self.db.add(
            RouteCasePhaseDecision(
                case_session_id=case.id,
                message_id=message.id,
                revision=case.revision,
                phase=case.phase,
                decision=assessment["decision"],
                evidence_message_ids=assessment["evidence_message_ids"] if not unsafe else [],
                satisfied_goal_codes=[g["goal_id"] for g in assessment["goal_checks"] if g["status"] == "satisfied"]
                if not unsafe
                else [],
                missing_goal_codes=assessment["missing_elements"],
                safety_status="unsafe" if unsafe else "educational",
            )
        )
        response = result["learning_response"]
        reply = (
            response
            if isinstance(response, str)
            else "\n".join([response["opening"], *response["key_points"], response["next_step"]])
        )
        self.db.add(
            RouteCaseMessage(
                case_session_id=case.id,
                sequence=message.sequence + 1,
                role="assistant",
                content=reply,
                request_revision=case.revision,
                processing_status="completed",
            )
        )
        case.status = "blocked" if unsafe else "in_progress"
        step.status = "blocked" if unsafe else "in_progress"
        if new_phase != case.phase:
            case.phase, case.phase_started_revision = new_phase, case.revision
        if new_phase == "completed":
            case.status, case.completed_at = "completed", now()
            self._complete_step(step)
        self._flush()
        self.db.refresh(message)
        return self._message_result(case, message)

    def fail_case_reply(self, public_id, claim):
        self._execute(
            update(RouteCaseMessage)
            .where(
                RouteCaseMessage.id == claim["message_id"],
                RouteCaseMessage.processing_token == claim["token"],
                RouteCaseMessage.processing_status == "processing",
            )
            .values(processing_status="failed", processing_expires_at=None, error_code="case_provider_failure")
        )

    def _notify(self, route, kind, title, body):
        key = f"{kind}:learning_route:{route.public_id}"
        if self.db.scalar(select(StudentNotification.id).where(StudentNotification.dedupe_key == key)) is None:
            self.db.add(
                StudentNotification(
                    student_id=route.student_id,
                    type=kind,
                    entity_type="learning_route",
                    entity_id=route.id,
                    entity_public_id=route.public_id,
                    title=title,
                    body=body,
                    dedupe_key=key,
                )
            )

    def _bank_payload(self, question):
        return {
            "task_type": "retest",
            "title": "病理知识单选题",
            "prompt": question.prompt,
            "options": list(question.options),
            "answer": {"correct_option": question.correct_option},
            "explanation": question.explanation,
            "point_codes": [question.primary_point_code],
            "dimension_ids": [],
        }

    def bank_source(self, teacher_id, question_id):
        question = self._get(RouteTestQuestion, question_id)
        test = self.db.get(RouteFinalTest, question.test_id)
        route = self.db.get(LearningRoute, test.route_id)
        if route.source_kind != "classroom" or route.teacher_id != teacher_id:
            raise AppError("RESOURCE_NOT_FOUND", "题目不存在", 404)
        if question.question_type != "single_choice":
            raise AppError("VALIDATION_ERROR", "仅单选题可加入当前题库", 422)
        payload = self._bank_payload(question)
        return {
            **payload,
            "source_type": "route_test_question",
            "source_id": question.public_id,
            "source_digest": digest(payload),
            "medical_status": None,
            "public_definition": {"title": payload["title"], "prompt": question.prompt, "options": question.options},
            "private_rubric": {"correct_option": question.correct_option, "explanation": question.explanation},
        }

    def teacher_test(self, test_id):
        test = self._get(RouteFinalTest, test_id)
        route = self.db.get(LearningRoute, test.route_id)
        return {
            "id": test.public_id,
            "route_id": route.public_id,
            "title": test.title,
            "source_kind": route.source_kind,
            "class_id": route.class_id,
            "session_id": route.session_id,
            "student_id": route.student_id,
            "diagnosis_summary": route.diagnosis_summary,
            "goal_point_codes": route.goal_point_codes,
            "generation_state": test.generation_state,
            "review_state": test.review_state,
            "review_kind": test.review_kind,
            "format_version": test.format_version,
            "version": test.version,
            "draft_digest": test.draft_digest or "",
            "released_at": test.released_at,
            "feedback_draft": test.feedback_draft,
            "questions": [
                {
                    "id": q.public_id,
                    "source_digest": digest(self._bank_payload(q)),
                    "position": q.position,
                    "primary_point_code": q.primary_point_code,
                    "prompt": q.prompt,
                    "question_type": q.question_type,
                    "options": q.options,
                    "correct_option": q.correct_option,
                    "correct_options": q.private_grading.get("correct_options"),
                    "reference_answer": q.private_grading.get("reference_answer"),
                    "rubric": q.private_grading.get("rubric"),
                    "explanation": q.explanation,
                }
                for q in self._questions(test)
            ],
        }

    def teacher_tests(self, teacher_id, filters):
        query = (
            select(RouteFinalTest)
            .join(LearningRoute, LearningRoute.id == RouteFinalTest.route_id)
            .where(
                LearningRoute.teacher_id == teacher_id,
                LearningRoute.source_kind == "classroom",
                LearningRoute.class_id == filters["class_id"],
            )
        )
        if filters.get("session_id"):
            query = query.where(LearningRoute.session_id == filters["session_id"])
        if filters.get("status"):
            query = query.where(RouteFinalTest.review_state == filters["status"])
        limit, offset = filters.get("limit", 20), filters.get("offset", 0)
        total = self.db.scalar(select(func.count()).select_from(query.subquery()))
        tests = self.db.scalars(
            query.order_by(RouteFinalTest.updated_at.desc(), RouteFinalTest.id.desc()).limit(limit).offset(offset)
        )
        return {
            "items": [self.teacher_test(t.public_id) for t in tests],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def teacher_review_candidates(self, teacher_id: int, filters: dict) -> list[dict]:
        # Only metadata crosses this read boundary; no questions or diagnosis.
        query = (
            select(
                RouteFinalTest.public_id,
                LearningRoute.public_id,
                RouteFinalTest.title,
                LearningRoute.class_id,
                LearningRoute.session_id,
                LearningRoute.student_id,
                RouteFinalTest.generation_state,
                RouteFinalTest.review_state,
                RouteFinalTest.updated_at,
                RouteFinalTest.generation_claim_expires_at,
            )
            .join(LearningRoute, LearningRoute.id == RouteFinalTest.route_id)
            .where(
                LearningRoute.teacher_id == teacher_id,
                LearningRoute.source_kind == "classroom",
                LearningRoute.generation_state == "published",
                RouteFinalTest.review_state != "released",
                RouteFinalTest.generation_state.in_(("ready", "generation_failed")),
            )
            .order_by(RouteFinalTest.updated_at.desc(), RouteFinalTest.id.desc())
        )
        for key, column in (("class_id", LearningRoute.class_id), ("session_id", LearningRoute.session_id)):
            if filters.get(key) is not None:
                query = query.where(column == filters[key])
        keys = (
            "id",
            "route_id",
            "title",
            "class_id",
            "session_id",
            "student_id",
            "generation_state",
            "review_state",
            "updated_at",
            "claim_expires_at",
        )
        return [dict(zip(keys, row, strict=True)) for row in self.db.execute(query)]

    def _editable(self, test, version):
        if test.review_state == "released":
            conflict("TEST_RELEASED")
        if test.generation_state != "ready":
            conflict("TEST_NOT_GENERATED")
        if test.version != version:
            conflict("VERSION_CONFLICT")

    def save_teacher_test(self, test_id, payload):
        test = self._get(RouteFinalTest, test_id)
        route = self.db.get(LearningRoute, test.route_id)
        replay = self._receipt(route.teacher_id, "teacher_save_test", payload["client_request_id"], payload, test_id)
        if replay:
            return replay.response_snapshot or self.teacher_test(test_id)
        self._editable(test, payload["expected_version"])
        questions = payload["questions"]
        validate_questions(questions, route.goal_point_codes, test.format_version)
        existing = {q.public_id: q for q in self._questions(test)}
        ids = [q["id"] for q in questions if q.get("id")]
        if (
            len(set(ids)) != len(ids)
            or not set(ids) <= set(existing)
            or [q["position"] for q in questions] != list(range(1, len(questions) + 1))
            or (test.format_version == "mixed_v2" and set(ids) != set(existing))
        ):
            raise AppError("VALIDATION_ERROR", "题目身份或顺序无效", 422)
        changed = self._execute(
            update(RouteFinalTest)
            .where(
                RouteFinalTest.id == test.id,
                RouteFinalTest.version == payload["expected_version"],
                RouteFinalTest.review_state != "released",
            )
            .values(version=test.version + 1, feedback_draft=payload.get("feedback_draft", ""))
        )
        if changed.rowcount != 1:
            conflict("VERSION_CONFLICT")
        # Move existing positions aside before reordering to respect the unique position constraint.
        for question in existing.values():
            question.position += 100
        self._flush()
        for public_id, question in existing.items():
            if public_id not in ids:
                self.db.delete(question)
        self._flush()
        for index, item in enumerate(questions, 1):
            question = existing.get(item.get("id"))
            if question is None:
                question = RouteTestQuestion(public_id=uid(), test_id=test.id, stable_key=uid())
                self.db.add(question)
            question.position = index
            question.primary_point_code = item["primary_point_code"]
            question.prompt = item["prompt"]
            question.question_type = item.get("question_type", "single_choice")
            question.options = item.get("options", [])
            question.correct_option = item.get("correct_option")
            question.explanation = item["explanation"]
            if test.format_version == "mixed_v2":
                question.private_grading = {
                    **question.private_grading,
                    "correct_options": item.get("correct_options"),
                    "reference_answer": item.get("reference_answer"),
                    "rubric": item.get("rubric"),
                }
        self._flush()
        self.db.refresh(test)
        test.draft_digest = digest(self.teacher_test(test_id)["questions"])
        self._flush()
        return self._record_response(
            route.teacher_id, "teacher_save_test", payload["client_request_id"], self.teacher_test(test_id)
        )

    def release_test(self, test_id, teacher_id, payload):
        test = self._get(RouteFinalTest, test_id)
        replay = self._receipt(teacher_id, "release_test", payload["client_request_id"], payload, test_id)
        if not replay:
            self._editable(test, payload["expected_version"])
            if test.draft_digest != payload["draft_digest"]:
                conflict("VERSION_CONFLICT")
            route = self.db.get(LearningRoute, test.route_id)
            validate_questions(self.teacher_test(test_id)["questions"], route.goal_point_codes, test.format_version)
            changed = self._execute(
                update(RouteFinalTest)
                .where(
                    RouteFinalTest.id == test.id,
                    RouteFinalTest.version == payload["expected_version"],
                    RouteFinalTest.review_state != "released",
                    RouteFinalTest.draft_digest == payload["draft_digest"],
                )
                .values(
                    review_state="released",
                    reviewer_id=teacher_id,
                    review_kind="teacher",
                    released_version=test.version,
                    released_digest=test.draft_digest,
                    released_at=now(),
                )
            )
            if changed.rowcount != 1:
                conflict("VERSION_CONFLICT")
            self.db.refresh(test)
            self.db.add(
                RouteTestReviewEvent(
                    test_id=test.id,
                    teacher_id=teacher_id,
                    action="released",
                    version=test.version,
                    digest=test.draft_digest,
                    feedback=payload.get("feedback", ""),
                )
            )
            self._notify(route, "final_test_released", "最终测试已开放", "完成学习路线后即可进行最终测试。")
            self._flush()
        return {
            "test_id": test.public_id,
            "released_version": test.released_version,
            "released_digest": test.released_digest,
            "released_at": test.released_at,
        }

    def request_changes(self, test_id, teacher_id, payload):
        test = self._get(RouteFinalTest, test_id)
        replay = self._receipt(teacher_id, "request_test_changes", payload["client_request_id"], payload, test_id)
        if not replay:
            self._editable(test, payload["expected_version"])
            test.review_state = "needs_changes"
            test.feedback_draft = payload.get("note", "")
            test.version += 1
            self.db.add(
                RouteTestReviewEvent(
                    test_id=test.id,
                    teacher_id=teacher_id,
                    action="requested_changes",
                    version=test.version,
                    digest=test.draft_digest,
                    feedback=payload.get("note", ""),
                )
            )
            self._flush()
        return self.teacher_test(test_id)

    def _published_rows(self, teacher_id, class_ids, start=None, end=None, session_id=None):
        query = (
            select(LearningRoute, RouteLearningResult, RouteFinalTest, RouteTestAttempt)
            .outerjoin(RouteLearningResult, RouteLearningResult.route_id == LearningRoute.id)
            .outerjoin(RouteFinalTest, RouteFinalTest.route_id == LearningRoute.id)
            .outerjoin(RouteTestAttempt, RouteTestAttempt.test_id == RouteFinalTest.id)
            .where(
                LearningRoute.teacher_id == teacher_id,
                LearningRoute.source_kind == "classroom",
                LearningRoute.class_id.in_(class_ids),
                LearningRoute.published_at.is_not(None),
            )
        )
        if start is not None:
            query = query.where(LearningRoute.published_at >= start)
        if end is not None:
            query = query.where(LearningRoute.published_at < end)
        if session_id is not None:
            query = query.where(LearningRoute.session_id == session_id)
        rows = list(self.db.execute(query.order_by(LearningRoute.id)))
        route_ids = tuple(route.id for route, _result, _test, _attempt in rows)
        progress = {}
        if route_ids:
            steps = self.db.execute(
                select(
                    LearningRouteStep.route_id,
                    LearningRouteStep.status,
                    LearningRouteStep.kind,
                    RouteReadingProgress.accumulated_seconds,
                )
                .outerjoin(RouteReadingProgress, RouteReadingProgress.step_id == LearningRouteStep.id)
                .where(LearningRouteStep.route_id.in_(route_ids))
            )
            for route_id, status, kind, seconds in steps:
                item = progress.setdefault(route_id, {"completed_steps": 0, "total_steps": 0, "reading_seconds": None})
                item["total_steps"] += 1
                item["completed_steps"] += status == "completed"
                if kind == "reading":
                    item["reading_seconds"] = (item["reading_seconds"] or 0) + (seconds or 0)
        return tuple(
            {
                "route_id": route.public_id,
                "student_id": route.student_id,
                "class_id": route.class_id,
                "session_id": route.session_id,
                "published_at": utc(route.published_at),
                "published": True,
                "result_id": result.public_id if result else None,
                "score": float(result.score) if result else None,
                "completed_at": utc(result.completed_at) if result else None,
                "question_count": result.question_count if result else None,
                "correct_count": result.correct_count if result else None,
                "test_generation_state": test.generation_state if test else None,
                "test_review_state": test.review_state if test else None,
                "attempt_status": attempt.status if attempt else None,
                **progress.get(route.id, {"completed_steps": 0, "total_steps": 0, "reading_seconds": None}),
            }
            for route, result, test, attempt in rows
        )

    def published_for_teacher(self, teacher_id, class_ids, start, end, session_id=None):
        return self._published_rows(teacher_id, class_ids, start, end, session_id)

    def classroom_progress_for_teacher(self, teacher_id, class_id, session_id):
        return self._published_rows(teacher_id, (class_id,), session_id=session_id)

    def completed_for_teacher(self, teacher_id, class_ids, start, end):
        query = (
            select(RouteLearningResult, LearningRoute)
            .join(LearningRoute, LearningRoute.id == RouteLearningResult.route_id)
            .where(
                RouteLearningResult.teacher_id == teacher_id,
                RouteLearningResult.source_kind == "classroom",
                RouteLearningResult.class_id.in_(class_ids),
                RouteLearningResult.completed_at >= start,
                RouteLearningResult.completed_at < end,
            )
        )
        return tuple(
            {
                "id": result.public_id,
                "result_id": result.public_id,
                "route_id": route.public_id,
                "student_id": result.student_id,
                "class_id": result.class_id,
                "session_id": route.session_id,
                "score": float(result.score),
                "completed_at": utc(result.completed_at),
                "question_count": result.question_count,
                "correct_count": result.correct_count,
                "payload": result.result_snapshot,
            }
            for result, route in self.db.execute(query.order_by(RouteLearningResult.id))
        )

    def teacher_results(self, teacher_id, filters):
        query = (
            select(RouteLearningResult)
            .join(LearningRoute, LearningRoute.id == RouteLearningResult.route_id)
            .where(
                RouteLearningResult.source_kind == "classroom",
                RouteLearningResult.teacher_id == teacher_id,
                RouteLearningResult.class_id == filters["class_id"],
            )
        )
        for key, column in (("session_id", LearningRoute.session_id), ("student_id", RouteLearningResult.student_id)):
            if filters.get(key):
                query = query.where(column == filters[key])
        if filters.get("start"):
            query = query.where(RouteLearningResult.completed_at >= filters["start"])
        if filters.get("end"):
            query = query.where(RouteLearningResult.completed_at < filters["end"])
        limit, offset = filters.get("limit", 20), filters.get("offset", 0)
        total = self.db.scalar(select(func.count()).select_from(query.subquery()))
        results = self.db.scalars(
            query.order_by(RouteLearningResult.completed_at.desc(), RouteLearningResult.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return {
            "items": [
                {
                    **r.result_snapshot,
                    "student_id": r.student_id,
                    "class_id": r.class_id,
                    "session_id": self.db.get(LearningRoute, r.route_id).session_id,
                }
                for r in results
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def teacher_result(self, teacher_id, result_id):
        result = self._get(RouteLearningResult, result_id)
        if result.source_kind != "classroom" or result.teacher_id != teacher_id:
            raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)
        return {
            **result.result_snapshot,
            "class_id": result.class_id,
            "student_id": result.student_id,
            "session_id": self.db.get(LearningRoute, result.route_id).session_id,
        }

    def claim_generation(self, route_id, component, token=None):
        route = self._get(LearningRoute, route_id)
        row = route if component == "route" else self._test(route)
        success = "published" if component == "route" else "ready"
        if row.generation_state == success:
            return {"execute": False, "token": None}
        if component == "test" and route.generation_state != "published":
            conflict("ROUTE_NOT_PUBLISHED")
        timestamp = now()
        if token:
            if row.generation_claim_token != token or utc(row.generation_claim_expires_at) <= timestamp:
                return {"execute": False, "token": token}
            conditions = [type(row).generation_claim_token == token, type(row).generation_execution_state == "queued"]
        else:
            token = uid()
            conditions = [
                or_(type(row).generation_claim_expires_at.is_(None), type(row).generation_claim_expires_at <= timestamp)
            ]
        changed = self._execute(
            update(type(row))
            .where(type(row).id == row.id, type(row).generation_state != success, *conditions)
            .values(
                generation_state="generating",
                generation_claim_token=token,
                generation_claim_expires_at=timestamp + timedelta(seconds=self.claim_seconds),
                generation_execution_state="running",
                error_code=None,
            )
        )
        if changed.rowcount != 1:
            return {"execute": False, "token": token}
        self._flush()
        return {
            "execute": True,
            "token": token,
            "format_version": row.format_version if component == "test" else None,
        }

    def queue_generation(self, route_id, component, actor_id, request_id):
        route = self._get(LearningRoute, route_id)
        row = route if component == "route" else self._test(route)
        replay = self._receipt(actor_id, "retry_" + component, request_id, {"component": component}, route_id)
        if replay:
            return {
                "route_id": route_id,
                "component": component,
                "generation_state": row.generation_state,
                "claim_expires_at": row.generation_claim_expires_at,
                "token": None,
            }
        success = "published" if component == "route" else "ready"
        if row.generation_state == success:
            conflict("ALREADY_GENERATED")
        if component == "test" and route.generation_state != "published":
            conflict("ROUTE_NOT_PUBLISHED")
        token, timestamp = uid(), now()
        changed = self._execute(
            update(type(row))
            .where(
                type(row).id == row.id,
                type(row).generation_state != success,
                or_(
                    type(row).generation_claim_expires_at.is_(None), type(row).generation_claim_expires_at <= timestamp
                ),
            )
            .values(
                generation_state="generating",
                generation_claim_token=token,
                generation_claim_expires_at=timestamp + timedelta(seconds=self.claim_seconds),
                generation_execution_state="queued",
                error_code=None,
            )
        )
        if changed.rowcount != 1:
            conflict("GENERATION_IN_PROGRESS")
        self.db.refresh(row)
        return {
            "route_id": route_id,
            "component": component,
            "generation_state": row.generation_state,
            "claim_expires_at": row.generation_claim_expires_at,
            "token": token,
        }

    def generation_input(self, route_id, component):
        route = self._get(LearningRoute, route_id)
        context = route.generation_context
        sources = {}
        for point in context["goal_points"]:
            for source in point["sources"]:
                sources[source["source_key"]] = {
                    "source_id": source["source_key"],
                    "title": source["title"],
                    "institution": source["publisher"],
                    "version": source["accessed_on"],
                    "url": source["url"],
                    "summary": next(
                        (m["reference"] for m in context["materials"] if m["point_code"] == point["code"]),
                        source["title"],
                    ),
                }
        findings = []
        for field, kind in (("knowledge_gaps", "knowledge_gap"), ("reasoning_issues", "reasoning_issue")):
            for finding in route.diagnosis_summary.get(field, []):
                findings.append(
                    {
                        "finding_id": finding["id"],
                        "kind": kind,
                        "target_code": finding.get("point_code", finding.get("dimension_id", "")),
                        "summary": finding["summary"],
                        "evidence_summary": finding.get("evidence_summary", ""),
                    }
                )
        data = {
            "source_kind": route.source_kind,
            "findings": findings,
            "goal_points": [{"code": p["code"], "title": p["title"]} for p in context["goal_points"]],
            "allowed_sources": list(sources.values()),
        }
        if component == "test":
            data["route_context"] = {
                "goal_point_codes": route.goal_point_codes,
                "reading_steps": [
                    {
                        key: s.public_definition[key]
                        for key in ("stable_key", "target_point_codes", "source_ids", "learning_points")
                    }
                    for s in self._steps(route)
                    if s.kind == "reading"
                ],
            }
        return data

    def publish_generation(self, route_id, component, claim, result):
        route = self._get(LearningRoute, route_id)
        row = route if component == "route" else self._test(route)
        timestamp = now()
        success = "published" if component == "route" else "ready"
        changed = self._execute(
            update(type(row))
            .where(
                type(row).id == row.id,
                type(row).generation_claim_token == claim["token"],
                type(row).generation_execution_state == "running",
                type(row).generation_claim_expires_at > timestamp,
            )
            .values(
                generation_state=success,
                generation_execution_state=None,
                generation_claim_expires_at=None,
                error_code=None,
            )
        )
        if changed.rowcount != 1:
            conflict("GENERATION_CLAIM_EXPIRED")
        if result.get("safety_status") != "educational":
            raise AppError("SERVICE_ERROR", "生成内容未通过安全校验", 503)
        if component == "route":
            if set(result["goal_point_codes"]) != set(route.goal_point_codes):
                raise AppError("SERVICE_ERROR", "生成目标不一致", 503)
            route.title, route.content_version, route.content_digest, route.published_at = (
                result["title"],
                1,
                digest(result),
                timestamp,
            )
            source_by_id = {s["source_id"]: s for s in self.generation_input(route_id, "route")["allowed_sources"]}
            for index, reading in enumerate(result["reading_steps"], 1):
                self.db.add(
                    LearningRouteStep(
                        public_id=uid(),
                        route_id=route.id,
                        position=index,
                        kind="reading",
                        title=reading.get("title", "资料学习 " + str(index)),
                        goal_point_codes=reading["target_point_codes"],
                        source_snapshot={"sources": [source_by_id[source_id] for source_id in reading["source_ids"]]},
                        public_definition=reading,
                        private_definition={},
                        status="available" if index == 1 else "locked",
                    )
                )
            self._notify(route, "learning_route_ready", "学习计划已生成", "请按顺序完成资料与病例学习。")
            case = result["synthetic_case"]
            step = LearningRouteStep(
                public_id=uid(),
                route_id=route.id,
                position=len(result["reading_steps"]) + 1,
                kind="case",
                title=case["title"],
                goal_point_codes=case["target_point_codes"],
                public_definition={
                    key: case[key] for key in ("title", "public_scenario", "case_facts", "target_point_codes")
                },
                private_definition={"phases": case["phases"]},
                source_snapshot={},
                status="locked",
            )
            self.db.add(step)
            self._flush()
            self.db.add(
                RouteCaseSession(
                    public_id=uid(),
                    step_id=step.id,
                    student_id=route.student_id,
                    phase=CASE_PHASES[0],
                    revision=0,
                    phase_started_revision=0,
                    status="in_progress",
                )
            )
        else:
            test = row
            validate_questions(result["questions"], route.goal_point_codes, test.format_version)
            for index, question in enumerate(result["questions"], 1):
                self.db.add(
                    RouteTestQuestion(
                        public_id=uid(),
                        test_id=test.id,
                        stable_key=question["stable_key"],
                        position=index,
                        primary_point_code=question["primary_point_code"],
                        prompt=question["prompt"],
                        question_type=question.get("question_type", "single_choice"),
                        options=question.get("options", []),
                        correct_option=question.get("correct_option"),
                        explanation=question["explanation"],
                        private_grading={
                            "source_ids": question["source_ids"],
                            "linked_findings": question["linked_findings"],
                            **(
                                {
                                    "correct_options": question.get("correct_options"),
                                    "reference_answer": question.get("reference_answer"),
                                    "rubric": question.get("rubric"),
                                }
                                if test.format_version == "mixed_v2"
                                else {}
                            ),
                        },
                    )
                )
            self._flush()
            self.db.refresh(test)
            test.draft_digest = digest(self.teacher_test(test.public_id)["questions"])
            if route.source_kind == "autonomous":
                test.review_state, test.review_kind = "released", "ai_direct"
                test.released_version, test.released_digest, test.released_at = (
                    test.version,
                    test.draft_digest,
                    timestamp,
                )
        if component == "test" and route.source_kind == "autonomous":
            self._notify(route, "final_test_released", "最终测试已开放", "AI生成测试未经教师审阅，完成路线后可开始。")
        route.updated_at = timestamp
        self._flush()

    def fail_generation(self, route_id, component, claim):
        route = self._get(LearningRoute, route_id)
        row = route if component == "route" else self._test(route)
        self._execute(
            update(type(row))
            .where(
                type(row).id == row.id,
                type(row).generation_claim_token == claim["token"],
                type(row).generation_state == "generating",
            )
            .values(
                generation_state="generation_failed",
                generation_execution_state=None,
                generation_claim_expires_at=None,
                error_code="provider_contract_failure",
            )
        )

    def evidence_points(self, command):
        result = self._get(RouteLearningResult, command.source_id)
        private = result.source_kind == "autonomous"
        if (
            command.student_id != result.student_id
            or command.class_id != result.class_id
            or command.source_type != ("private_final_test" if private else "classroom_final_test")
            or command.source_version != 1
            or command.event_kind != "assessment"
            or utc(command.occurred_at) != utc(result.completed_at)
            or command.dedupe_key != f"final-test-result:{result.public_id}:v1"
        ):
            raise AppError("VALIDATION_ERROR", "最终测试证据来源无效", 422)
        return set(result.result_snapshot["goal_point_codes"])
