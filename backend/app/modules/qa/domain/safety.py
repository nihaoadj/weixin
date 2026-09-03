from __future__ import annotations

import re

EMERGENCY_PATTERNS = (
    re.compile(r"胸.{0,6}(持续|突然|剧烈|压榨|闷).{0,8}(痛|疼)"),
    re.compile(r"呼吸(困难|急促)|喘不上气|不能呼吸"),
    re.compile(r"意识(不清|丧失)|昏迷|抽搐"),
    re.compile(r"大出血|止不住血"),
    re.compile(r"偏瘫|口角歪斜|言语不清"),
    re.compile(r"自杀|轻生|不想活"),
)


def is_emergency(content: str) -> bool:
    return any(pattern.search(content) for pattern in EMERGENCY_PATTERNS)


def fallback_reply(prompt: str, mode: str | None) -> str:
    if is_emergency(prompt):
        return (
            "你描述的情况可能包含急症风险信号。请立即停止线上问答并联系当地急救服务，"
            "中国大陆请拨打 120。本提示仅用于安全分流，不能替代急诊评估。"
        )
    if mode == "模拟诊疗":
        return "演示反馈：请继续询问起病时间、诱因、伴随症状、既往史和用药史，并说明鉴别诊断依据。"
    if mode == "病例分析":
        return "演示反馈：建议按主要问题、支持证据、鉴别诊断、检查计划和处理原则组织答案。"
    return "演示反馈：建议从定义、常见表现、鉴别要点和处理原则四部分梳理。医学内容仅用于教学。"
