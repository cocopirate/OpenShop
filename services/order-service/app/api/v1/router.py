from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


@router.post("/orders", summary="创建订单")
async def create_order():
    return {"order_id": "ORD-001", "status": "pending_payment"}


@router.get("/orders/{order_id}", summary="获取订单详情")
async def get_order(order_id: str):
    return {"order_id": order_id, "status": "pending_payment", "items": []}


@router.get("/orders", summary="查询订单列表")
async def list_orders(user_id: Optional[str] = Query(None), page: int = 1, size: int = 20):
    return {"items": [], "total": 0, "page": page, "size": size}
