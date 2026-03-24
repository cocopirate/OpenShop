from fastapi import APIRouter

router = APIRouter()


@router.post("/aftersale", summary="发起售后申请")
async def create_aftersale():
    return {"request_id": "AS-001", "status": "pending_review"}


@router.get("/aftersale/{request_id}", summary="查询售后详情")
async def get_aftersale(request_id: str):
    return {"request_id": request_id, "status": "pending_review"}


@router.put("/aftersale/{request_id}/approve", summary="审核通过售后")
async def approve_aftersale(request_id: str):
    return {"request_id": request_id, "status": "approved"}
