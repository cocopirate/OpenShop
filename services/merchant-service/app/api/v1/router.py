from fastapi import APIRouter

router = APIRouter()


@router.post("/merchants", summary="商家入驻申请")
async def create_merchant():
    return {"message": "merchant application submitted"}


@router.get("/merchants/{merchant_id}", summary="获取商家信息")
async def get_merchant(merchant_id: str):
    return {"merchant_id": merchant_id}


@router.get("/merchants/{merchant_id}/shops", summary="获取商家店铺列表")
async def get_merchant_shops(merchant_id: str):
    return {"merchant_id": merchant_id, "shops": []}
