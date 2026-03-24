"""initial: create sms_records and sms_templates tables

Revision ID: 0001_init
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- sms_templates ---
    op.create_table(
        "sms_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider_template_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.UniqueConstraint("provider_template_id"),
    )

    # --- sms_records ---
    op.create_table(
        "sms_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("template_id", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_message_id", sa.String(length=128), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "SENT", "DELIVERED", "FAILED", name="smsstatus"
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
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
    )
    op.create_index(
        "ix_sms_records_phone", "sms_records", ["phone"], unique=False
    )
    op.create_index(
        "ix_sms_records_phone_created_at",
        "sms_records",
        ["phone", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sms_records_phone_created_at", table_name="sms_records")
    op.drop_index("ix_sms_records_phone", table_name="sms_records")
    op.drop_table("sms_records")
    op.execute("DROP TYPE IF EXISTS smsstatus")
    op.drop_table("sms_templates")
