"""Business logic for consumer account CRUD."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consumer import ConsumerAccount
from app.schemas.consumer import ConsumerCreate, ConsumerUpdate


async def get_consumer(db: AsyncSession, public_id: UUID) -> Optional[ConsumerAccount]:
    result = await db.execute(
        select(ConsumerAccount).where(ConsumerAccount.public_id == public_id)
    )
    return result.scalar_one_or_none()


async def get_consumer_by_internal_id(db: AsyncSession, consumer_id: int) -> Optional[ConsumerAccount]:
    result = await db.execute(
        select(ConsumerAccount).where(ConsumerAccount.id == consumer_id)
    )
    return result.scalar_one_or_none()


async def get_consumer_by_phone(db: AsyncSession, phone: str) -> Optional[ConsumerAccount]:
    result = await db.execute(
        select(ConsumerAccount).where(ConsumerAccount.phone == phone)
    )
    return result.scalar_one_or_none()


async def create_consumer(db: AsyncSession, data: ConsumerCreate) -> ConsumerAccount:
    consumer = ConsumerAccount(
        nickname=data.nickname,
        phone=data.phone,
        email=data.email,
        avatar_url=data.avatar_url,
    )
    db.add(consumer)
    await db.flush()
    await db.refresh(consumer)
    return consumer


async def update_consumer(
    db: AsyncSession, public_id: UUID, data: ConsumerUpdate
) -> Optional[ConsumerAccount]:
    consumer = await get_consumer(db, public_id)
    if consumer is None:
        return None
    if data.nickname is not None:
        consumer.nickname = data.nickname
    if data.avatar_url is not None:
        consumer.avatar_url = data.avatar_url
    if data.gender is not None:
        consumer.gender = data.gender
    if data.birthday is not None:
        consumer.birthday = data.birthday
    await db.flush()
    await db.refresh(consumer)
    return consumer


async def adjust_points(
    db: AsyncSession, public_id: UUID, delta: int
) -> Optional[ConsumerAccount]:
    """Add or deduct points. Returns None if consumer not found."""
    consumer = await get_consumer(db, public_id)
    if consumer is None:
        return None
    consumer.points = consumer.points + delta
    await db.flush()
    await db.refresh(consumer)
    return consumer
