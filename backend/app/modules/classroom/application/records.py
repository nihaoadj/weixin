from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ClassRecord:
    id: int
    name: str
    code: str
    status: str
    teacher_id: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ClassStudentRecord:
    id: int
    nickname: str
    external_id: str
    joined_at: datetime


@dataclass(frozen=True, slots=True)
class ClassCommand:
    name: str
    code: str


@dataclass(frozen=True, slots=True)
class ClassUpdateCommand:
    name: str | None
    status: str | None
