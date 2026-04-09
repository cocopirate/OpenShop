"""init lead tables

Revision ID: 0001_init_lead_tables
Revises:
Create Date: 2026-04-04 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_init_lead_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    leadstatus = sa.Enum("pending", "converted", "cancelled", name="leadstatus")
    leadoperatortype = sa.Enum("consumer", "merchant", "system", name="leadoperatortype")
    leadstatus.create(op.get_bind(), checkfirst=True)
    leadoperatortype.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "lead_order",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=False),
        sa.Column("district", sa.String(length=64), nullable=False),
        sa.Column("product_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "converted", "cancelled", name="leadstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("consumer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("converted_order_id", postgresql.UUID(as_uuid=True), nullable=True),
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
    op.create_index("ix_lead_order_phone", "lead_order", ["phone"])
    op.create_index("ix_lead_order_status", "lead_order", ["status"])
    op.create_index("ix_lead_order_consumer_id", "lead_order", ["consumer_id"])
    op.create_index("ix_lead_order_merchant_id", "lead_order", ["merchant_id"])

    op.create_table(
        "lead_status_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "from_status",
            sa.Enum("pending", "converted", "cancelled", name="leadstatus"),
            nullable=False,
        ),
        sa.Column(
            "to_status",
            sa.Enum("pending", "converted", "cancelled", name="leadstatus"),
            nullable=False,
        ),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "operator_type",
            sa.Enum("consumer", "merchant", "system", name="leadoperatortype"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["lead_order.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_status_log_lead_id", "lead_status_log", ["lead_id"])


def downgrade() -> None:
    op.drop_index("ix_lead_status_log_lead_id", table_name="lead_status_log")
    op.drop_table("lead_status_log")
    op.drop_index("ix_lead_order_merchant_id", table_name="lead_order")
    op.drop_index("ix_lead_order_consumer_id", table_name="lead_order")
    op.drop_index("ix_lead_order_status", table_name="lead_order")
    op.drop_index("ix_lead_order_phone", table_name="lead_order")
    op.drop_table("lead_order")
    op.execute("DROP TYPE IF EXISTS leadoperatortype")
    op.execute("DROP TYPE IF EXISTS leadstatus")
