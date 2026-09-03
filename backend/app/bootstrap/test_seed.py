from datetime import UTC, datetime

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bootstrap.composition import learning_application
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

TEST_CASE_SLUG = "demo-pending-chest-pain"
TEST_QUESTION_SLUG = "demo-question-001"
TEST_CONVERSATION_CLIENT_ID = "demo-conversation-001"


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
    payload = showcase_draft("急性胸痛")
    payload.update(
        {
            "title": "【测试】急性胸痛：待审核病例",
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
        title="【测试】社区获得性肺炎的首要检查",
        description="患者发热、咳嗽、黄痰，胸片提示右下肺浸润影。下一步最适合的教学讨论方向是什么？",
        target="all",
        target_label="全体学生",
        target_ids="",
        status="published",
        published_at=datetime.now(UTC),
        slug=TEST_QUESTION_SLUG,
        content_type="question",
        specialty="呼吸内科",
        difficulty="basic",
        estimated_minutes=5,
        version=1,
    )
    db.add(problem)
    db.flush()
    return problem


def _conversation_and_report(db: Session, student: User) -> None:
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
                    content="患者发热、咳嗽和黄痰，为什么首先考虑社区获得性肺炎？",
                ),
                Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content="可以从病程、痰液性质、肺部体征和影像学证据进行结构化分析。",
                ),
                Message(
                    conversation_id=conversation.id,
                    role="user",
                    content="还需要补充哪些危险因素和安全信息？",
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
                ai_summary="已识别主要诊断方向，但危险因素和安全边界仍需补充。",
                ai_analysis={
                    "errors": [{"content": "危险因素追问不完整", "suggestion": "补充既往史、过敏史和近期住院用药史。"}],
                    "strengths": ["能够结合症状和影像建立初步问题表征"],
                    "general_suggestions": ["使用起病、伴随症状、危险因素和安全信息的固定提问顺序"],
                },
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
                content="这个病例中哪些证据最支持肺炎？",
            ),
            QuestionThreadMessage(
                thread_id=thread.id,
                role="assistant",
                content="发热、黄痰、右下肺局灶体征和新发浸润影是主要支持证据。",
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
                "summary": "48岁男性，急性发热、咳嗽3天，伴黄色黏痰、右侧胸痛和活动后气促。",
                "key_findings": ["发热", "咳嗽", "黄色黏痰", "胸痛"],
            },
        ),
        (
            "problem_representation",
            {
                "stage_id": "problem_representation",
                "summary": "48岁男性急性发热、咳嗽3天伴黄痰和右侧胸痛，考虑社区获得性肺炎。",
            },
        ),
        (
            "differential",
            {
                "stage_id": "differential",
                "items": [
                    {
                        "diagnosis": "社区获得性肺炎",
                        "supporting_evidence": ["发热", "黄痰", "湿啰音"],
                        "opposing_evidence": [],
                    },
                    {"diagnosis": "病毒性肺炎", "supporting_evidence": ["发热"], "opposing_evidence": []},
                    {
                        "diagnosis": "肺栓塞",
                        "supporting_evidence": ["血氧93%"],
                        "opposing_evidence": ["反对黄痰"],
                    },
                ],
            },
        ),
        (
            "tests",
            {
                "stage_id": "tests",
                "items": [
                    {"test_name": "胸部影像", "rationale": "确认浸润并评估范围", "priority": "necessary"},
                    {"test_name": "血常规和炎症指标", "rationale": "评估感染和炎症程度", "priority": "necessary"},
                ],
            },
        ),
        (
            "management",
            {
                "stage_id": "management",
                "items": [
                    {"action": "评估氧合和严重程度", "rationale": "识别恶化风险"},
                    {"action": "支持治疗并复评", "rationale": "监测症状和氧合变化"},
                ],
                "safety_considerations": ["监测血氧", "及时复评"],
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
        classroom = ClassRoom(name="临床一班", code="demo_class_1", teacher_id=teacher.id)
        db.add(classroom)
        db.flush()
    _ensure_member(db, classroom, student)
    _ensure_member(db, classroom, second_student)

    pending_case = _pending_case(db, teacher)
    question = _question(db)
    _conversation_and_report(db, student)
    _question_thread(db, student, question)
    assessment = _seed_assessed_attempt(db, student, showcase_case)
    if assessment is not None:
        learning_application(db).ensure_for_assessment(Actor.from_user(student), assessment.attempt_id)
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
