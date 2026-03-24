from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


@router.get("/products", summary="商品列表/搜索")
async def list_products(q: Optional[str] = Query(None), page: int = 1, size: int = 20):
    return {"items": [], "total": 0, "page": page, "size": size}


@router.post("/products", summary="创建商品")
async def create_product():
    return {"message": "product created"}


@router.get("/products/{product_id}", summary="获取商品详情")
async def get_product(product_id: str):
    return {"product_id": product_id}
