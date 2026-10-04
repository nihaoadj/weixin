"""Application orchestration over persistence, catalog, inference and evidence ports."""

import logging
from datetime import UTC, datetime

from app.modules.learning.application.route_ports import LearningRouteInferencePort, LearningRouteStore
from app.modules.learning.domain.learning_routes import conflict, percentage
from app.modules.learning.public import LearningEvidenceCommand, LearningEvidenceMetricCommand
from app.shared.errors import AppError

logger = logging.getLogger(__name__)


class LearningRouteApplication:
    def __init__(self, store: LearningRouteStore, uow, catalog, classroom_scope, inference, evidence):
        self.store = store
        self.uow = uow
        self.catalog = catalog
        self.scope = classroom_scope
        self.inference: LearningRouteInferencePort = inference
        self.evidence = evidence

    def ensure_shell(self, context: dict) -> dict:
        if not self.catalog.contains_points(tuple(context["goal_point_codes"])):
            raise AppError("VALIDATION_ERROR", "学习目标无效", 422)
        context = {
            **context,
            "materials": [self.catalog.study_material_view(code) for code in context["goal_point_codes"]],
            "goal_points": [self.catalog.point_view(code) for code in context["goal_point_codes"]],
        }
        if any(x is None for x in context["materials"]):
            raise AppError("SERVICE_ERROR", "学习资料暂不可用", 503)
        return self.store.ensure_shell(context)

    def review_locator(self, teacher_id: int, participation_id: int) -> dict | None:
        return self.store.review_locator(teacher_id, participation_id)

    def classroom_progress(self, teacher_id: int, class_id: int, session_id: int) -> list[dict]:
        if self.scope.owned(teacher_id, class_id) is None:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        return self.store.classroom_progress(teacher_id, class_id, session_id)

    def _own_route(self, student_id: int, route_id: str):
        route = self.store.route(route_id)
        if route is None or route["student_id"] != student_id:
            raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)
        return route

    def _own_step(self, student_id: int, step_id: str):
        step = self.store.step(step_id)
        if step is None:
            raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)
        self._own_route(student_id, step["route_id"])
        if step["status"] == "locked":
            conflict("STEP_LOCKED")
        return step

    def _scope_summary(self, summary):
        route = self.store.route(summary["id"])
        inactive = route["source_kind"] == "classroom" and (
            self.scope.owned_active(route["teacher_id"], route["class_id"]) is None
            or not self.scope.active_member(route["student_id"], route["class_id"])
        )
        summary["scope_status"] = "inactive" if inactive else "active"
        if inactive and summary["test_summary"]["review_state"] != "released":
            summary["retry_allowed"] = False
            summary["test_summary"]["retry_allowed"] = False
            summary["test_summary"]["lock_reason"] = "CLASSROOM_SCOPE_INACTIVE"
            if summary["status"] in {"waiting_teacher", "waiting_test_generation"}:
                summary["next_action"] = "contact_teacher"
        return summary

    def routes(self, student_id, status="active", limit=20, offset=0):
        page = self.store.list_routes(student_id, status, limit, offset)
        page["items"] = [self._scope_summary(row) for row in page["items"]]
        return page

    def detail(self, student_id, route_id):
        self._own_route(student_id, route_id)
        detail = self.store.detail(route_id)
        detail["summary"] = self._scope_summary(detail["summary"])
        detail["test_summary"] = detail["summary"]["test_summary"]
        return detail

    def step(self, student_id, step_id):
        return self._own_step(student_id, step_id)

    def reading_progress(self, student_id, step_id, payload):
        self._own_step(student_id, step_id)
        result = self.store.reading_progress(
            step_id, payload["action"], payload.get("lease_token"), payload["client_request_id"]
        )
        self.uow.commit()
        return result

    def complete_reading(self, student_id, step_id, payload):
        self._own_step(student_id, step_id)
        result = self.store.complete_reading(step_id, payload["client_request_id"])
        self.uow.commit()
        return result

    def case(self, student_id, case_id):
        case = self.store.case(case_id)
        if case is None:
            raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)
        self._own_step(student_id, case["step_id"])
        return case

    def message(self, student_id, case_id, payload):
        self.case(student_id, case_id)
        claim = self.store.claim_case_message(
            case_id, payload["client_message_id"], payload["content"], payload["expected_revision"]
        )
        self.uow.commit()
        if not claim.get("execute"):
            return claim["response"]
        try:
            envelope = self.inference.execute_task("route_case_turn", claim["token"], claim["input"])
            result = self.store.save_case_reply(case_id, claim, envelope["result"])
            self.uow.commit()
            return result
        except Exception as exc:
            logger.warning("route case failure type=%s", type(exc).__name__)
            self.uow.rollback()
            self.store.fail_case_reply(case_id, claim)
            self.uow.commit()
            raise AppError("SERVICE_ERROR", "病例回复暂不可用，可重试原消息", 503) from None

    def _own_test(self, student_id, test_id):
        test = self.store.test(test_id)
        if test is None:
            raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)
        self._own_route(student_id, test["route_id"])
        return test

    def start(self, student_id, test_id, payload):
        self._own_test(student_id, test_id)
        result = self.store.start_test(test_id, payload["client_request_id"])
        self.uow.commit()
        return result

    def test(self, student_id, route_id):
        self._own_route(student_id, route_id)
        return self.store.student_test(route_id)

    def draft(self, student_id, test_id, payload):
        self._own_test(student_id, test_id)
        result = self.store.save_draft(test_id, payload)
        self.uow.commit()
        return result

    def submit(self, student_id, test_id, payload):
        self._own_test(student_id, test_id)
        submission = self.store.prepare_submission(test_id, payload)
        if submission.get("grading"):
            self.uow.commit()
            return self.store.grading_status(test_id)
        if not submission["created"]:
            return submission["result"]
        result, route, metrics = submission["result"], submission["route"], submission["metrics"]
        private = route["source_kind"] == "autonomous"
        self.evidence.append(
            LearningEvidenceCommand(
                student_id=student_id,
                class_id=None if private else route["class_id"],
                source_type="private_final_test" if private else "classroom_final_test",
                source_id=result["id"],
                source_version=1,
                authority_level="personal_unverified" if private else "pbl_formal",
                visibility_scope="student_only" if private else "class_detail",
                event_kind="assessment",
                occurred_at=submission["occurred_at"],
                dedupe_key=f"final-test-result:{result['id']}:v1",
                metrics=tuple(
                    LearningEvidenceMetricCommand(
                        "knowledge",
                        code,
                        normalized_score=percentage(correct, count),
                        result="observed",
                        evidence_present=True,
                    )
                    for code, correct, count in metrics
                ),
            )
        )
        self.uow.commit()
        return result

    def grading_status(self, student_id, test_id):
        self._own_test(student_id, test_id)
        return self.store.grading_status(test_id)

    def grade(self, test_id):
        claim = self.store.claim_grading(test_id)
        self.uow.commit()
        if not claim["execute"]:
            return
        try:
            self.uow.rollback()
            envelope = self.inference.execute_task("short_answer_grading", claim["token"], claim["input"])
            completed = self.store.finish_grading(test_id, claim, envelope["result"])
            result, route = completed["result"], completed["route"]
            private = route["source_kind"] == "autonomous"
            self.evidence.append(
                LearningEvidenceCommand(
                    student_id=route["student_id"],
                    class_id=None if private else route["class_id"],
                    source_type="private_final_test" if private else "classroom_final_test",
                    source_id=result["id"],
                    source_version=1,
                    authority_level="personal_unverified" if private else "pbl_formal",
                    visibility_scope="student_only" if private else "class_detail",
                    event_kind="assessment",
                    occurred_at=completed["occurred_at"],
                    dedupe_key=f"final-test-result:{result['id']}:v1",
                    metrics=(
                        LearningEvidenceMetricCommand(
                            "knowledge",
                            route["goal_point_codes"][0],
                            normalized_score=float(completed["score"]),
                            result="observed",
                            evidence_present=True,
                        ),
                    ),
                )
            )
            self.uow.commit()
        except Exception as exc:
            logger.warning("route test grading failure type=%s", type(exc).__name__)
            self.uow.rollback()
            self.store.fail_grading(test_id, claim)
            self.uow.commit()

    def result(self, student_id, route_id):
        self._own_route(student_id, route_id)
        result = self.store.result(route_id)
        if result is None:
            raise AppError("RESOURCE_NOT_FOUND", "尚无学习结果", 404)
        return result

    def _own_result(self, student_id, result_id):
        locator = self.store.result_locator(result_id)
        if locator is None or locator["student_id"] != student_id:
            raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)
        self._own_route(student_id, locator["route_id"])
        return locator

    def tutor(self, student_id, result_id):
        self._own_result(student_id, result_id)
        return self.store.tutor_read(result_id)

    def tutor_message(self, student_id, result_id, payload):
        self._own_result(student_id, result_id)
        claim = self.store.claim_tutor_message(result_id, payload)
        self.uow.commit()
        if not claim["execute"]:
            return claim["response"]
        try:
            self.uow.rollback()
            envelope = self.inference.execute_task("test_result_tutor", claim["token"], claim["input"])
            result = self.store.save_tutor_reply(result_id, claim, envelope["result"])
            self.uow.commit()
            return result
        except Exception as exc:
            logger.warning("route test tutor failure type=%s", type(exc).__name__)
            self.uow.rollback()
            self.store.fail_tutor_reply(result_id, claim)
            self.uow.commit()
            raise AppError("SERVICE_ERROR", "导学回复暂不可用，可重试原消息", 503) from None

    def _teacher(self, teacher_id, test_id, *, active=False):
        test = self.store.test(test_id)
        if test is None:
            raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)
        route = self.store.route(test["route_id"])
        if (
            route["source_kind"] != "classroom"
            or route["teacher_id"] != teacher_id
            or self.scope.owned(teacher_id, route["class_id"]) is None
        ):
            raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)
        if active and (
            self.scope.owned_active(teacher_id, route["class_id"]) is None
            or not self.scope.active_member(route["student_id"], route["class_id"])
        ):
            conflict("CLASSROOM_SCOPE_INACTIVE")
        return test

    def _teacher_test_scope_projection(self, teacher_id: int, test: dict) -> dict:
        current_scope_active = test["source_kind"] == "classroom" and (
            self.scope.owned_active(teacher_id, test["class_id"]) is not None
            and self.scope.active_member(test["student_id"], test["class_id"])
        )
        return {**test, "current_scope_active": current_scope_active}

    def teacher_tests(self, teacher_id, filters):
        if self.scope.owned(teacher_id, filters["class_id"]) is None:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        page = self.store.teacher_tests(teacher_id, filters)
        return {
            **page,
            "items": [self._teacher_test_scope_projection(teacher_id, item) for item in page["items"]],
        }

    def teacher_review_queue(self, teacher_id: int, filters: dict) -> dict:
        class_id = filters.get("class_id")
        if class_id is not None and self.scope.owned(teacher_id, class_id) is None:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        members = {
            (member.class_id, member.student_id): member
            for member in self.scope.teaching_members(teacher_id)
            if member.class_status == "active"
        }
        timestamp = datetime.now(UTC)
        counts = {"pending_review": 0, "needs_changes": 0, "generation_failed": 0}
        items = []
        for candidate in self.store.teacher_review_candidates(teacher_id, filters):
            member = members.get((candidate["class_id"], candidate["student_id"]))
            if member is None:
                continue
            generation = candidate["generation_state"]
            review = candidate["review_state"]
            expiry = candidate["claim_expires_at"]
            if expiry is not None and expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
            can_review = generation == "ready" and review in {"pending_review", "needs_changes"}
            can_retry = generation == "generation_failed" and (expiry is None or expiry <= timestamp)
            if not can_review and not can_retry:
                continue
            kind = "generation_failed" if can_retry else review
            counts[kind] += 1
            if filters.get("kind") is not None and filters["kind"] != kind:
                continue
            items.append(
                {
                    **{key: value for key, value in candidate.items() if key != "claim_expires_at"},
                    "class_name": member.class_name,
                    "student_name": member.student_name,
                    "can_review": can_review,
                    "can_retry": can_retry,
                    "action_reason": "GENERATION_FAILED" if can_retry else "REVIEW_READY",
                }
            )
        limit, offset = filters.get("limit", 20), filters.get("offset", 0)
        return {
            "items": items[offset : offset + limit],
            "counts": counts,
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "as_of": timestamp,
        }

    def teacher_test(self, teacher_id, test_id):
        self._teacher(teacher_id, test_id)
        return self._teacher_test_scope_projection(teacher_id, self.store.teacher_test(test_id))

    def teacher_mutation(self, teacher_id, test_id, operation, payload):
        self._teacher(teacher_id, test_id, active=True)
        if operation == "save":
            result = self.store.save_teacher_test(test_id, payload)
        elif operation == "release":
            result = self.store.release_test(test_id, teacher_id, payload)
        else:
            result = self.store.request_changes(test_id, teacher_id, payload)
        self.uow.commit()
        if operation == "release":
            return result
        return self._teacher_test_scope_projection(teacher_id, result)

    def teacher_results(self, teacher_id, filters):
        if self.scope.owned(teacher_id, filters["class_id"]) is None:
            raise AppError("RESOURCE_NOT_FOUND", "班级不存在", 404)
        return self.store.teacher_results(teacher_id, filters)

    def teacher_result(self, teacher_id, result_id):
        result = self.store.teacher_result(teacher_id, result_id)
        if self.scope.owned(teacher_id, result["class_id"]) is None:
            raise AppError("RESOURCE_NOT_FOUND", "资源不存在", 404)
        return result

    def retry(self, actor_id, route_id, payload, *, teacher=False):
        if teacher:
            test_id = self.store.detail(route_id)["test_summary"]["id"]
            self._teacher(actor_id, test_id, active=True)
            if payload["component"] != "test":
                conflict("INVALID_COMPONENT")
        else:
            route = self._own_route(actor_id, route_id)
            if route["source_kind"] == "classroom":
                # Generation mutations require an active classroom and current membership.
                if self.scope.owned_active(
                    route["teacher_id"], route["class_id"]
                ) is None or not self.scope.active_member(actor_id, route["class_id"]):
                    conflict("CLASSROOM_SCOPE_INACTIVE")
        result = self.store.queue_generation(route_id, payload["component"], actor_id, payload["client_request_id"])
        self.uow.commit()
        return result

    def generate(self, route_id, component="route", token=None):
        claim = self.store.claim_generation(route_id, component, token)
        self.uow.commit()
        if not claim["execute"]:
            return
        try:
            input_payload = self.store.generation_input(route_id, component)
            self.uow.rollback()  # release read transaction before calling the provider
            envelope = self.inference.execute_task(
                "learning_route_generation"
                if component == "route"
                else "mixed_final_test_generation"
                if claim["format_version"] == "mixed_v2"
                else "final_test_generation",
                claim["token"],
                input_payload,
            )
            self.store.publish_generation(route_id, component, claim, envelope["result"])
            self.uow.commit()
        except Exception as exc:
            logger.warning("route generation failure component=%s type=%s", component, type(exc).__name__)
            self.uow.rollback()
            self.store.fail_generation(route_id, component, claim)
            self.uow.commit()
            return
        if component == "route":
            self.generate(route_id, "test")
