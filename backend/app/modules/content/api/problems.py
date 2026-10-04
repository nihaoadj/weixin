from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.bootstrap.composition import content_application
from app.db import get_db
from app.dependencies import get_current_user, require_student, require_teacher
from app.modules.content.api.schemas import (
    ProblemAuthoringRead,
    ProblemCreate,
    ProblemRead,
    ProblemUpdate,
    TeacherContentActionSummary,
)
from app.modules.content.application.records import ProblemCommand, ProblemRecord
from app.modules.content.public import authoring_problem_view, draft_view, problem_view
from app.modules.identity.infrastructure.models import User
from app.modules.qa.api.question_schemas import QuestionThreadRead, QuestionThreadUpsert
from app.modules.qa.application.ports import QuestionThreadCommand
from app.modules.qa.application.records import MessageInput
from app.modules.qa.public import question_thread_view
from app.modules.qa.wiring import questions_application
from app.modules.training.api.schemas import CaseDraftGenerateRequest, CaseDraftGenerateResponse
from app.shared.actor import Actor

router = APIRouter(prefix="/problems", tags=["problems"])


def _view_problem(db: Session, user: User, problem: ProblemRecord) -> dict[str, object]:
    actor = Actor.from_user(user)
    return problem_view(
        problem,
        public_for_student=actor.role == "student",
        allowed_actions=content_application(db).allowed_actions(actor, problem),
    )


def _command(payload: ProblemCreate | ProblemUpdate) -> ProblemCommand:
    return ProblemCommand(
        type=payload.type,
        title=payload.title,
        description=payload.description,
        target=payload.target,
        target_label=payload.target_label,
        target_ids=tuple(payload.target_ids),
        content_type=payload.content_type,
        slug=payload.slug,
        specialty=payload.specialty,
        difficulty=payload.difficulty,
        estimated_minutes=payload.estimated_minutes,
        version=payload.version,
        parent_problem_id=payload.parent_problem_id,
        case_definition=payload.case_definition.model_dump(mode="json") if payload.case_definition else None,
        rubric=payload.rubric.model_dump(mode="json") if payload.rubric else None,
        capability_tags=tuple(payload.capability_tags),
        knowledge_point_codes=tuple(dict.fromkeys(payload.knowledge_point_codes)),
        preserve_knowledge_point_codes=isinstance(payload, ProblemUpdate)
        and "knowledge_point_codes" not in payload.model_fields_set,
        status=getattr(payload, "status", None),
    )


@router.get("", response_model=list[ProblemRead])
def list_problems(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    actor = Actor.from_user(user)
    return [_view_problem(db, user, item) for item in content_application(db).list(actor)]


@router.post("/case-drafts/generate", response_model=CaseDraftGenerateResponse)
def generate_case_draft(
    payload: CaseDraftGenerateRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = content_application(db).generate_draft(
        Actor.from_user(teacher), payload.topic, payload.learner_level, payload.learning_objectives
    )
    return draft_view(result)


@router.get("/teacher-action-summary", response_model=TeacherContentActionSummary)
def teacher_content_action_summary(teacher: User = Depends(require_teacher), db: Session = Depends(get_db)) -> dict:
    return content_application(db).teacher_action_summary(Actor.from_user(teacher))


@router.get("/{problem_id}/authoring", response_model=ProblemAuthoringRead)
def get_problem_authoring(
    problem_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return authoring_problem_view(content_application(db).authoring(Actor.from_user(teacher), problem_id))


@router.get("/{problem_id}", response_model=ProblemRead)
def get_problem(
    problem_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    actor = Actor.from_user(user)
    return _view_problem(db, user, content_application(db).get(actor, problem_id))


@router.post("", response_model=ProblemRead)
def create_problem(
    payload: ProblemCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return _view_problem(db, teacher, content_application(db).create(Actor.from_user(teacher), _command(payload)))


@router.put("/{problem_id}", response_model=ProblemRead)
def update_problem(
    problem_id: int,
    payload: ProblemUpdate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return _view_problem(
        db, teacher, content_application(db).update(Actor.from_user(teacher), problem_id, _command(payload))
    )


@router.delete("/{problem_id}", status_code=204)
def delete_problem(
    problem_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> Response:
    content_application(db).delete(Actor.from_user(teacher), problem_id)
    return Response(status_code=204)


@router.post("/{problem_id}/clone-version", response_model=ProblemAuthoringRead)
def clone_problem_version(
    problem_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return authoring_problem_view(content_application(db).clone(Actor.from_user(teacher), problem_id))


@router.post("/{problem_id}/publish", response_model=ProblemRead)
def publish_problem(
    problem_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return _view_problem(db, teacher, content_application(db).publish(Actor.from_user(teacher), problem_id))


@router.post("/{problem_id}/reject", response_model=ProblemRead)
def reject_problem(
    problem_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return _view_problem(db, teacher, content_application(db).reject(Actor.from_user(teacher), problem_id))


@router.get("/{problem_id}/thread", response_model=QuestionThreadRead)
def get_question_thread(
    problem_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)
) -> dict[str, object]:
    return question_thread_view(questions_application().thread(Actor.from_user(user), problem_id))


@router.post("/{problem_id}/thread", response_model=QuestionThreadRead)
def upsert_question_thread(
    problem_id: int,
    payload: QuestionThreadUpsert,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    command = QuestionThreadCommand(
        messages=tuple(MessageInput(role=item.role, content=item.content) for item in payload.messages)
    )
    return question_thread_view(questions_application().upsert_thread(Actor.from_user(user), problem_id, command))
