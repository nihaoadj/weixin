from datetime import UTC, datetime

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bootstrap.seed import seed_showcase_case, showcase_draft
from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.content.infrastructure.models import Problem
from app.modules.identity.infrastructure.models import User
from app.modules.qa.infrastructure.models import Conversation, Message, QuestionThread, QuestionThreadMessage
from app.modules.reports.infrastructure.models import Report
from app.modules.training.api.schemas import StageAnswer
from app.modules.training.infrastructure.models import CaseAssessment, CaseAttempt
from app.modules.training.wiring import training_application
from app.shared.actor import Actor

TEST_CASE_SLUG = "pathology-demo-pending-v2"
TEST_QUESTION_SLUG = "pathology-demo-question-v2"
TEST_CONVERSATION_CLIENT_ID = "pathology-demo-conversation-v2"


def _user(db: Session, external_id: str, role: str, nickname: str, permissions: list[str] | None = None) -> User:
    user = db.scalar(select(User).where(User.external_id == external_id))
    if user is None:
        user = User(
            external_id=external_id,
            role=role,
            nickname=nickname,
            permissions=permissions or [],
            class_ids=[],
        )
        db.add(user)
        db.flush()
    elif permissions:
        user.permissions = sorted(set((user.permissions or []) + permissions))
    return user


def _ensure_member(db: Session, classroom: ClassRoom, student: User) -> None:
    member = db.scalar(
        select(ClassMember).where(ClassMember.class_id == classroom.id, ClassMember.student_id == student.id)
    )
    if member is None:
        db.add(ClassMember(class_id=classroom.id, student_id=student.id))
    class_ids = set(student.class_ids or [])
    if classroom.code not in class_ids:
        student.class_ids = sorted(class_ids | {classroom.code})


def _pending_case(db: Session, teacher: User) -> Problem:
    problem = db.scalar(select(Problem).where(Problem.slug == TEST_CASE_SLUG, Problem.version == 1))
    if problem is not None:
        return problem
    payload = showcase_draft("细胞损伤与适应")
    payload.update(
        {
            "title": "【测试】细胞损伤与适应：待审核病例",
            "description": "用于测试教师提交、医学审核和发布流程的合成教学病例。",
            "slug": TEST_CASE_SLUG,
            "status": "draft",
            "medical_review_status": "pending",
            "author_id": teacher.id,
        }
    )
    problem = Problem(**payload)
    db.add(problem)
    db.flush()
    return problem


def _question(db: Session) -> Problem:
    problem = db.scalar(select(Problem).where(Problem.slug == TEST_QUESTION_SLUG, Problem.version == 1))
    if problem is not None:
        return problem
    problem = Problem(
        type="病例单选",
        title="【测试】可逆性细胞损伤的形态依据",
        description="合成切片见细胞肿胀与胞质淡染，核结构尚存。如何建立病理机制解释？",
        target="all",
        target_label="全体学生",
        target_ids="",
        status="published",
        published_at=datetime.now(UTC),
        slug=TEST_QUESTION_SLUG,
        content_type="question",
        specialty="病理学",
        difficulty="basic",
        estimated_minutes=5,
        version=1,
    )
    db.add(problem)
    db.flush()
    return problem


def _conversation_and_report(db: Session, student: User, classroom: ClassRoom) -> None:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.client_id == TEST_CONVERSATION_CLIENT_ID,
            Conversation.student_id == student.id,
        )
    )
    if conversation is None:
        conversation = Conversation(client_id=TEST_CONVERSATION_CLIENT_ID, student_id=student.id)
        db.add(conversation)
        db.flush()
        db.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    role="user",
                    content="组织切片中出现细胞肿胀，怎样区分可逆损伤与坏死？",
                ),
                Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content="可以从细胞形态、核结构与组织分布进行结构化分析。",
                ),
                Message(
                    conversation_id=conversation.id,
                    role="user",
                    content="还需要观察哪些核变化才能支持坏死？",
                ),
            ]
        )
    report = db.scalar(select(Report).where(Report.conversation_id == conversation.id))
    if report is None:
        db.add(
            Report(
                conversation_id=conversation.id,
                student_id=student.id,
                status="pending_review",
                ai_score=78,
                ai_summary="已描述细胞损伤的形态，仍需区分可逆变化与细胞死亡。",
                ai_analysis={
                    "errors": [{"content": "核形态观察不完整", "suggestion": "补充核固缩、核碎裂与核溶解的观察。"}],
                    "strengths": ["能够依据形态建立初步解释"],
                    "general_suggestions": ["按照观察、假设与证据核对的顺序讨论"],
                },
                class_id=classroom.id,
                class_name_snapshot=classroom.name,
            )
        )


