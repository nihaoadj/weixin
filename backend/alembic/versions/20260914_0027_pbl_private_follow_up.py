"""Freeze completed PBL evidence and persist private follow-up turns."""

import sqlalchemy as sa

from alembic import op

revision = "20260914_0027"
down_revision = "20260914_0026"
branch_labels = None
depends_on = None


def _columns(bind, table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def _constraints(bind, table: str, kind: str) -> set[str]:
    inspector = sa.inspect(bind)
    values = (
        inspector.get_check_constraints(table)
        if kind == "check"
        else inspector.get_unique_constraints(table)
        if kind == "unique"
        else inspector.get_foreign_keys(table)
    )
    return {str(value["name"]) for value in values if value.get("name")}


def _backfill_completion_boundaries(bind, *, apply: bool = True) -> None:
    completed = bind.execute(
        sa.text("SELECT id FROM pbl_participations WHERE phase_status = 'completed' ORDER BY id")
    ).scalars().all()
    for participation_id in completed:
        snapshots = bind.execute(
            sa.text(
                "SELECT id, revision, status, assistant_reply FROM pbl_diagnostic_snapshots "
                "WHERE participation_id = :participation_id AND phase_decision = 'complete' ORDER BY id"
            ),
            {"participation_id": participation_id},
        ).mappings().all()
        if len(snapshots) != 1 or snapshots[0]["status"] != "ready":
            raise RuntimeError("T32 cannot uniquely establish a completed participation snapshot")
        snapshot = snapshots[0]
        student_messages = bind.execute(
            sa.text(
                "SELECT id, sequence, request_revision FROM pbl_messages "
                "WHERE participation_id = :participation_id AND role = 'student' "
                "AND result_snapshot_id = :snapshot_id ORDER BY id"
            ),
            {"participation_id": participation_id, "snapshot_id": snapshot["id"]},
        ).mappings().all()
        if len(student_messages) != 1 or student_messages[0]["request_revision"] != snapshot["revision"]:
            raise RuntimeError("T32 cannot uniquely locate the message that completed the evidence")
        student_message = student_messages[0]
        assistants = bind.execute(
            sa.text(
                "SELECT id FROM pbl_messages WHERE participation_id = :participation_id "
                "AND role = 'assistant' AND sequence = :sequence AND content = :assistant_reply ORDER BY id"
            ),
            {
                "participation_id": participation_id,
                "sequence": student_message["sequence"] + 1,
                "assistant_reply": snapshot["assistant_reply"],
            },
        ).scalars().all()
        if len(assistants) != 1:
            raise RuntimeError("T32 cannot uniquely locate the completed assistant reply")
        if apply:
            bind.execute(
                sa.text(
                    "UPDATE pbl_participations SET completion_snapshot_id = :snapshot_id, "
                    "evidence_completed_revision = :revision WHERE id = :participation_id"
                ),
                {
                    "snapshot_id": snapshot["id"],
                    "revision": snapshot["revision"],
                    "participation_id": participation_id,
                },
            )
            bind.execute(
                sa.text("UPDATE pbl_messages SET reply_to_message_id = :student_id WHERE id = :assistant_id"),
                {"student_id": student_message["id"], "assistant_id": assistants[0]},
            )


def upgrade():
    bind = op.get_bind()
    # SQLite DDL is non-transactional. Prove every historical completion boundary
    # before changing the schema so a rejected history remains cleanly at 0026.
    _backfill_completion_boundaries(bind, apply=False)
    participation_columns = _columns(bind, "pbl_participations")
    if "completion_snapshot_id" not in participation_columns:
        op.add_column("pbl_participations", sa.Column("completion_snapshot_id", sa.Integer(), nullable=True))
    if "evidence_completed_revision" not in participation_columns:
        op.add_column("pbl_participations", sa.Column("evidence_completed_revision", sa.Integer(), nullable=True))
    if "fk_pbl_participation_completion_snapshot" not in _constraints(bind, "pbl_participations", "foreign"):
        with op.batch_alter_table("pbl_participations") as batch:
            batch.create_foreign_key(
                "fk_pbl_participation_completion_snapshot",
                "pbl_diagnostic_snapshots",
                ["completion_snapshot_id"],
                ["id"],
                ondelete="SET NULL",
            )

    message_columns = _columns(bind, "pbl_messages")
    if "turn_scope" not in message_columns:
        op.add_column("pbl_messages", sa.Column("turn_scope", sa.String(30), nullable=True))
    if "reply_to_message_id" not in message_columns:
        op.add_column("pbl_messages", sa.Column("reply_to_message_id", sa.Integer(), nullable=True))
    bind.execute(sa.text("UPDATE pbl_messages SET turn_scope = 'evidence' WHERE turn_scope IS NULL"))
    _backfill_completion_boundaries(bind)

    message_checks = _constraints(bind, "pbl_messages", "check")
    message_uniques = _constraints(bind, "pbl_messages", "unique")
    message_foreign_keys = _constraints(bind, "pbl_messages", "foreign")
    with op.batch_alter_table("pbl_messages") as batch:
        batch.alter_column(
            "turn_scope", existing_type=sa.String(30), nullable=False, server_default="evidence"
        )
        if "ck_pbl_message_turn_scope" not in message_checks:
            batch.create_check_constraint(
                "ck_pbl_message_turn_scope", "turn_scope IN ('evidence', 'private_follow_up')"
            )
        if "fk_pbl_message_reply_to" not in message_foreign_keys:
            batch.create_foreign_key(
                "fk_pbl_message_reply_to", "pbl_messages", ["reply_to_message_id"], ["id"], ondelete="CASCADE"
            )
        if "uq_pbl_message_reply_to" not in message_uniques:
            batch.create_unique_constraint("uq_pbl_message_reply_to", ["reply_to_message_id"])
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("pbl_messages")}
    if "ix_pbl_messages_participation_scope_id" not in indexes:
        op.create_index(
            "ix_pbl_messages_participation_scope_id",
            "pbl_messages",
            ["participation_id", "turn_scope", "id"],
        )

    if "pbl_private_follow_up_results" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "pbl_private_follow_up_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "participation_id",
                sa.Integer(),
                sa.ForeignKey("pbl_participations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "student_message_id",
                sa.Integer(),
                sa.ForeignKey("pbl_messages.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "assistant_message_id",
                sa.Integer(),
                sa.ForeignKey("pbl_messages.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("interaction_style", sa.String(20), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("processing_status", sa.String(20), nullable=False),
            sa.Column("safety_status", sa.String(30), nullable=False),
            sa.Column("safety_notice", sa.String(500), nullable=True),
            sa.Column("provider_name", sa.String(40), nullable=False),
            sa.Column("provider_mode", sa.String(40), nullable=True),
            sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("failure_category", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "interaction_style IN ('guided', 'direct')", name="ck_pbl_private_follow_up_interaction_style"
            ),
            sa.CheckConstraint(
                "processing_status IN ('completed', 'unavailable')",
                name="ck_pbl_private_follow_up_processing_status",
            ),
            sa.UniqueConstraint("student_message_id", name="uq_pbl_private_follow_up_student_message"),
            sa.UniqueConstraint("assistant_message_id", name="uq_pbl_private_follow_up_assistant_message"),
        )
        op.create_index(
            "ix_pbl_private_follow_up_results_participation_id",
            "pbl_private_follow_up_results",
            ["participation_id"],
        )
        op.create_index(
            "ix_pbl_private_follow_up_participation_created",
            "pbl_private_follow_up_results",
            ["participation_id", "created_at"],
        )

    invalid = bind.scalar(
        sa.text(
            "SELECT COUNT(*) FROM pbl_participations WHERE "
            "(phase_status = 'completed' AND (completion_snapshot_id IS NULL OR evidence_completed_revision IS NULL)) "
            "OR (phase_status <> 'completed' AND "
            "(completion_snapshot_id IS NOT NULL OR evidence_completed_revision IS NOT NULL))"
        )
    )
    if invalid:
        raise RuntimeError("T32 completion boundary integrity check failed")


def downgrade():
    bind = op.get_bind()
    tables = sa.inspect(bind).get_table_names()
    if "pbl_private_follow_up_results" in tables and bind.scalar(
        sa.text("SELECT COUNT(*) FROM pbl_private_follow_up_results")
    ):
        raise RuntimeError("T32 private follow-up data exists; use a forward fix or verified backup")
    if "turn_scope" in _columns(bind, "pbl_messages") and bind.scalar(
        sa.text("SELECT COUNT(*) FROM pbl_messages WHERE turn_scope = 'private_follow_up'")
    ):
        raise RuntimeError("T32 private follow-up messages exist; use a forward fix or verified backup")

    if "pbl_private_follow_up_results" in tables:
        op.drop_index(
            "ix_pbl_private_follow_up_participation_created", table_name="pbl_private_follow_up_results"
        )
        op.drop_index(
            "ix_pbl_private_follow_up_results_participation_id", table_name="pbl_private_follow_up_results"
        )
        op.drop_table("pbl_private_follow_up_results")

    if "ix_pbl_messages_participation_scope_id" in {
        index["name"] for index in sa.inspect(bind).get_indexes("pbl_messages")
    }:
        op.drop_index("ix_pbl_messages_participation_scope_id", table_name="pbl_messages")
    with op.batch_alter_table("pbl_messages") as batch:
        if "uq_pbl_message_reply_to" in _constraints(bind, "pbl_messages", "unique"):
            batch.drop_constraint("uq_pbl_message_reply_to", type_="unique")
        if "fk_pbl_message_reply_to" in _constraints(bind, "pbl_messages", "foreign"):
            batch.drop_constraint("fk_pbl_message_reply_to", type_="foreignkey")
        if "ck_pbl_message_turn_scope" in _constraints(bind, "pbl_messages", "check"):
            batch.drop_constraint("ck_pbl_message_turn_scope", type_="check")
        if "reply_to_message_id" in _columns(bind, "pbl_messages"):
            batch.drop_column("reply_to_message_id")
        if "turn_scope" in _columns(bind, "pbl_messages"):
            batch.drop_column("turn_scope")

    with op.batch_alter_table("pbl_participations") as batch:
        if "fk_pbl_participation_completion_snapshot" in _constraints(
            bind, "pbl_participations", "foreign"
        ):
            batch.drop_constraint("fk_pbl_participation_completion_snapshot", type_="foreignkey")
        if "evidence_completed_revision" in _columns(bind, "pbl_participations"):
            batch.drop_column("evidence_completed_revision")
        if "completion_snapshot_id" in _columns(bind, "pbl_participations"):
            batch.drop_column("completion_snapshot_id")
