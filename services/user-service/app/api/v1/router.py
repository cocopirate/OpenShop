from fastapi import APIRouter

from app.api.v1 import auth, permissions, roles, users

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(roles.router, prefix="/roles", tags=["roles"])
router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
