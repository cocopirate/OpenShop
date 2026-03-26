"""consumer accounts: replace RBAC tables with consumer_account and consumer_address

Revision ID: 0003_consumer_accounts
Revises: 0002_add_public_id
Create Date: 2024-01-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_consumer_accounts"
down_revision: Union[str, None] = "0002_add_public_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Create new consumer tables                                           #
    # ------------------------------------------------------------------ #

    op.create_table(
        "consumer_account",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nickname", sa.String(length=50), nullable=True),
        sa.Column("avatar_url", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("gender", sa.SmallInteger(), nullable=True),
        sa.Column("birthday", sa.Date(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("phone"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_consumer_account_public_id", "consumer_account", ["public_id"], unique=True)
    op.create_index("ix_consumer_account_phone", "consumer_account", ["phone"], unique=True)
    op.create_index("ix_consumer_account_email", "consumer_account", ["email"], unique=True)

    op.create_table(
        "consumer_address",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("consumer_id", sa.BigInteger(), nullable=False),
        sa.Column("receiver", sa.String(length=50), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("province", sa.String(length=50), nullable=True),
        sa.Column("city", sa.String(length=50), nullable=True),
        sa.Column("district", sa.String(length=50), nullable=True),
        sa.Column("detail", sa.String(length=255), nullable=True),
        sa.Column("is_default", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["consumer_id"], ["consumer_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consumer_address_consumer_id", "consumer_address", ["consumer_id"])

    # ------------------------------------------------------------------ #
    # Drop old RBAC tables (order matters due to FK constraints)          #
    # ------------------------------------------------------------------ #

    op.drop_table("admin_user_roles")
    op.drop_table("role_permissions")
    op.drop_index("ix_admin_users_public_id", table_name="admin_users")
    op.drop_index("ix_admin_users_username", table_name="admin_users")
    op.drop_table("admin_users")
    op.execute("DROP TYPE IF EXISTS adminuserstatus")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")
    op.execute("DROP TYPE IF EXISTS permissiontype")


def downgrade() -> None:
    # Restore RBAC tables
    op.create_table(
        "permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("type", sa.Enum("menu", "api", name="permissiontype"), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=True),
        sa.Column("path", sa.String(length=256), nullable=True),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["permissions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("desc", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    op.create_table(
        "admin_users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("hashed_password", sa.String(length=256), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "disabled", name="adminuserstatus"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_admin_users_username", "admin_users", ["username"], unique=True)
    op.create_index("ix_admin_users_public_id", "admin_users", ["public_id"], unique=True)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.create_table(
        "admin_user_roles",
        sa.Column("admin_user_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("admin_user_id", "role_id"),
    )

    # Drop consumer tables
    op.drop_index("ix_consumer_address_consumer_id", table_name="consumer_address")
    op.drop_table("consumer_address")
    op.drop_index("ix_consumer_account_email", table_name="consumer_account")
    op.drop_index("ix_consumer_account_phone", table_name="consumer_account")
    op.drop_index("ix_consumer_account_public_id", table_name="consumer_account")
    op.drop_table("consumer_account")
