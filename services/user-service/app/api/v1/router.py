from fastapi import APIRouter

router = APIRouter()


@router.post("/users", summary="创建用户")
async def create_user():
    return {"message": "user created"}


@router.get("/users/{user_id}", summary="获取用户信息")
async def get_user(user_id: str):
    return {"user_id": user_id}


@router.put("/users/{user_id}", summary="更新用户信息")
async def update_user(user_id: str):
    return {"user_id": user_id, "message": "updated"}


@router.get("/users/{user_id}/profile", summary="获取用户画像")
async def get_user_profile(user_id: str):
    return {"user_id": user_id, "profile": {}}
