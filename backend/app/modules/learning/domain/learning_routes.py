"""Pure single-route learning rules; process progress never produces a grade."""

import json
from decimal import ROUND_HALF_UP, Decimal
from hashlib import sha256

from app.shared.errors import AppError

CASE_PHASES = ("pathology_recognition", "mechanism_explanation", "evidence_judgment", "summary_reflection")

REFLECTION_GOALS = [
    {
        "goal_id": "summary_reflection.reasoning",
        "objective": "串联病例事实、病理变化、发生机制与判断，总结推理过程。",
        "completion_requirements": ["用自己的语言串联事实、变化、机制与判断，而非仅复述AI结论。"],
        "guidance_prompts": ["请回顾你的病例分析，说明推理过程、仍不确定之处和下一次的改进方法。"],
    },
    {
        "goal_id": "summary_reflection.improvement",
        "objective": "反思仍不确定的内容或推理不足，提出具体学习改进。",
        "completion_requirements": ["指出至少一个不确定点或推理不足，并提出针对性的核对或学习方法。"],
        "guidance_prompts": ["哪一步仍需要核对？你准备如何改进？"],
    },
]


def digest(value: object) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def conflict(reason: str) -> None:
    error = AppError("STATE_CONFLICT", reason, 409)
    error.reason = reason
    raise error


