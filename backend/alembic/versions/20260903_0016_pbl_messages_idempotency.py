"""Normalize PBL messages and make student submissions idempotent.

Revision ID: 20260903_0016
Revises: 20260903_0015
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260903_0016"
down_revision = "20260903_0015"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if "pbl_participations" not in _table_names():
        return
    if "pbl_messages" not in _table_names():
        op.create_table(
            "pbl_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "participation_id",
                sa.Integer(),
                sa.ForeignKey("pbl_participations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("client_message_id", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("participation_id", "client_message_id", name="uq_pbl_message_client_id"),
            sa.UniqueConstraint("participation_id", "sequence", name="uq_pbl_message_sequence"),
        )
        op.create_index("ix_pbl_messages_participation_sequence", "pbl_messages", ["participation_id", "sequence"])

    if "messages" not in _column_names("pbl_participations"):
        return
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, messages FROM pbl_participations")).mappings()
    messages = sa.table(
        "pbl_messages",
        sa.column("participation_id", sa.Integer()),
        sa.column("sequence", sa.Integer()),
        sa.column("role", sa.String()),
        sa.column("content", sa.Text()),
        sa.column("client_message_id", sa.String()),
    )
    for row in rows:
        history = row["messages"]
        if isinstance(history, str):
            try:
                history = json.loads(history)
            except json.JSONDecodeError:
                history = []
        if not isinstance(history, list):
            continue
        for sequence, item in enumerate(history, start=1):
            if not isinstance(item, dict) or not str(item.get("content", "")).strip():
                continue
            bind.execute(
                messages.insert().values(
                    participation_id=row["id"],
                    sequence=sequence,
                    role=str(item.get("role", "student"))[:20],
                    content=str(item["content"])[:4000],
                    client_message_id=(str(item["client_message_id"])[:100] if item.get("client_message_id") else None),
                )
            )
    with op.batch_alter_table("pbl_participations") as batch:
        batch.drop_column("messages")


def downgrade() -> None:
    if "pbl_participations" not in _table_names():
        return
    if "messages" not in _column_names("pbl_participations"):
        with op.batch_alter_table("pbl_participations") as batch:
            batch.add_column(sa.Column("messages", sa.JSON(), nullable=True))
    if "pbl_messages" not in _table_names():
        return
    bind = op.get_bind()
    history_column = sa.table("pbl_participations", sa.column("id", sa.Integer()), sa.column("messages", sa.JSON()))
    participants = bind.execute(sa.text("SELECT id FROM pbl_participations")).mappings()
    for participant in participants:
        rows = bind.execute(
            sa.text(
                "SELECT role, content, client_message_id FROM pbl_messages "
                "WHERE participation_id = :participation_id ORDER BY sequence"
            ),
            {"participation_id": participant["id"]},
        ).mappings()
        history = [
            {
                "role": row["role"],
                "content": row["content"],
                **({"client_message_id": row["client_message_id"]} if row["client_message_id"] else {}),
            }
            for row in rows
        ]
        bind.execute(history_column.update().where(history_column.c.id == participant["id"]).values(messages=history))
    with op.batch_alter_table("pbl_participations") as batch:
        batch.alter_column("messages", existing_type=sa.JSON(), nullable=False)
    op.drop_index("ix_pbl_messages_participation_sequence", table_name="pbl_messages")
    op.drop_table("pbl_messages")
