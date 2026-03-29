"""add sms_policies, sms_channels, sms_client_keys tables; drop sms_config_store

Revision ID: 0004_policy_and_channel_tables
Revises: 0003_add_config_store
Create Date: 2024-07-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_policy_and_channel_tables"
down_revision: Union[str, None] = "0003_add_config_store"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sms_policies table
    op.create_table(
        "sms_policies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("code_ttl", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("rate_limit_phone_per_minute", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rate_limit_phone_per_day", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("rate_limit_ip_per_minute", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("rate_limit_ip_per_day", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("records_retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("failure_threshold", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("recovery_timeout", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("fallback_channel", sa.String(64), nullable=True),
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
    )
    op.create_index("ix_sms_policies_name", "sms_policies", ["name"], unique=True)

    # Create sms_channels table
    op.create_table(
        "sms_channels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("provider", sa.String(32), nullable=False, server_default="aliyun"),
        sa.Column("policy_name", sa.String(64), nullable=True),
        sa.Column("access_key_id", sa.String(256), nullable=True),
        sa.Column("access_key_secret", sa.String(256), nullable=True),
        sa.Column("sign_name", sa.String(64), nullable=True),
        sa.Column("endpoint", sa.String(256), nullable=True),
        sa.Column("account", sa.String(64), nullable=True),
        sa.Column("password", sa.String(256), nullable=True),
        sa.Column("api_url", sa.String(256), nullable=True),
        sa.Column("app_id", sa.String(64), nullable=True),
        sa.Column("secret_id", sa.String(256), nullable=True),
        sa.Column("secret_key", sa.String(256), nullable=True),
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
    )
    op.create_index("ix_sms_channels_name", "sms_channels", ["name"], unique=True)

    # Create sms_client_keys table
    op.create_table(
        "sms_client_keys",
        sa.Column("api_key", sa.String(128), primary_key=True, nullable=False),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Drop old config store table
    op.drop_table("sms_config_store")


def downgrade() -> None:
    # Re-create sms_config_store
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

    op.drop_table("sms_client_keys")
    op.drop_index("ix_sms_channels_name", table_name="sms_channels")
    op.drop_table("sms_channels")
    op.drop_index("ix_sms_policies_name", table_name="sms_policies")
    op.drop_table("sms_policies")
