"""Dry-run-first, development-only evidence backfill.

The script deliberately handles only deterministic case-assessment facts.  It
never backfills QA reports, autonomous PBL findings, or AI practice scores.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.core.config import get_settings
from app.db import SessionLocal
from app.modules.classroom.infrastructure.models import ClassMember, ClassRoom
from app.modules.content.infrastructure.models import Problem
from app.modules.learning.public import LearningEvidenceCommand, LearningEvidenceMetricCommand
from app.modules.learning.wiring import learning_evidence_port
from app.modules.training.infrastructure.models import CaseAssessment, CaseAttempt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill deterministic T30 learning evidence")
    parser.add_argument("--apply", action="store_true", help="write eligible evidence; dry-run is the default")
    parser.add_argument("--confirm-development", action="store_true")
    parser.add_argument("--backup-path", type=Path, help="new JSON backup path required for --apply")
    return parser


def _class_ids(session, attempt: CaseAttempt, problem: Problem) -> tuple[int, ...]:
    classes = session.scalars(
        select(ClassRoom)
        .join(ClassMember, ClassMember.class_id == ClassRoom.id)
        .where(ClassMember.student_id == attempt.student_id, ClassRoom.status == "active")
    ).all()
    if problem.target == "class":
        target_codes = set(item for item in (problem.target_ids or "").split(",") if item)
        classes = [item for item in classes if item.code in target_codes]
    elif problem.target == "individual":
        return ()
    return tuple(item.id for item in classes)


def _eligible_rows(session):
    return session.scalars(
        select(CaseAssessment)
        .join(CaseAttempt, CaseAttempt.id == CaseAssessment.attempt_id)
        .join(Problem, Problem.id == CaseAttempt.problem_id)
        .where(
            CaseAttempt.status == "assessed",
            Problem.content_type == "guided_case",
            Problem.status == "published",
            Problem.medical_review_status == "approved",
        )
    ).all()


def _commands(session):
    counts = Counter()
    commands = []
    for assessment in _eligible_rows(session):
        attempt = session.get(CaseAttempt, assessment.attempt_id)
        problem = session.get(Problem, attempt.problem_id) if attempt else None
        if attempt is None or problem is None:
            counts["missing_provenance"] += 1
            continue
        class_ids = _class_ids(session, attempt, problem)
        if not class_ids:
            counts["missing_class_provenance"] += 1
            continue
        metrics = [
            LearningEvidenceMetricCommand(
                "dimension",
                str(item.get("dimension_id")),
                float(item["score"]) if isinstance(item.get("score"), int | float) else None,
                "observed",
                item.get("score") is not None,
            )
            for item in (assessment.dimensions or [])
            if item.get("dimension_id")
        ]
        for class_id in class_ids:
            commands.append(
                LearningEvidenceCommand(
                    student_id=attempt.student_id,
                    class_id=class_id,
                    source_type="case_assessment",
                    source_id=str(assessment.id),
                    source_version=problem.version,
                    authority_level="formal_instruction",
                    visibility_scope="class_detail",
                    event_kind="assessment",
                    occurred_at=assessment.created_at or datetime.now(UTC),
                    dedupe_key=f"case-assessment:{assessment.id}:v{problem.version}:class:{class_id}",
                    metrics=tuple(metrics),
                )
            )
    counts["eligible_commands"] = len(commands)
    return commands, counts


def main() -> int:
    args = _parser().parse_args()
    settings = get_settings()
    if settings.is_production:
        raise RuntimeError("拒绝在 production 环境回填学习证据")
    if args.apply and (not args.confirm_development or args.backup_path is None):
        raise RuntimeError("--apply 必须同时提供 --confirm-development 和新的 --backup-path")
    if args.apply:
        if args.backup_path.exists():
            raise RuntimeError("--backup-path 必须指向尚不存在的新文件")
        if not args.backup_path.parent.exists():
            raise RuntimeError("--backup-path 的父目录必须已存在")

    with SessionLocal() as session:
        commands, counts = _commands(session)
        existing = sum(
            session.scalar(
                select(CaseAssessment.id).where(CaseAssessment.id == int(command.source_id))
            )
            is not None
            for command in commands
        )
        counts["already_source_rows"] = existing
        if args.apply:
            evidence = learning_evidence_port(session)
            for command in commands:
                evidence.append(command)
            session.commit()
            args.backup_path.write_text(
                json.dumps(
                    {
                        "created_at": datetime.now(UTC).isoformat(),
                        "source": "case_assessment",
                        "command_count": len(commands),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
    mode = "apply" if args.apply else "dry-run"
    print(f"mode: {mode}")
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")
    print("skipped_sources: qa_report, autonomous_pbl, ai_personal_practice, unprovenanceable_history")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
