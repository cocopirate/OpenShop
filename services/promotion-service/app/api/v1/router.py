from fastapi import APIRouter

router = APIRouter()


@router.get("/promotions/coupons/{code}/validate", summary="校验优惠券")
async def validate_coupon(code: str, user_id: str):
    return {"code": code, "valid": True, "discount": 0.0}


@router.post("/promotions/coupons/{code}/redeem", summary="核销优惠券")
async def redeem_coupon(code: str):
    return {"code": code, "redeemed": True}


@router.get("/promotions/flash-sales", summary="获取秒杀活动列表")
async def list_flash_sales():
    return {"items": []}
