#!/usr/bin/env python
"""Seed SMS templates into the database.

Usage (from the sms-service root):
    python scripts/seed_templates.py [--provider aliyun_phone_svc]

Options:
    --provider   Only seed templates for this provider (default: all).
    --dry-run    Print what would be inserted without writing to the database.

The script is idempotent: existing rows matched by provider_template_id are
skipped (no update, no error).
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Allow running from the service root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.sms_template import SmsTemplate

# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

TEMPLATES: list[dict] = [
    # ── Aliyun Phone Number Service (号码认证服务) ──────────────────────────
    {
        "provider_template_id": "100001",
        "name": "登录/注册验证码",
        "content": (
            "您的验证码为${code}。"
            "尊敬的客户，以上验证码${min}分钟内有效，请注意保密，切勿告知他人。"
        ),
        "provider": "aliyun_phone_svc",
        "is_active": True,
    },
    {
        "provider_template_id": "100002",
        "name": "修改绑定手机号验证码",
        "content": (
            "尊敬的客户，您正在进行修改手机号操作，您的验证码为${code}。"
            "以上验证码${min}分钟内有效，请注意保密，切勿告知他人。"
        ),
        "provider": "aliyun_phone_svc",
        "is_active": True,
    },
    {
        "provider_template_id": "100003",
        "name": "重置密码验证码",
        "content": (
            "尊敬的客户，您正在进行重置密码操作，您的验证码为${code}。"
            "以上验证码${min}分钟内有效，请注意保密，切勿告知他人。"
        ),
        "provider": "aliyun_phone_svc",
        "is_active": True,
    },
    {
        "provider_template_id": "100004",
        "name": "绑定新手机号验证码",
        "content": (
            "尊敬的客户，您正在进行绑定手机号操作，您的验证码为${code}。"
            "以上验证码${min}分钟内有效，请注意保密，切勿告知他人。"
        ),
        "provider": "aliyun_phone_svc",
        "is_active": True,
    },
    {
        "provider_template_id": "100005",
        "name": "验证绑定手机号验证码",
        "content": (
            "尊敬的客户，您正在验证绑定手机号操作，您的验证码为${code}。"
            "以上验证码${min}分钟内有效，请注意保密，切勿告知他人。"
        ),
        "provider": "aliyun_phone_svc",
        "is_active": True,
    },
]


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------


async def seed(provider_filter: str | None, dry_run: bool) -> None:
    templates = TEMPLATES
    if provider_filter:
        templates = [t for t in templates if t["provider"] == provider_filter]

    if not templates:
        print(f"No templates matched provider filter: {provider_filter!r}")
        return

    async with AsyncSessionLocal() as session:
        inserted = skipped = 0
        for tpl in templates:
            result = await session.execute(
                select(SmsTemplate).where(
                    SmsTemplate.provider_template_id == tpl["provider_template_id"]
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(
                    f"  [skip]   {tpl['provider_template_id']}  {tpl['name']} (already exists)"
                )
                skipped += 1
                continue

            print(
                f"  [insert] {tpl['provider_template_id']}  {tpl['name']}"
                + (" (dry-run)" if dry_run else "")
            )
            if not dry_run:
                session.add(SmsTemplate(**tpl))
            inserted += 1

        if not dry_run:
            await session.commit()

    print(
        f"\nDone: {inserted} inserted, {skipped} skipped"
        + (" (dry-run, no changes written)" if dry_run else "")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed SMS templates")
    parser.add_argument("--provider", default=None, help="Only seed this provider")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without writing to DB"
    )
    args = parser.parse_args()

    asyncio.run(seed(provider_filter=args.provider, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
