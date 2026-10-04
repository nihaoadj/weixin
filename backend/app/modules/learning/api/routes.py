from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response
from sqlalchemy.orm import Session

from app.bootstrap.composition import (
    learning_route_application,
    learning_route_generation_dispatch,
    student_learning_insights_application,
)
from app.db import get_db
from app.dependencies import require_student, require_teacher
from app.modules.learning.api.route_schemas import (
    AttemptRead,
    CaseCommand,
    CaseMessageResult,
    CaseRead,
    Command,
    DraftCommand,
    GradingStatus,
    LearningResult,
    ReadingCommand,
    ReadingProgress,
    ReadingStep,
    ReleaseCommand,
    ReleaseReceipt,
    RetryCommand,
    RetryReceipt,
    ReviewCommand,
    RouteDetail,
    RoutePage,
    StudentInsightPage,
    StudentTest,
    SubmitCommand,
    TeacherLearningResult,
    TeacherResultPage,
    TeacherReviewQueuePage,
    TeacherSave,
    TeacherTest,
    TeacherTestPage,
    TutorCommand,
    TutorRead,
)

router = APIRouter(tags=["learning-routes"])


@router.get("/learning/student-insights", response_model=StudentInsightPage)
def student_insights(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    student=Depends(require_student),
    db: Session = Depends(get_db),
):
    return student_learning_insights_application(db).read(student.id, limit, offset)


@router.get("/learning/routes", response_model=RoutePage)
def routes(
    status: Literal["active", "completed"] = "active",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    student=Depends(require_student),
    db: Session = Depends(get_db),
):
    return learning_route_application(db).routes(student.id, status, limit, offset)


@router.get("/learning/routes/{route_id}", response_model=RouteDetail)
def detail(route_id: UUID, student=Depends(require_student), db: Session = Depends(get_db)):
    return learning_route_application(db).detail(student.id, str(route_id))


def _retry(db, background_tasks, actor_id, route_id, payload, teacher=False):
    receipt = learning_route_application(db).retry(actor_id, route_id, payload, teacher=teacher)
    token = receipt.pop("token")
    if token:
        dispatch = learning_route_generation_dispatch(db)
        background_tasks.add_task(dispatch.generate, route_id, receipt["component"], token)
    return receipt


@router.post("/learning/routes/{route_id}/retry-generation", response_model=RetryReceipt, status_code=202)
def retry(
    route_id: UUID,
    payload: RetryCommand,
    background_tasks: BackgroundTasks,
    student=Depends(require_student),
    db: Session = Depends(get_db),
):
    return _retry(db, background_tasks, student.id, str(route_id), payload.model_dump())


@router.get("/learning/route-steps/{step_id}", response_model=ReadingStep)
def step(step_id: UUID, student=Depends(require_student), db: Session = Depends(get_db)):
    return learning_route_application(db).step(student.id, str(step_id))


@router.post("/learning/route-steps/{step_id}/reading-progress", response_model=ReadingProgress)
def progress(step_id: UUID, payload: ReadingCommand, student=Depends(require_student), db: Session = Depends(get_db)):
    return learning_route_application(db).reading_progress(student.id, str(step_id), payload.model_dump())


@router.post("/learning/route-steps/{step_id}/complete-reading", response_model=RouteDetail)
def complete_reading(step_id: UUID, payload: Command, student=Depends(require_student), db: Session = Depends(get_db)):
    return learning_route_application(db).complete_reading(student.id, str(step_id), payload.model_dump())


@router.get("/learning/route-cases/{case_id}", response_model=CaseRead)
def case(case_id: UUID, student=Depends(require_student), db: Session = Depends(get_db)):
    return learning_route_application(db).case(student.id, str(case_id))


@router.post("/learning/route-cases/{case_id}/messages", response_model=CaseMessageResult)
def message(
    case_id: UUID,
    payload: CaseCommand,
    response: Response,
    student=Depends(require_student),
    db: Session = Depends(get_db),
):
    result = learning_route_application(db).message(student.id, str(case_id), payload.model_dump())
    if result["processing_state"] == "processing":
        response.status_code = 202
    return result


@router.post("/learning/final-tests/{test_id}/start", response_model=StudentTest)
def start_test(test_id: UUID, payload: Command, student=Depends(require_student), db: Session = Depends(get_db)):
    return learning_route_application(db).start(student.id, str(test_id), payload.model_dump())


@router.get("/learning/routes/{route_id}/final-test", response_model=StudentTest)
def final_test(route_id: UUID, student=Depends(require_student), db: Session = Depends(get_db)):
    return learning_route_application(db).test(student.id, str(route_id))


@router.put("/learning/final-tests/{test_id}/draft", response_model=AttemptRead)
def draft(test_id: UUID, payload: DraftCommand, student=Depends(require_student), db: Session = Depends(get_db)):
    return learning_route_application(db).draft(student.id, str(test_id), payload.model_dump())


@router.post("/learning/final-tests/{test_id}/submit", response_model=LearningResult | GradingStatus)
def submit(
    test_id: UUID,
    payload: SubmitCommand,
    background_tasks: BackgroundTasks,
    student=Depends(require_student),
    db: Session = Depends(get_db),
):
    result = learning_route_application(db).submit(student.id, str(test_id), payload.model_dump())
    if result.get("status") == "grading" and result["retry_allowed"]:
        background_tasks.add_task(learning_route_generation_dispatch(db).grade, str(test_id))
    return result


