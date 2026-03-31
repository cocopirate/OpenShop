"""initial product schema

Revision ID: 0001_init_product
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001_init_product"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum types
    spu_status = sa.Enum("DRAFT", "ONLINE", "OFFLINE", name="spu_status")
    sku_status = sa.Enum("ENABLE", "DISABLE", name="sku_status")
    category_status = sa.Enum("ENABLE", "DISABLE", name="category_status")
    attribute_type = sa.Enum("SALE", "SPEC", name="attribute_type")
    group_type = sa.Enum("MANUAL", "RULE", name="group_type")
    group_status = sa.Enum("ENABLE", "DISABLE", name="group_status")

    spu_status.create(op.get_bind(), checkfirst=True)
    sku_status.create(op.get_bind(), checkfirst=True)
    category_status.create(op.get_bind(), checkfirst=True)
    attribute_type.create(op.get_bind(), checkfirst=True)
    group_type.create(op.get_bind(), checkfirst=True)
    group_status.create(op.get_bind(), checkfirst=True)

    # product_category
    op.create_table(
        "product_category",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("path", sa.String(length=500), nullable=False, server_default="/"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.Enum("ENABLE", "DISABLE", name="category_status"), nullable=False, server_default="ENABLE"),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_category_parent_id", "product_category", ["parent_id"], unique=False)

    # product_attribute
    op.create_table(
        "product_attribute",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.Enum("SALE", "SPEC", name="attribute_type"), nullable=False, server_default="SPEC"),
        sa.PrimaryKeyConstraint("id"),
    )

    # product_category_attribute
    op.create_table(
        "product_category_attribute",
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("attribute_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["attribute_id"], ["product_attribute.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["product_category.id"]),
        sa.PrimaryKeyConstraint("category_id", "attribute_id"),
        sa.UniqueConstraint("category_id", "attribute_id", name="uq_category_attribute"),
    )

    # product_spu
    op.create_table(
        "product_spu",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("brand_id", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("DRAFT", "ONLINE", "OFFLINE", name="spu_status"), nullable=False, server_default="DRAFT"),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_spu_category_id", "product_spu", ["category_id"], unique=False)

    # product_sku
    op.create_table(
        "product_sku",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("spu_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.Enum("ENABLE", "DISABLE", name="sku_status"), nullable=False, server_default="ENABLE"),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_sku_spu_id", "product_sku", ["spu_id"], unique=False)

    # product_group
    op.create_table(
        "product_group",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.Enum("MANUAL", "RULE", name="group_type"), nullable=False, server_default="MANUAL"),
        sa.Column("status", sa.Enum("ENABLE", "DISABLE", name="group_status"), nullable=False, server_default="ENABLE"),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # product_group_item
    op.create_table(
        "product_group_item",
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("spu_id", sa.BigInteger(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["group_id"], ["product_group.id"]),
        sa.PrimaryKeyConstraint("group_id", "spu_id"),
        sa.UniqueConstraint("group_id", "spu_id", name="uq_group_spu"),
    )


def downgrade() -> None:
    op.drop_table("product_group_item")
    op.drop_table("product_group")
    op.drop_table("product_sku")
    op.drop_table("product_spu")
    op.drop_table("product_category_attribute")
    op.drop_table("product_attribute")
    op.drop_index("ix_product_category_parent_id", table_name="product_category")
    op.drop_table("product_category")

    for enum_name in ["spu_status", "sku_status", "category_status", "attribute_type", "group_type", "group_status"]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
