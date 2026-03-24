from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class CheckoutRequest(BaseModel):
    user_id: str
    items: list[dict]
    promotion_code: Optional[str] = None
    address_id: str


class CheckoutResponse(BaseModel):
    order_id: str
    status: str
    message: str


@router.post("/checkout", response_model=CheckoutResponse, summary="发起下单流程")
async def checkout(request: CheckoutRequest):
    # Saga orchestration: validate coupon -> lock inventory -> create order -> notify
    return CheckoutResponse(
        order_id="ORD-PLACEHOLDER",
        status="pending",
        message="订单创建中",
    )


@router.post("/orders/{order_id}/cancel", summary="取消订单（补偿流程）")
async def cancel_order(order_id: str):
    # Trigger compensation Saga
    return {"order_id": order_id, "status": "cancelling"}


@router.get("/orders/{order_id}/status", summary="查询订单编排状态")
async def get_order_status(order_id: str):
    return {"order_id": order_id, "status": "pending"}
