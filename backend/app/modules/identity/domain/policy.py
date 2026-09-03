from __future__ import annotations


class AuthPolicy:
    """Pure account-source and server-owned role decisions."""

    @staticmethod
    def demo_permissions(external_id: str) -> tuple[str, ...]:
        return ("medical_review",) if external_id == "demo_reviewer" else ()

    @staticmethod
    def wechat_role(openid: str, requested_role: str, teacher_openids: set[str]) -> str:
        return "teacher" if requested_role == "teacher" and openid in teacher_openids else "student"

    @staticmethod
    def can_demo_login(auth_provider: str) -> bool:
        return auth_provider == "demo"
