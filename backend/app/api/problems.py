from copy import deepcopy
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.dependencies import get_current_user, require_student, require_teacher
from app.models import (
    CaseAttempt,
    CaseAttemptMessage,
    MedicalReview,
    Problem,
    QuestionThread,
    QuestionThreadMessage,
    StageSubmission,
    User,
)
from app.schemas import (
    ProblemAuthoringRead,
    ProblemCreate,
    ProblemRead,
    ProblemUpdate,
    QuestionThreadRead,
    QuestionThreadUpsert,
)
from app.schemas.case_training import CaseDraftGenerateRequest, CaseDraftGenerateResponse
from app.services.access_control import is_problem_visible_to_student, student_class_codes, student_problem_filter
from app.services.case_ai import generate_draft

router = APIRouter(prefix="/problems", tags=["problems"])


def serialize_problem(problem: Problem, answer_count: int = 0, public_for_student: bool = False) -> dict:
    return {
        "id": problem.id,
        "type": problem.type,
        "title": problem.title,
        "description": problem.description,
        "target": problem.target,
        "target_label": "已分配学习内容" if public_for_student and problem.target != "all" else problem.target_label,
        "target_ids": [] if public_for_student else [item for item in problem.target_ids.split(",") if item],
        "status": problem.status,
        "created_at": problem.created_at,
        "published_at": problem.published_at,
        "answer_count": answer_count,
        "content_type": problem.content_type or "question",
        "slug": problem.slug,
        "specialty": problem.specialty or "",
        "difficulty": problem.difficulty or "basic",
        "estimated_minutes": problem.estimated_minutes or 10,
        "version": problem.version or 1,
        "parent_problem_id": problem.parent_problem_id,
        "author_id": None if public_for_student else problem.author_id,
        "medical_review_status": (
            "approved"
            if public_for_student and problem.content_type == "guided_case"
            else problem.medical_review_status
        ),
        "capability_tags": [] if public_for_student else problem.capability_tags or [],
        "case_definition": None,
        "rubric": None,
        "opening": (problem.case_definition or {}).get("opening") if problem.content_type == "guided_case" else None,
    }


def serialize_authoring_problem(problem: Problem, answer_count: int = 0) -> dict:
    data = serialize_problem(problem, answer_count)
    data["case_definition"] = problem.case_definition
    data["rubric"] = problem.rubric
    return data


def answer_counts(db: Session, problem_ids: list[int] | None = None) -> dict[int, int]:
    if problem_ids == []:
        return {}
    question_statement = select(QuestionThread.problem_id, func.count(QuestionThread.id)).group_by(
        QuestionThread.problem_id
    )
    guided_statement = select(
        CaseAttempt.problem_id, func.count(func.distinct(CaseAttempt.id))
    ).where(
        or_(
            exists().where(CaseAttemptMessage.attempt_id == CaseAttempt.id),
            exists().where(StageSubmission.attempt_id == CaseAttempt.id),
        )
    )
    if problem_ids is not None:
        question_statement = question_statement.where(QuestionThread.problem_id.in_(problem_ids))
        guided_statement = guided_statement.where(CaseAttempt.problem_id.in_(problem_ids))
    rows = db.execute(question_statement).all()
    counts = {problem_id: count for problem_id, count in rows}
    guided_rows = db.execute(guided_statement.group_by(CaseAttempt.problem_id)).all()
    counts.update({problem_id: count for problem_id, count in guided_rows})
    return counts