def percentage(correct: int, count: int) -> float:
    if count <= 0 or not 0 <= correct <= count:
        raise AppError("VALIDATION_ERROR", "测试题数无效", 422)
    return float((Decimal(correct) * 100 / Decimal(count)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def validate_answers(answers: dict, question_ids: set[str], *, complete: bool = False) -> None:
    if not isinstance(answers, dict) or not set(answers) <= question_ids:
        raise AppError("VALIDATION_ERROR", "答卷包含无效题目", 422)
    if any(type(option) is not int or option not in range(4) for option in answers.values()):
        raise AppError("VALIDATION_ERROR", "答案必须为0至3的整数", 422)
    if complete and set(answers) != question_ids:
        raise AppError("VALIDATION_ERROR", "请完成全部题目", 422)


def validate_mixed_answers(answers: dict, questions: list[dict], *, complete: bool = False) -> None:
    types = {item["id"]: item["question_type"] for item in questions}
    if not isinstance(answers, dict) or not set(answers) <= set(types):
        raise AppError("VALIDATION_ERROR", "答卷包含无效题目", 422)
    if complete and set(answers) != set(types):
        raise AppError("VALIDATION_ERROR", "请完成全部题目", 422)
    for question_id, answer in answers.items():
        kind = types[question_id]
        if kind == "single_choice":
            valid = type(answer) is int and answer in range(4)
        elif kind == "multiple_choice":
            valid = (
                isinstance(answer, list)
                and 1 <= len(answer) <= 4
                and all(type(value) is int and value in range(4) for value in answer)
                and len(set(answer)) == len(answer)
            )
        else:
            valid = isinstance(answer, str) and 1 <= len(answer.strip()) <= 2000
        if not valid:
            raise AppError("VALIDATION_ERROR", "答案与题型不匹配", 422)


def mixed_objective_scores(answers: dict, questions: list[dict]) -> tuple[dict[str, int], int]:
    scores: dict[str, int] = {}
    correct_count = 0
    for item in questions:
        if item["question_type"] == "short_answer":
            continue
        selected = answers[item["id"]]
        if item["question_type"] == "single_choice":
            correct = selected == item["correct_option"]
            possible = 15
        else:
            correct = set(selected) == set(item["correct_options"])
            possible = 25
        scores[item["id"]] = possible if correct else 0
        correct_count += int(correct)
    return scores, correct_count


def validate_questions(questions: list[dict], goals: list[str], format_version: str = "single_choice_v1") -> None:
    if format_version == "mixed_v2":
        _validate_mixed_questions(questions, goals)
        return
    if not 1 <= len(questions) <= 12:
        raise AppError("VALIDATION_ERROR", "测试需要1至12题", 422)
    covered = set()
    prompts = set()
    for question in questions:
        options = question.get("options", [])
        prompt = question.get("prompt", "").strip()
        point = question.get("primary_point_code", question.get("point_code"))
        if (
            not prompt
            or len(prompt) > 2000
            or prompt.casefold() in prompts
            or point not in goals
            or len(options) != 4
            or len({x.strip().casefold() for x in options if isinstance(x, str)}) != 4
            or any(not isinstance(x, str) or not x.strip() or len(x) > 500 for x in options)
            or type(question.get("correct_option")) is not int
            or question["correct_option"] not in range(4)
            or not question.get("explanation", "").strip()
            or len(question["explanation"]) > 2000
        ):
            raise AppError("VALIDATION_ERROR", "题目、选项、目标或解析无效", 422)
        prompts.add(prompt.casefold())
        covered.add(point)
    if covered != set(goals):
        raise AppError("VALIDATION_ERROR", "测试必须覆盖全部主要目标", 422)


def _validate_mixed_questions(questions: list[dict], goals: list[str]) -> None:
    if len(goals) != 1 or len(questions) != 5:
        raise AppError("VALIDATION_ERROR", "混合测试需要一个目标和五道题", 422)
    expected = ("single_choice", "single_choice", "single_choice", "multiple_choice", "short_answer")
    if tuple(item.get("question_type") for item in questions) != expected:
        raise AppError("VALIDATION_ERROR", "题型应为三道单选、一道多选、一道简答", 422)
    prompts: set[str] = set()
    for index, item in enumerate(questions, 1):
        prompt = item.get("prompt", "")
        explanation = item.get("explanation", "")
        if (
            not isinstance(prompt, str)
            or not prompt.strip()
            or len(prompt) > 2000
            or prompt.strip().casefold() in prompts
            or not isinstance(explanation, str)
            or not explanation.strip()
            or len(explanation) > 2000
            or item.get("primary_point_code", item.get("point_code")) != goals[0]
            or item.get("position", index) != index
        ):
            raise AppError("VALIDATION_ERROR", "混合测试题目或目标无效", 422)
        prompts.add(prompt.strip().casefold())
        if item["question_type"] == "short_answer":
            rubric = item.get("rubric")
            reference = item.get("reference_answer")
            if (
                not isinstance(reference, str)
                or not reference.strip()
                or len(reference) > 2000
                or not isinstance(rubric, list | tuple)
                or len(rubric) != 3
                or any(
                    not isinstance(part, dict)
                    or not isinstance(part.get("criterion_id"), str)
                    or not part["criterion_id"].strip()
                    or not isinstance(part.get("description"), str)
                    or not part["description"].strip()
                    or len(part["description"]) > 300
                    or part.get("max_points") != 10
                    for part in rubric
                )
                or len({part["criterion_id"] for part in rubric}) != 3
            ):
                raise AppError("VALIDATION_ERROR", "简答标准答案或评分要点无效", 422)
            continue
        options = item.get("options")
        if (
            not isinstance(options, list | tuple)
            or len(options) != 4
            or any(not isinstance(value, str) or not value.strip() or len(value) > 500 for value in options)
            or len({value.strip().casefold() for value in options}) != 4
        ):
            raise AppError("VALIDATION_ERROR", "选择题选项无效", 422)
        if item["question_type"] == "single_choice":
            if type(item.get("correct_option")) is not int or item["correct_option"] not in range(4):
                raise AppError("VALIDATION_ERROR", "单选答案无效", 422)
        else:
            answers = item.get("correct_options")
            if (
                not isinstance(answers, list | tuple)
                or not 2 <= len(answers) <= 3
                or any(type(value) is not int or value not in range(4) for value in answers)
                or len(set(answers)) != len(answers)
            ):
                raise AppError("VALIDATION_ERROR", "多选答案无效", 422)


def case_transition(phase: str, assessment: dict, goals: list[str], evidence: set[str]) -> str:
    if assessment.get("phase") != phase or phase not in CASE_PHASES:
        conflict("INVALID_PHASE")
    decision = assessment.get("decision")
    if decision == "stay":
        return phase
    expected = "complete" if phase == CASE_PHASES[-1] else "advance"
    references = assessment.get("evidence_message_ids", [])
    checks = assessment.get("goal_checks", [])
    satisfied = {item.get("goal_id") for item in checks if item.get("status") == "satisfied"}
    if decision != expected or not references or not set(references) <= evidence or satisfied != set(goals):
        conflict("INVALID_PHASE_EVIDENCE")
    index = CASE_PHASES.index(phase) + 1
    return CASE_PHASES[index] if index < len(CASE_PHASES) else "completed"
