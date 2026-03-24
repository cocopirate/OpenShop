from fastapi import APIRouter

router = APIRouter()


@router.get("/locations/addresses", summary="获取用户地址列表")
async def list_addresses(user_id: str):
    return {"user_id": user_id, "addresses": []}


@router.post("/locations/addresses", summary="新增收货地址")
async def create_address():
    return {"address_id": "ADDR-001", "message": "address created"}


@router.get("/locations/regions", summary="获取行政区划")
async def list_regions(parent_code: str = ""):
    return {"parent_code": parent_code, "regions": []}
