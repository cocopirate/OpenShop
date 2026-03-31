"""initial git aggregator schema

Revision ID: 0001_init_git_aggregator
Revises:
Create Date: 2026-03-31 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_init_git_aggregator"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # repositories
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("webhook_token", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uk_repo_name"),
    )

    # commits
    op.create_table(
        "commits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=True),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("author_name", sa.String(length=100), nullable=True),
        sa.Column("author_email", sa.String(length=100), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("branch", sa.String(length=255), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("commit_sha", name="uk_commit_sha"),
    )
    op.create_index("idx_commits_repo_time", "commits", ["repo_id", sa.text("committed_at DESC")])
    op.create_index("idx_commits_author", "commits", ["author_email"])

    # commit_files
    op.create_table(
        "commit_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("commit_id", sa.Integer(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("change_type", sa.String(length=10), nullable=True),
        sa.Column("additions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deletions", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["commit_id"], ["commits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("commit_files")
    op.drop_index("idx_commits_author", table_name="commits")
    op.drop_index("idx_commits_repo_time", table_name="commits")
    op.drop_table("commits")
    op.drop_table("repositories")
