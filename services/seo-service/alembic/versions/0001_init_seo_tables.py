"""init seo tables

Revision ID: 0001_init_seo_tables
Revises:
Create Date: 2026-04-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_init_seo_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # city
    op.create_table(
        "city",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("pinyin", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_city_slug", "city", ["slug"])

    # district
    op.create_table(
        "district",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "landmarks",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="'[]'",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["city_id"], ["city.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "slug", name="uq_district_city_slug"),
    )
    op.create_index("ix_district_city_id", "district", ["city_id"])

    # service
    op.create_table(
        "service",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="'[]'",
            nullable=False,
        ),
        sa.Column("base_price", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_service_slug", "service", ["slug"])

    # seo_page
    op.create_table(
        "seo_page",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("district_id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("h1", sa.String(), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(), server_default="draft", nullable=False),
        sa.Column("generation_count", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(["city_id"], ["city.id"]),
        sa.ForeignKeyConstraint(["district_id"], ["district.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["service.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("city_id", "district_id", "service_id", name="uq_seo_page_combination"),
    )
    op.create_index("ix_seo_page_slug", "seo_page", ["slug"])
    op.create_index("ix_seo_page_city_id", "seo_page", ["city_id"])
    op.create_index("ix_seo_page_district_id", "seo_page", ["district_id"])
    op.create_index("ix_seo_page_service_id", "seo_page", ["service_id"])
    op.create_index("ix_seo_page_status", "seo_page", ["status"])

    # generation_job
    op.create_table(
        "generation_job",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "error_log",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="'[]'",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generation_job_status", "generation_job", ["status"])


def downgrade() -> None:
    op.drop_index("ix_generation_job_status", table_name="generation_job")
    op.drop_table("generation_job")
    op.drop_index("ix_seo_page_status", table_name="seo_page")
    op.drop_index("ix_seo_page_service_id", table_name="seo_page")
    op.drop_index("ix_seo_page_district_id", table_name="seo_page")
    op.drop_index("ix_seo_page_city_id", table_name="seo_page")
    op.drop_index("ix_seo_page_slug", table_name="seo_page")
    op.drop_table("seo_page")
    op.drop_index("ix_service_slug", table_name="service")
    op.drop_table("service")
    op.drop_index("ix_district_city_id", table_name="district")
    op.drop_table("district")
    op.drop_index("ix_city_slug", table_name="city")
    op.drop_table("city")
