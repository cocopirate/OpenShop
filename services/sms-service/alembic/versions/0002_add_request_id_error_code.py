"""add request_id, phone_masked, error_code to sms_records

Revision ID: 0002_add_fields
Revises: 0001_init
Create Date: 2024-06-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_fields"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sms_records", sa.Column("request_id", sa.String(64), nullable=True))
    op.add_column("sms_records", sa.Column("phone_masked", sa.String(20), nullable=True))
    op.add_column("sms_records", sa.Column("error_code", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_sms_records_request_id", "sms_records", ["request_id"])
    op.create_index("ix_sms_records_request_id", "sms_records", ["request_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_sms_records_request_id", table_name="sms_records")
    op.drop_constraint("uq_sms_records_request_id", "sms_records", type_="unique")
    op.drop_column("sms_records", "error_code")
    op.drop_column("sms_records", "phone_masked")
    op.drop_column("sms_records", "request_id")
