from __future__ import annotations

from typing import Any


def _field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def completed_stream_text(events: Any) -> tuple[str, str | None]:
    """Read only completion/delta payloads from the SDK stream boundary.

    The small untyped branch supports the local fake SDK fixtures; real SDK
    events must identify a Coze completion or message-delta event explicitly.
    """
    chunks: list[str] = []
    conversation_ref: str | None = None
    saw_completed = False
    for event in events:
        event_name = str(_field(event, "event") or _field(event, "type") or "")
        data = _field(event, "data") or event
        if not event_name:
            # Fixture shape used at the official SDK boundary, never a fallback
            # path for a real named event.
            content = _field(data, "content")
            if content:
                chunks.append(str(content))
                saw_completed = True
            continue
        normalized = event_name.lower()
        if normalized.endswith("message.delta") or normalized.endswith("message.completed"):
            content = _field(data, "content")
            if content:
                chunks.append(str(content))
        if normalized.endswith("chat.completed") or normalized.endswith("workflow.completed"):
            saw_completed = True
            conversation_ref = (
                str(_field(data, "conversation_id") or _field(event, "conversation_id") or conversation_ref or "")
                or conversation_ref
            )
        if normalized.endswith("chat.interrupted") or normalized.endswith("workflow.interrupted"):
            raise RuntimeError("coze_interrupted")
    if not saw_completed:
        raise RuntimeError("coze_incomplete_stream")
    return "".join(chunks), conversation_ref