@router.get("", response_model=list[ProblemRead])
def list_problems(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    statement = select(Problem).order_by(Problem.created_at.desc())
    if user.role == "student":
        statement = statement.where(student_problem_filter(user, student_class_codes(db, user)))
    problems = list(db.scalars(statement).all())
    problems.sort(key=lambda item: (0 if item.slug == "cap-undergraduate-showcase" else 1, -(item.id or 0)))
    counts = answer_counts(db, [problem.id for problem in problems if problem.id is not None])
    return [
        serialize_problem(problem, counts.get(problem.id, 0), public_for_student=user.role == "student")
        for problem in problems
    ]


@router.post("/case-drafts/generate", response_model=CaseDraftGenerateResponse)
def generate_case_draft(
    payload: CaseDraftGenerateRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    return generate_draft(db, payload.topic, payload.learner_level, payload.learning_objectives, teacher.id)


@router.get("/{problem_id}/authoring", response_model=ProblemAuthoringRead)
def get_problem_authoring(
    problem_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    problem = db.get(Problem, problem_id)
    if problem is None or problem.content_type != "guided_case" or problem.author_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESOURCE_NOT_FOUND")
    return serialize_authoring_problem(problem, answer_counts(db, [problem.id]).get(problem.id, 0))


@router.get("/{problem_id}", response_model=ProblemRead)
def get_problem(
    problem_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    problem = db.get(Problem, problem_id)
    if problem is None or (user.role == "student" and not is_problem_visible_to_student(problem, user, db)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")
    return serialize_problem(
        problem,
        answer_counts(db, [problem.id]).get(problem.id, 0),
        public_for_student=user.role == "student",
    )


@router.post("", response_model=ProblemRead)
def create_problem(
    payload: ProblemCreate,
    _teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    case_definition = payload.case_definition.model_dump(mode="json") if payload.case_definition else None
    if case_definition and case_definition.get("schema_version") == 1:
        case_definition["schema_version"] = 2
    problem = Problem(
        type=payload.type,
        title=payload.title,
        description=payload.description,
        target=payload.target,
        target_label=payload.target_label,
        target_ids=",".join(payload.target_ids),
        status="draft",
        content_type=payload.content_type,
        slug=payload.slug,
        specialty=payload.specialty,
        difficulty=payload.difficulty,
        estimated_minutes=payload.estimated_minutes,
        version=payload.version,
        parent_problem_id=payload.parent_problem_id,
        case_definition=case_definition,
        rubric=payload.rubric.model_dump(mode="json") if payload.rubric else None,
        capability_tags=payload.capability_tags,
        author_id=_teacher.id if payload.content_type == "guided_case" else None,
        medical_review_status="not_submitted",
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return serialize_problem(problem)


@router.put("/{problem_id}", response_model=ProblemRead)
def update_problem(
    problem_id: int,
    payload: ProblemUpdate,
    _teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")
    if problem.content_type != payload.content_type:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Content type is immutable")
    if problem.content_type == "guided_case" and problem.author_id not in (None, _teacher.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESOURCE_NOT_FOUND")
    if problem.content_type == "guided_case" and problem.medical_review_status == "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="STATE_CONFLICT")
    if problem.status == "published" and problem.content_type == "guided_case":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Published case is immutable; clone a new version"
        )
    if problem.content_type == "guided_case" and problem.medical_review_status == "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Approved case is immutable; clone a new version"
        )
    problem.type = payload.type
    problem.title = payload.title
    problem.description = payload.description
    problem.target = payload.target
    problem.target_label = payload.target_label
    problem.target_ids = ",".join(payload.target_ids)
    if payload.status and problem.content_type == "question":
        problem.status = payload.status
    problem.content_type = payload.content_type
    problem.slug = payload.slug
    problem.specialty = payload.specialty
    problem.difficulty = payload.difficulty
    problem.estimated_minutes = payload.estimated_minutes
    problem.case_definition = payload.case_definition.model_dump(mode="json") if payload.case_definition else None
    if problem.case_definition and problem.case_definition.get("schema_version") == 1:
        problem.case_definition["schema_version"] = 2
    problem.rubric = payload.rubric.model_dump(mode="json") if payload.rubric else None
    problem.capability_tags = payload.capability_tags
    if problem.content_type == "guided_case":
        problem.author_id = problem.author_id or _teacher.id
        problem.medical_review_status = "not_submitted"
    db.commit()
    db.refresh(problem)
    return serialize_problem(problem, answer_counts(db, [problem.id]).get(problem.id, 0))


@router.post("/{problem_id}/clone-version", response_model=ProblemAuthoringRead)
def clone_problem_version(
    problem_id: int,
    _teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    problem = db.get(Problem, problem_id)
    if (
        problem is None
        or problem.content_type != "guided_case"
        or problem.status != "published"
        or problem.medical_review_status != "approved"
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    for attempt_number in range(2):
        maximum = db.scalar(select(func.max(Problem.version)).where(Problem.slug == problem.slug)) or 0
        clone = Problem(
            type=problem.type,
            title=problem.title,
            description=problem.description,
            target=problem.target,
            target_label=problem.target_label,
            target_ids=problem.target_ids,
            status="draft",
            slug=problem.slug,
            content_type="guided_case",
            specialty=problem.specialty,
            difficulty=problem.difficulty,
            estimated_minutes=problem.estimated_minutes,
            version=maximum + 1,
            parent_problem_id=problem.id,
            case_definition=deepcopy(problem.case_definition),
            rubric=deepcopy(problem.rubric),
            capability_tags=deepcopy(problem.capability_tags or []),
            author_id=_teacher.id,
            medical_review_status="not_submitted",
        )
        db.add(clone)
        try:
            db.commit()
            db.refresh(clone)
            return serialize_authoring_problem(clone)
        except IntegrityError:
            db.rollback()
            if attempt_number == 1:
                raise HTTPException(status_code=409, detail="Unable to allocate a unique case version") from None
    raise HTTPException(status_code=409, detail="Unable to allocate a unique case version")


@router.post("/{problem_id}/publish", response_model=ProblemRead)
def publish_problem(
    problem_id: int,
    _teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")
    if problem.content_type == "guided_case" and problem.author_id != _teacher.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESOURCE_NOT_FOUND")
    if problem.content_type == "guided_case" and (not problem.case_definition or not problem.rubric):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Guided case requires definition and rubric"
        )
    if problem.content_type == "guided_case" and problem.medical_review_status != "approved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Medical review approval required")
    if problem.content_type == "guided_case":
        from app.api.medical_review import case_digest

        latest_review = db.scalar(
            select(MedicalReview)
            .where(MedicalReview.problem_id == problem.id, MedicalReview.decision == "approved")
            .order_by(MedicalReview.id.desc())
        )
        if latest_review is None or latest_review.case_digest != case_digest(problem):
            problem.medical_review_status = "not_submitted"
            db.commit()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="STATE_CONFLICT")
    if problem.status == "published":
        return serialize_problem(problem, answer_counts(db, [problem.id]).get(problem.id, 0))
    problem.status = "published"
    problem.published_at = datetime.now(UTC)
    db.commit()
    db.refresh(problem)
    return serialize_problem(problem, answer_counts(db, [problem.id]).get(problem.id, 0))


@router.post("/{problem_id}/reject", response_model=ProblemRead)
def reject_problem(
    problem_id: int,
    _teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")
    if problem.content_type == "guided_case":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Use medical review to reject a case")
    if problem.status == "published" and problem.content_type == "guided_case":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Published case is immutable; clone a new version"
        )
    problem.status = "rejected"
    db.commit()
    db.refresh(problem)
    return serialize_problem(problem, answer_counts(db, [problem.id]).get(problem.id, 0))


@router.get("/{problem_id}/thread", response_model=QuestionThreadRead)
def get_question_thread(
    problem_id: int,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> QuestionThread:
    thread = db.scalar(
        select(QuestionThread)
        .where(QuestionThread.problem_id == problem_id, QuestionThread.student_id == user.id)
        .options(selectinload(QuestionThread.messages))
    )
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question thread not found")
    return {"question_id": problem_id, "messages": thread.messages, "updated_at": thread.updated_at}


@router.post("/{problem_id}/thread", response_model=QuestionThreadRead)
def upsert_question_thread(
    problem_id: int,
    payload: QuestionThreadUpsert,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict:
    problem = db.get(Problem, problem_id)
    if problem is None or not is_problem_visible_to_student(problem, user, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")
    thread = db.scalar(
        select(QuestionThread).where(QuestionThread.problem_id == problem_id, QuestionThread.student_id == user.id)
    )
    if thread is None:
        thread = QuestionThread(problem_id=problem_id, student_id=user.id)
        db.add(thread)
        db.flush()
    thread.messages.clear()
    db.flush()
    for message in payload.messages:
        thread.messages.append(QuestionThreadMessage(role=message.role, content=message.content))
    db.commit()
    thread = db.scalar(
        select(QuestionThread).where(QuestionThread.id == thread.id).options(selectinload(QuestionThread.messages))
    )
    return {"question_id": problem_id, "messages": thread.messages, "updated_at": thread.updated_at}
