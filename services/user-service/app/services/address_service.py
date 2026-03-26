"""Business logic for consumer address CRUD."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consumer import ConsumerAddress
from app.schemas.consumer import AddressCreate, AddressUpdate


async def list_addresses(db: AsyncSession, consumer_id: int) -> list[ConsumerAddress]:
    result = await db.execute(
        select(ConsumerAddress).where(ConsumerAddress.consumer_id == consumer_id)
    )
    return list(result.scalars().all())


async def get_address(
    db: AsyncSession, consumer_id: int, addr_id: int
) -> Optional[ConsumerAddress]:
    result = await db.execute(
        select(ConsumerAddress).where(
            ConsumerAddress.id == addr_id,
            ConsumerAddress.consumer_id == consumer_id,
        )
    )
    return result.scalar_one_or_none()


async def create_address(
    db: AsyncSession, consumer_id: int, data: AddressCreate
) -> ConsumerAddress:
    if data.is_default == 1:
        await _clear_default(db, consumer_id)

    address = ConsumerAddress(
        consumer_id=consumer_id,
        receiver=data.receiver,
        phone=data.phone,
        province=data.province,
        city=data.city,
        district=data.district,
        detail=data.detail,
        is_default=data.is_default,
    )
    db.add(address)
    await db.flush()
    await db.refresh(address)
    return address


async def update_address(
    db: AsyncSession, consumer_id: int, addr_id: int, data: AddressUpdate
) -> Optional[ConsumerAddress]:
    address = await get_address(db, consumer_id, addr_id)
    if address is None:
        return None

    if data.is_default == 1:
        await _clear_default(db, consumer_id)

    if data.receiver is not None:
        address.receiver = data.receiver
    if data.phone is not None:
        address.phone = data.phone
    if data.province is not None:
        address.province = data.province
    if data.city is not None:
        address.city = data.city
    if data.district is not None:
        address.district = data.district
    if data.detail is not None:
        address.detail = data.detail
    if data.is_default is not None:
        address.is_default = data.is_default

    await db.flush()
    await db.refresh(address)
    return address


async def delete_address(db: AsyncSession, consumer_id: int, addr_id: int) -> bool:
    address = await get_address(db, consumer_id, addr_id)
    if address is None:
        return False
    await db.delete(address)
    await db.flush()
    return True


async def set_default_address(
    db: AsyncSession, consumer_id: int, addr_id: int
) -> Optional[ConsumerAddress]:
    address = await get_address(db, consumer_id, addr_id)
    if address is None:
        return None
    await _clear_default(db, consumer_id)
    address.is_default = 1
    await db.flush()
    await db.refresh(address)
    return address


async def _clear_default(db: AsyncSession, consumer_id: int) -> None:
    """Reset is_default=0 for all addresses of a consumer."""
    await db.execute(
        update(ConsumerAddress)
        .where(ConsumerAddress.consumer_id == consumer_id, ConsumerAddress.is_default == 1)
        .values(is_default=0)
    )
