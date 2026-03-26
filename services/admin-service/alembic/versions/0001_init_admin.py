"""initial admin schema

Revision ID: 0001_init_admin
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_init_admin"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # admin_permission
    op.create_table(
        "admin_permission",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("perm_code", sa.String(length=100), nullable=False),
        sa.Column("perm_name", sa.String(length=100), nullable=False),
        sa.Column("perm_type", sa.SmallInteger(), nullable=True),
        sa.Column("path", sa.String(length=255), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("perm_code"),
    )
    op.create_index("ix_admin_permission_perm_code", "admin_permission", ["perm_code"], unique=True)

    # admin_role
    op.create_table(
        "admin_role",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("role_code", sa.String(length=50), nullable=False),
        sa.Column("role_name", sa.String(length=100), nullable=False),
        sa.Column("is_system", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_code"),
    )
    op.create_index("ix_admin_role_role_code", "admin_role", ["role_code"], unique=True)

    # admin_account
    op.create_table(
        "admin_account",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("real_name", sa.String(length=50), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("last_login_ip", sa.String(length=45), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_admin_account_username", "admin_account", ["username"], unique=True)
    op.create_index("ix_admin_account_public_id", "admin_account", ["public_id"], unique=True)

    # admin_role_permission association
    op.create_table(
        "admin_role_permission",
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["admin_permission.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["admin_role.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    # admin_account_role association
    op.create_table(
        "admin_account_role",
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_account.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["admin_role.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("admin_id", "role_id"),
    )

    # admin_operation_log
    op.create_table(
        "admin_operation_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("admin_name", sa.String(length=50), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=True),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.BigInteger(), nullable=True),
        sa.Column("request_body", sa.Text(), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_operation_log_admin_id", "admin_operation_log", ["admin_id"])
    op.create_index("ix_admin_operation_log_created_at", "admin_operation_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_operation_log_created_at", table_name="admin_operation_log")
    op.drop_index("ix_admin_operation_log_admin_id", table_name="admin_operation_log")
    op.drop_table("admin_operation_log")
    op.drop_table("admin_account_role")
    op.drop_table("admin_role_permission")
    op.drop_index("ix_admin_account_public_id", table_name="admin_account")
    op.drop_index("ix_admin_account_username", table_name="admin_account")
    op.drop_table("admin_account")
    op.drop_index("ix_admin_role_role_code", table_name="admin_role")
    op.drop_table("admin_role")
    op.drop_index("ix_admin_permission_perm_code", table_name="admin_permission")
    op.drop_table("admin_permission")
