from __future__ import annotations


def analytics_view(value: dict[str, object]) -> dict[str, object]:
    """Stable read-model boundary; analytics has no write DTO or ORM export."""
    return value
