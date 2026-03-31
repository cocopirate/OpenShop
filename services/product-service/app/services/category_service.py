"""Business logic for Category management."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category, CategoryStatus
from app.models.spu import Spu
from app.schemas.category import CategoryCreate, CategoryTreeNode, CategoryUpdate

MAX_CATEGORY_LEVEL = 3


async def get_category(db: AsyncSession, category_id: int) -> Category | None:
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def list_all_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category).order_by(Category.sort_order, Category.id))
    return list(result.scalars().all())


async def build_category_tree(categories: list[Category]) -> list[CategoryTreeNode]:
    """Convert flat list of categories into a tree structure."""
    node_map: dict[int, CategoryTreeNode] = {}
    roots: list[CategoryTreeNode] = []

    for cat in categories:
        node = CategoryTreeNode.model_validate(cat)
        node_map[cat.id] = node

    for cat in categories:
        node = node_map[cat.id]
        if cat.parent_id == 0:
            roots.append(node)
        elif cat.parent_id in node_map:
            node_map[cat.parent_id].children.append(node)

    return roots


async def create_category(db: AsyncSession, data: CategoryCreate) -> Category | tuple[None, str]:
    if data.parent_id != 0:
        parent = await get_category(db, data.parent_id)
        if not parent:
            return None, "parent_not_found"
        if parent.level >= MAX_CATEGORY_LEVEL:
            return None, "level_exceeded"
        level = parent.level + 1
        path = parent.path + str(data.parent_id) + "/"
    else:
        level = 1
        path = "/"

    category = Category(
        parent_id=data.parent_id,
        name=data.name,
        level=level,
        path=path,
        sort_order=data.sort_order,
        status=data.status,
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category, None


async def update_category(db: AsyncSession, category_id: int, data: CategoryUpdate) -> Category | None:
    category = await get_category(db, category_id)
    if not category:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(category, k, v)
    await db.flush()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category_id: int) -> tuple[bool, str | None]:
    category = await get_category(db, category_id)
    if not category:
        return False, "not_found"

    # Check if any SPU belongs to this category
    count_result = await db.execute(
        select(func.count()).select_from(Spu).where(Spu.category_id == category_id)
    )
    spu_count = count_result.scalar_one()
    if spu_count > 0:
        return False, "has_products"

    await db.delete(category)
    await db.flush()
    return True, None
