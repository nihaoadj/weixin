from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom, MedicalReview
from app.modules.content.domain.digest import case_digest
from app.modules.content.domain.templates import SAFETY_NOTICE as _SAFETY_NOTICE
from app.modules.content.domain.templates import showcase_draft as _content_showcase_draft
from app.modules.content.infrastructure.models import Problem, ProblemKnowledgeLink
from app.modules.identity.infrastructure.models import User

SAFETY_NOTICE = _SAFETY_NOTICE


_CAPABILITY_TAGS: dict[str, list[str]] = {
    "cap-undergraduate-showcase": ["differential_diagnosis", "evidence_reasoning", "management_safety"],
    "acute-chest-pain-undergraduate-showcase": [
        "differential_diagnosis",
        "evidence_reasoning",
        "management_safety",
    ],
    "right-lower-quadrant-pain-undergraduate-showcase": [
        "problem_representation",
        "evidence_reasoning",
        "test_selection",
    ],
}

_KNOWLEDGE_POINT_CODES: dict[str, tuple[str, ...]] = {
    "cap-undergraduate-showcase": ("respiratory.cap",),
    "acute-chest-pain-undergraduate-showcase": ("cardio.acs",),
    "right-lower-quadrant-pain-undergraduate-showcase": ("digestive.appendicitis",),
}


def _apply_knowledge_links(problem: Problem) -> None:
    """Keep the three built-in cases navigable from the fixed T08 catalog."""

    expected = _KNOWLEDGE_POINT_CODES.get(problem.slug or "", ())
    if tuple(link.point_code for link in problem.knowledge_links) == expected:
        return
    problem.knowledge_links.clear()
    problem.knowledge_links.extend(ProblemKnowledgeLink(point_code=code) for code in expected)


def _seed_payload(draft: dict[str, object], slug: str) -> dict[str, object]:
    return {
        "type": "病例分析",
        "title": draft["title"],
        "description": draft["description"],
        "target": "all",
        "target_label": "全体学生",
        "target_ids": "",
        "status": "published",
        "slug": slug,
        "content_type": "guided_case",
        "specialty": draft["specialty"],
        "difficulty": draft["difficulty"],
        "estimated_minutes": draft["estimated_minutes"],
        "version": 1,
        "case_definition": draft["case_definition"],
        "rubric": draft["rubric"],
        "capability_tags": list(_CAPABILITY_TAGS[slug]),
    }


def showcase_case_payload() -> dict[str, object]:
    """Build the published seed envelope around content-owned case templates."""

    return _seed_payload(_content_showcase_draft("社区获得性肺炎"), "cap-undergraduate-showcase")


def showcase_draft(topic: str = "社区获得性肺炎") -> dict[str, object]:
    """Build a seed-compatible envelope from the content module's pure template."""

    lowered = topic.lower()
    if "胸痛" in lowered:
        slug = "acute-chest-pain-undergraduate-showcase"
    elif "右下腹" in lowered or "阑尾" in lowered:
        slug = "right-lower-quadrant-pain-undergraduate-showcase"
    else:
        slug = "cap-undergraduate-showcase"
    return _seed_payload(_content_showcase_draft(topic), slug)


def seed_showcase_case(db: Session) -> Problem:
    existing = db.scalar(select(Problem).where(Problem.slug == "cap-undergraduate-showcase", Problem.version == 1))
    if existing:
        problem = existing
        if not problem.capability_tags:
            problem.capability_tags = showcase_case_payload()["capability_tags"]
        if problem.case_definition and problem.case_definition.get("schema_version") == 1:
            problem.case_definition = showcase_case_payload()["case_definition"]
    else:
        problem = Problem(**showcase_case_payload())
        db.add(problem)
    _apply_knowledge_links(problem)
    db.commit()
    db.refresh(problem)
    teacher = db.scalar(select(User).where(User.external_id == "demo_teacher"))
    if teacher is None:
        teacher = User(external_id="demo_teacher", role="teacher", nickname="示例教师", permissions=[])
        db.add(teacher)
        db.flush()
    reviewer = db.scalar(select(User).where(User.external_id == "demo_reviewer"))
    if reviewer is None:
        reviewer = User(
            external_id="demo_reviewer",
            role="teacher",
            nickname="医学审核专家",
            permissions=["medical_review"],
        )
        db.add(reviewer)
        db.flush()
    student = db.scalar(select(User).where(User.external_id == "demo_student"))
    if student is None:
        student = User(external_id="demo_student", role="student", nickname="示例学生", class_ids=["demo_class_1"])
        db.add(student)
        db.flush()
    classroom = db.scalar(select(ClassRoom).where(ClassRoom.code == "demo_class_1"))
    if classroom is None:
        classroom = ClassRoom(name="临床一班", code="demo_class_1", teacher_id=teacher.id)
        db.add(classroom)
        db.flush()
    if (
        db.scalar(select(ClassMember).where(ClassMember.class_id == classroom.id, ClassMember.student_id == student.id))
        is None
    ):
        db.add(ClassMember(class_id=classroom.id, student_id=student.id))
    problem.author_id = teacher.id
    problem.medical_review_status = "approved"
    digest = case_digest(problem)
    if (
        db.scalar(
            select(MedicalReview).where(
                MedicalReview.problem_id == problem.id,
                MedicalReview.decision == "approved",
                MedicalReview.case_digest == digest,
            )
        )
        is None
    ):
        db.add(
            MedicalReview(
                problem_id=problem.id,
                reviewer_id=reviewer.id,
                decision="approved",
                comment="内置示例病例审核通过",
                problem_version=problem.version,
                case_digest=digest,
            )
        )
    db.commit()
    db.refresh(problem)
    for payload in showcase_additional_payloads():
        item = db.scalar(select(Problem).where(Problem.slug == payload["slug"], Problem.version == 1))
        if item is None:
            item = Problem(**payload, author_id=teacher.id, medical_review_status="approved")
            db.add(item)
            db.flush()
        else:
            item.author_id = teacher.id
            item.medical_review_status = "approved"
        _apply_knowledge_links(item)
        digest = case_digest(item)
        if (
            db.scalar(
                select(MedicalReview).where(
                    MedicalReview.problem_id == item.id,
                    MedicalReview.decision == "approved",
                    MedicalReview.case_digest == digest,
                )
            )
            is None
        ):
            db.add(
                MedicalReview(
                    problem_id=item.id,
                    reviewer_id=reviewer.id,
                    decision="approved",
                    comment="内置示例病例审核通过",
                    problem_version=item.version,
                    case_digest=digest,
                )
            )
    db.commit()
    db.refresh(problem)
    return problem


def showcase_additional_payloads() -> list[dict[str, object]]:
    return [showcase_draft("急性胸痛"), showcase_draft("右下腹痛")]
