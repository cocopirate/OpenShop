"""add public_id to admin_users

Revision ID: 0002_add_public_id
Revises: 0001_init_rbac
Create Date: 2024-01-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_add_public_id"
down_revision: Union[str, None] = "0001_init_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add as nullable first to handle any existing rows
    op.add_column(
        "admin_users",
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # Populate existing rows with a random UUID (PostgreSQL built-in)
    op.execute("UPDATE admin_users SET public_id = gen_random_uuid() WHERE public_id IS NULL")
    # Now enforce NOT NULL and unique constraints
    op.alter_column("admin_users", "public_id", nullable=False)
    op.create_index("ix_admin_users_public_id", "admin_users", ["public_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_admin_users_public_id", table_name="admin_users")
    op.drop_column("admin_users", "public_id")
