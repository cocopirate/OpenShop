from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class BindRequest(BaseModel):
    phone_a: str
    phone_b: str
    order_id: str


@router.post("/virtual-numbers/bind", summary="创建号码绑定")
async def bind_number(req: BindRequest):
    return {"binding_id": "VN-001", "virtual_number": "+8613900000000", "expires_at": "2025-12-31T00:00:00Z"}


@router.delete("/virtual-numbers/{binding_id}", summary="释放号码绑定")
async def release_binding(binding_id: str):
    return {"binding_id": binding_id, "released": True}


@router.get("/virtual-numbers/{binding_id}/calls", summary="查询通话记录")
async def get_call_records(binding_id: str):
    return {"binding_id": binding_id, "records": []}
