"""add sms_config_store table

Revision ID: 0003_add_config_store
Revises: 0002_add_fields
Create Date: 2024-06-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_config_store"
down_revision: Union[str, None] = "0002_add_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sms_config_store",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("config_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("sms_config_store")
