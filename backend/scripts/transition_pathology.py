"""Explicit local-development conversion. Default is read-only preview, never dotenv-driven."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
DEVELOPMENT_DB = BACKEND / "data/dev.db"
LEGACY = json.loads(Path(__file__).with_name("pathology_legacy_ids.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(BACKEND))


@contextmanager
def connect(path: Path, *, readonly=False):
    connection = sqlite3.connect(path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"), uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        yield connection
    finally:
        connection.close()


def inventory(connection):
    tables = [
        row[0]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    ]
    if any(not name.replace("_", "").isalnum() for name in tables):
        raise ValueError("Unexpected SQL identifier")
    return {table: [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')] for table in tables}


def fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, ensure_ascii=True, sort_keys=True, default=str).encode()).hexdigest()


def plan_conversion(connection):
    rows = inventory(connection)
    candidate = {table: set() for table in rows}
    protected = {table: set() for table in rows}
    old_codes = set(LEGACY["point_codes"])
    old_problems = {r["id"] for r in rows.get("problems", []) if r.get("slug") in LEGACY["problem_slugs"]}
    pbl_problems = {r["problem_id"] for r in rows.get("problem_origins", []) if r["source_type"] == "pbl_suggestion"}
    mixed_problems = {
        r["problem_id"] for r in rows.get("problem_knowledge_links", []) if r["point_code"] not in old_codes
    }
    candidate.get("problems", set()).update(old_problems - pbl_problems - mixed_problems)
    sample_students = {r["id"] for r in rows.get("users", []) if r["external_id"] in LEGACY["student_external_ids"]}
    sample_conversations = {
        r["id"]
        for r in rows.get("conversations", [])
        if r["client_id"] in LEGACY["conversation_client_ids"] and r["student_id"] in sample_students
    }
    candidate.get("conversations", set()).update(sample_conversations)
    for table, column in (
        ("problem_knowledge_links", "point_code"),
        ("report_knowledge_links", "point_code"),
        ("conversation_learning_contexts", "topic_code"),
        ("knowledge_card_contributions", "point_code"),
        ("review_items", "point_code"),
        ("review_states", "point_code"),
    ):
        candidate.get(table, set()).update(r["id"] for r in rows.get(table, []) if r.get(column) in old_codes)
    # Preserve original content, identities, PBL, and mixed intervention chains.
    for table in rows:
        if table in {"users", "classes", "class_members"} or table.startswith("pbl_"):
            protected[table] = {r["id"] for r in rows[table]}
    protected.get("problems", set()).update(
        r["id"] for r in rows.get("problems", []) if r["id"] not in candidate.get("problems", set())
    )
    protected.get("conversations", set()).update(
        r["id"] for r in rows.get("conversations", []) if r["id"] not in sample_conversations
    )
    protected.get("reports", set()).update(
        r["id"] for r in rows.get("reports", []) if r["conversation_id"] not in sample_conversations
    )
    for plan in rows.get("learning_plans", []):
        tasks = [r for r in rows.get("learning_tasks", []) if r["plan_id"] == plan["id"]]
        mixed = any(t.get("problem_id") in old_problems for t in tasks) and any(
            t.get("problem_id") and t["problem_id"] not in old_problems for t in tasks
        )
        if plan.get("source_type") == "pbl_suggestion" or mixed:
            protected["learning_plans"].add(plan["id"])
            protected["learning_tasks"].update(t["id"] for t in tasks)
            protected.get("learning_task_attempts", set()).update(
                r["id"] for r in rows.get("learning_task_attempts", []) if r["task_id"] in protected["learning_tasks"]
            )
    foreign_keys = {
        table: [dict(r) for r in connection.execute(f'PRAGMA foreign_key_list("{table}")')] for table in rows
    }
    # Protected children retain their ancestors, including a legacy case referenced by PBL.
    changed = True
    while changed:
        changed = False
        for table, references in foreign_keys.items():
            for row in rows[table]:
                if row.get("id") not in protected[table]:
                    continue
                for reference in references:
                    parent, value = reference["table"], row.get(reference["from"])
                    if value is not None and parent in protected and value not in protected[parent]:
                        protected[parent].add(value)
                        changed = True
    # Expand only the retired example chain. Audit rows survive with detached references.
    changed = True
    while changed:
        changed = False
        for table, references in foreign_keys.items():
            if table == "ai_call_logs":
                continue
            for row in rows[table]:
                identifier = row.get("id")
                if identifier is None or identifier in candidate[table] or identifier in protected[table]:
                    continue
                if any(
                    row.get(ref["from"]) in candidate.get(ref["table"], set()) - protected.get(ref["table"], set())
                    for ref in references
                ):
                    candidate[table].add(identifier)
                    changed = True
    for row in rows.get("student_notifications", []):
        if row.get("entity_type") == "learning_plan" and row["entity_id"] in candidate.get("learning_plans", set()):
            candidate["student_notifications"].add(row["id"])
    deletions = {table: sorted(ids - protected[table]) for table, ids in candidate.items() if ids - protected[table]}
    preserved = {
        table: fingerprint([row for row in rows[table] if row.get("id") in ids])
        for table, ids in protected.items()
        if ids
    }
    return deletions, protected, preserved


def backup_verified(source: Path, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError("Backup target already exists")
    with connect(source, readonly=True) as original, closing(sqlite3.connect(target)) as backup:
        original.backup(backup)
        if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Backup integrity failure")
        backup.row_factory = sqlite3.Row
        if fingerprint(inventory(original)) != fingerprint(inventory(backup)):
            raise RuntimeError("Backup content mismatch")
    # Exercise SQLite restore, not just file existence.
    with closing(sqlite3.connect(":memory:")) as restored, connect(target, readonly=True) as backup:
        backup.backup(restored)
        restored.row_factory = sqlite3.Row
        if fingerprint(inventory(restored)) != fingerprint(inventory(backup)):
            raise RuntimeError("Restore verification failed")


def clean_retired_content(connection):
    connection.execute("BEGIN IMMEDIATE")
    deletions, protected, fingerprints = plan_conversion(connection)
    connection.execute("PRAGMA defer_foreign_keys=ON")
    try:
        for column, table in (("attempt_id", "case_attempts"), ("learning_task_id", "learning_tasks")):
            for identifier in deletions.get(table, []):
                connection.execute(f"UPDATE ai_call_logs SET {column}=NULL WHERE {column}=?", (identifier,))
        for table, ids in deletions.items():
            connection.executemany(f'DELETE FROM "{table}" WHERE id=?', [(value,) for value in ids])
        current = inventory(connection)
        for table, expected in fingerprints.items():
            if fingerprint([row for row in current[table] if row.get("id") in protected[table]]) != expected:
                raise RuntimeError(f"Protected records changed: {table}")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("Foreign key check failed")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {table: len(ids) for table, ids in deletions.items()}


def isolated_environment(path: Path):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("AI_", "PBL_", "COZE_", "WECHAT_"))}
    env.update(
        APP_ENV="test",
        DATABASE_URL=f"sqlite:///{path.as_posix()}",
        AI_ENABLED="false",
        PBL_AI_ENABLED="false",
        PBL_MOCK_ENABLED="false",
        SEED_SHOWCASE_CASE="false",
    )
    return env


def migrate_and_convert(path: Path):
    env = isolated_environment(path)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError("Migration failed; original backup retained")
    with connect(path) as db:
        removed = clean_retired_content(db)
    # Content-only seed: no old grades are relabelled and no synthetic learner result is inserted.
    code = (
        "from app.bootstrap import model_registry; from app.db import SessionLocal; "
        "from app.bootstrap.seed import seed_showcase_case; "
        "s=SessionLocal(); seed_showcase_case(s); s.close()"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError("Pathology seeding failed; restore the verified backup")
    with connect(path, readonly=True) as db:
        if (
            db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
            or db.execute("PRAGMA foreign_key_check").fetchall()
        ):
            raise RuntimeError("Post-conversion database validation failed")
        return {"removed": removed, "counts": {k: len(v) for k, v in inventory(db).items()}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEVELOPMENT_DB)
    parser.add_argument("--rehearse", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-development", action="store_true")
    args = parser.parse_args()
    path = args.database.resolve(strict=True)
    if args.database.is_symlink() or any(p.is_symlink() for p in args.database.parents):
        raise ValueError("Linked paths are not allowed")
    if args.apply and (path != DEVELOPMENT_DB.resolve(strict=True) or not args.confirm_development):
        raise ValueError("Apply requires the verified local dev.db and --confirm-development")
    with connect(path, readonly=True) as db:
        deletions, _, _ = plan_conversion(db)
        print(
            json.dumps(
                {"mode": "preview", "delete_counts": {k: len(v) for k, v in deletions.items()}}, ensure_ascii=True
            )
        )
    if not args.rehearse and not args.apply:
        return
    from app.testing_resources import assert_owned_resource, cleanup_managed_database, create_managed_database

    resource = create_managed_database("t11-rehearsal")
    assert_owned_resource(resource)
    backup_verified(path, resource.database_path)
    try:
        result = migrate_and_convert(resource.database_path)
        print(json.dumps({"mode": "rehearsal", "restore_verified": True, **result}, ensure_ascii=True))
    except Exception:
        print("Rehearsal failed; source database unchanged")
        raise
    finally:
        cleanup_managed_database(resource)
    if not args.apply:
        return
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    backup = BACKEND.parent / f"output/t11/backups/dev-{stamp}.sqlite3"
    backup_verified(path, backup)
    try:
        result = migrate_and_convert(path)
    except Exception:
        with connect(backup, readonly=True) as saved, connect(path) as target:
            saved.backup(target)
        raise
    print(json.dumps({"mode": "applied", "backup": str(backup), "restore_verified": True, **result}, ensure_ascii=True))


if __name__ == "__main__":
    main()