def _question_thread(db: Session, student: User, problem: Problem) -> None:
    thread = db.scalar(
        select(QuestionThread).where(QuestionThread.problem_id == problem.id, QuestionThread.student_id == student.id)
    )
    if thread is not None:
        return
    thread = QuestionThread(problem_id=problem.id, student_id=student.id)
    db.add(thread)
    db.flush()
    db.add_all(
        [
            QuestionThreadMessage(
                thread_id=thread.id,
                role="user",
                content="这个病例中哪些形态证据支持可逆损伤？",
            ),
            QuestionThreadMessage(
                thread_id=thread.id,
                role="assistant",
                content="细胞肿胀而核结构尚存，需结合膜与细胞器的观察判断。",
            ),
        ]
    )


def _seed_assessed_attempt(db: Session, student: User, problem: Problem) -> CaseAssessment | None:
    existing = db.scalar(
        select(CaseAttempt)
        .where(
            CaseAttempt.problem_id == problem.id,
            CaseAttempt.student_id == student.id,
            CaseAttempt.status == "assessed",
        )
        .order_by(CaseAttempt.id.desc())
    )
    if existing is not None:
        return existing.assessment
    in_progress = db.scalar(
        select(CaseAttempt)
        .where(CaseAttempt.problem_id == problem.id, CaseAttempt.student_id == student.id)
        .order_by(CaseAttempt.id.desc())
    )
    if in_progress is not None:
        return None

    actor = Actor.from_user(student)
    application = training_application(db)
    attempt = application.start(actor, problem.id)
    answers = [
        (
            "history",
            {
                "stage_id": "history",
                "summary": "合成肾小管切片见上皮细胞肿胀与胞质淡染。",
                "key_findings": ["细胞肿胀", "核结构尚存"],
            },
        ),
        (
            "problem_representation",
            {"stage_id": "problem_representation", "summary": "细胞肿胀与核结构尚存提示可逆损伤，需排查坏死证据。"},
        ),
        (
            "differential",
            {
                "stage_id": "differential",
                "items": [
                    {"diagnosis": "可逆性损伤", "supporting_evidence": ["肿胀", "核尚存"], "opposing_evidence": []},
                    {"diagnosis": "坏死", "supporting_evidence": [], "opposing_evidence": ["尚无核溶解证据"]},
                ],
            },
        ),
        (
            "tests",
            {
                "stage_id": "tests",
                "items": [
                    {
                        "test_name": "补充核与细胞膜的形态观察",
                        "rationale": "核对细胞死亡的支持和反对证据",
                        "priority": "necessary",
                    }
                ],
            },
        ),
        (
            "management",
            {
                "stage_id": "management",
                "items": [{"action": "总结损伤与形态关系", "rationale": "说明现有证据与解释的限制"}],
                "safety_considerations": ["合成教学内容不能代替临床诊断"],
            },
        ),
    ]
    adapter = TypeAdapter(StageAnswer)
    for stage_id, raw_answer in answers:
        validated_answer = adapter.validate_python(raw_answer)
        application.submit_stage(actor, attempt.id, stage_id, validated_answer.model_dump(mode="json"))
    assessment = application.complete(actor, attempt.id)
    return db.get(CaseAssessment, assessment.id)


def seed_test_data(db: Session) -> dict[str, int]:
    """Add repeatable development fixtures without deleting or resetting user data."""
    showcase_case = seed_showcase_case(db)
    teacher = _user(db, "demo_teacher", "teacher", "示例教师")
    _user(db, "demo_reviewer", "teacher", "医学审核专家", ["medical_review"])
    student = _user(db, "demo_student", "student", "示例学生")
    second_student = _user(db, "demo_student_b", "student", "示例学生（二）")
    classroom = db.scalar(select(ClassRoom).where(ClassRoom.code == "demo_class_1"))
    if classroom is None:
        classroom = ClassRoom(name="病理学一班", code="demo_class_1", teacher_id=teacher.id)
        db.add(classroom)
        db.flush()
    _ensure_member(db, classroom, student)
    _ensure_member(db, classroom, second_student)

    pending_case = _pending_case(db, teacher)
    question = _question(db)
    _conversation_and_report(db, student, classroom)
    _question_thread(db, student, question)
    # Independent case assessment remains available to the student without a formal plan.
    _seed_assessed_attempt(db, student, showcase_case)
    db.commit()

    return {
        "users": db.query(User).count(),
        "classes": db.query(ClassRoom).count(),
        "class_members": db.query(ClassMember).count(),
        "problems": db.query(Problem).count(),
        "pending_cases": db.query(Problem).filter(Problem.slug == pending_case.slug).count(),
        "conversations": db.query(Conversation).count(),
        "reports": db.query(Report).count(),
        "question_threads": db.query(QuestionThread).count(),
        "case_attempts": db.query(CaseAttempt).count(),
    }
