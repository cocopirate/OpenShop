"""Business logic for Attribute management."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribute import Attribute, CategoryAttribute
from app.schemas.attribute import AttributeCreate, CategoryAttributeCreate


async def get_attribute(db: AsyncSession, attribute_id: int) -> Attribute | None:
    result = await db.execute(select(Attribute).where(Attribute.id == attribute_id))
    return result.scalar_one_or_none()


async def list_attributes(db: AsyncSession) -> list[Attribute]:
    result = await db.execute(select(Attribute).order_by(Attribute.id))
    return list(result.scalars().all())


async def create_attribute(db: AsyncSession, data: AttributeCreate) -> Attribute:
    attr = Attribute(**data.model_dump())
    db.add(attr)
    await db.flush()
    await db.refresh(attr)
    return attr


async def bind_category_attribute(
    db: AsyncSession, category_id: int, data: CategoryAttributeCreate
) -> CategoryAttribute | None:
    # Check if binding already exists
    result = await db.execute(
        select(CategoryAttribute).where(
            CategoryAttribute.category_id == category_id,
            CategoryAttribute.attribute_id == data.attribute_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    binding = CategoryAttribute(category_id=category_id, attribute_id=data.attribute_id)
    db.add(binding)
    await db.flush()
    await db.refresh(binding)
    return binding


async def list_category_attributes(db: AsyncSession, category_id: int) -> list[Attribute]:
    result = await db.execute(
        select(Attribute)
        .join(CategoryAttribute, Attribute.id == CategoryAttribute.attribute_id)
        .where(CategoryAttribute.category_id == category_id)
        .order_by(Attribute.id)
    )
    return list(result.scalars().all())