@router.get("/learning/final-tests/{test_id}/grading", response_model=GradingStatus)
def grading_status(test_id: UUID, student=Depends(require_student), db: Session = Depends(get_db)):
    return learning_route_application(db).grading_status(student.id, str(test_id))


@router.post("/learning/final-tests/{test_id}/retry-grading", response_model=GradingStatus, status_code=202)
def retry_grading(
    test_id: UUID,
    payload: Command,
    background_tasks: BackgroundTasks,
    student=Depends(require_student),
    db: Session = Depends(get_db),
):
    _ = payload.client_request_id
    result = learning_route_application(db).grading_status(student.id, str(test_id))
    if result["status"] == "grading" and result["retry_allowed"]:
        background_tasks.add_task(learning_route_generation_dispatch(db).grade, str(test_id))
    return result


@router.get("/learning/routes/{route_id}/result", response_model=LearningResult)
def result(route_id: UUID, student=Depends(require_student), db: Session = Depends(get_db)):
    return learning_route_application(db).result(student.id, str(route_id))


@router.get("/learning/results/{result_id}/tutor", response_model=TutorRead)
def tutor(result_id: UUID, student=Depends(require_student), db: Session = Depends(get_db)):
    return learning_route_application(db).tutor(student.id, str(result_id))


@router.post("/learning/results/{result_id}/tutor/messages", response_model=TutorRead)
def tutor_message(
    result_id: UUID,
    payload: TutorCommand,
    student=Depends(require_student),
    db: Session = Depends(get_db),
):
    return learning_route_application(db).tutor_message(
        student.id, str(result_id), {**payload.model_dump(), "question_id": str(payload.question_id)}
    )


@router.get("/learning/teacher/final-test-review-queue", response_model=TeacherReviewQueuePage)
def teacher_review_queue(
    class_id: int | None = Query(default=None, gt=0),
    session_id: int | None = Query(default=None, gt=0),
    kind: Literal["pending_review", "needs_changes", "generation_failed"] | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    teacher=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return learning_route_application(db).teacher_review_queue(
        teacher.id, {"class_id": class_id, "session_id": session_id, "kind": kind, "limit": limit, "offset": offset}
    )


@router.get("/learning/teacher/final-tests", response_model=TeacherTestPage)
def teacher_tests(
    class_id: int = Query(gt=0),
    session_id: int | None = Query(None, gt=0),
    status: Literal["pending_review", "needs_changes", "released"] | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    teacher=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return learning_route_application(db).teacher_tests(
        teacher.id, {"class_id": class_id, "session_id": session_id, "status": status, "limit": limit, "offset": offset}
    )


@router.get("/learning/teacher/final-tests/{test_id}", response_model=TeacherTest)
def teacher_test(test_id: UUID, teacher=Depends(require_teacher), db: Session = Depends(get_db)):
    return learning_route_application(db).teacher_test(teacher.id, str(test_id))


@router.put("/learning/teacher/final-tests/{test_id}", response_model=TeacherTest)
def teacher_save(test_id: UUID, payload: TeacherSave, teacher=Depends(require_teacher), db: Session = Depends(get_db)):
    return learning_route_application(db).teacher_mutation(
        teacher.id, str(test_id), "save", payload.model_dump(mode="json")
    )


@router.post("/learning/teacher/final-tests/{test_id}/request-changes", response_model=TeacherTest)
def teacher_changes(
    test_id: UUID, payload: ReviewCommand, teacher=Depends(require_teacher), db: Session = Depends(get_db)
):
    return learning_route_application(db).teacher_mutation(teacher.id, str(test_id), "changes", payload.model_dump())


@router.post("/learning/teacher/final-tests/{test_id}/release", response_model=ReleaseReceipt)
def teacher_release(
    test_id: UUID, payload: ReleaseCommand, teacher=Depends(require_teacher), db: Session = Depends(get_db)
):
    return learning_route_application(db).teacher_mutation(teacher.id, str(test_id), "release", payload.model_dump())


@router.post("/learning/teacher/final-tests/{test_id}/retry-generation", response_model=RetryReceipt, status_code=202)
def teacher_retry(
    test_id: UUID,
    payload: Command,
    background_tasks: BackgroundTasks,
    teacher=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    app = learning_route_application(db)
    test = app.teacher_test(teacher.id, str(test_id))
    return _retry(
        db, background_tasks, teacher.id, test["route_id"], {**payload.model_dump(), "component": "test"}, True
    )


@router.get("/learning/teacher/route-results", response_model=TeacherResultPage)
def teacher_results(
    class_id: int = Query(gt=0),
    session_id: int | None = Query(None, gt=0),
    student_id: int | None = Query(None, gt=0),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    teacher=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    filters = {
        "class_id": class_id,
        "session_id": session_id,
        "student_id": student_id,
        "limit": limit,
        "offset": offset,
    }
    if date_from and date_to and date_from > date_to:
        from app.shared.errors import AppError

        raise AppError("INVALID_DATE_RANGE", "日期范围无效", 422)
    if date_from:
        filters["start"] = datetime.combine(date_from, time.min, ZoneInfo("Asia/Shanghai")).astimezone(UTC)
    if date_to:
        filters["end"] = datetime.combine(date_to + timedelta(days=1), time.min, ZoneInfo("Asia/Shanghai")).astimezone(
            UTC
        )
    return learning_route_application(db).teacher_results(teacher.id, filters)


@router.get("/learning/teacher/route-results/{result_id}", response_model=TeacherLearningResult)
def teacher_result(result_id: UUID, teacher=Depends(require_teacher), db: Session = Depends(get_db)):
    return learning_route_application(db).teacher_result(teacher.id, str(result_id))
