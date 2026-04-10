"""init ai service tables

Revision ID: 0001_init_ai_tables
Revises:
Create Date: 2026-04-10 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_init_ai_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # prompt_template
    op.create_table(
        "prompt_template",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("provider", sa.String(), server_default="openai", nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt_template", sa.Text(), nullable=False),
        sa.Column("temperature", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("max_tokens", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("response_format", sa.String(), server_default="text", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", "version", name="uq_prompt_template_key_version"),
    )
    op.create_index("ix_prompt_template_key", "prompt_template", ["key"])
    op.create_index("ix_prompt_template_is_active", "prompt_template", ["is_active"])

    # call_log
    op.create_table(
        "call_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("caller_service", sa.String(), nullable=False),
        sa.Column("caller_ref_id", sa.String(), nullable=True),
        sa.Column("template_key", sa.String(), nullable=True),
        sa.Column("template_version", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("request_hash", sa.String(), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_call_log_caller_service", "call_log", ["caller_service"])
    op.create_index("ix_call_log_template_key", "call_log", ["template_key"])
    op.create_index("ix_call_log_status", "call_log", ["status"])
    op.create_index("ix_call_log_created_at", "call_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_call_log_created_at", table_name="call_log")
    op.drop_index("ix_call_log_status", table_name="call_log")
    op.drop_index("ix_call_log_template_key", table_name="call_log")
    op.drop_index("ix_call_log_caller_service", table_name="call_log")
    op.drop_table("call_log")
    op.drop_index("ix_prompt_template_is_active", table_name="prompt_template")
    op.drop_index("ix_prompt_template_key", table_name="prompt_template")
    op.drop_table("prompt_template")
