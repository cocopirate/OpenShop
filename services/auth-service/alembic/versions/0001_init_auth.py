"""initial auth schema

Revision ID: 0001_init_auth
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_init_auth"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # auth_credential
    op.create_table(
        "auth_credential",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("identity", sa.String(length=100), nullable=False),
        sa.Column("identity_type", sa.SmallInteger(), nullable=False),
        sa.Column("credential", sa.String(length=255), nullable=True),
        sa.Column("account_type", sa.SmallInteger(), nullable=False),
        sa.Column("biz_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identity", "identity_type", "account_type", name="uk_identity"),
    )
    op.create_index("ix_auth_credential_identity", "auth_credential", ["identity"], unique=False)
    op.create_index("ix_auth_credential_biz_id", "auth_credential", ["biz_id"], unique=False)

    # auth_login_log
    op.create_table(
        "auth_login_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("biz_id", sa.BigInteger(), nullable=False),
        sa.Column("account_type", sa.SmallInteger(), nullable=False),
        sa.Column("login_ip", sa.String(length=45), nullable=True),
        sa.Column("device_info", sa.String(length=255), nullable=True),
        sa.Column(
            "login_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("result", sa.SmallInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_login_log_biz_id", "auth_login_log", ["biz_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_login_log_biz_id", table_name="auth_login_log")
    op.drop_table("auth_login_log")
    op.drop_index("ix_auth_credential_biz_id", table_name="auth_credential")
    op.drop_index("ix_auth_credential_identity", table_name="auth_credential")
    op.drop_table("auth_credential")
