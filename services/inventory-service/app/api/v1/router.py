from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class LockRequest(BaseModel):
    quantity: int
    order_id: str


@router.get("/inventory/{sku_id}", summary="查询 SKU 库存")
async def get_inventory(sku_id: str):
    return {"sku_id": sku_id, "available": 0, "locked": 0}


@router.post("/inventory/{sku_id}/lock", summary="锁定库存")
async def lock_inventory(sku_id: str, req: LockRequest):
    return {"sku_id": sku_id, "locked": req.quantity, "success": True}


@router.post("/inventory/{sku_id}/release", summary="释放库存")
async def release_inventory(sku_id: str, req: LockRequest):
    return {"sku_id": sku_id, "released": req.quantity, "success": True}
