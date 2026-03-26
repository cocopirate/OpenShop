from fastapi import APIRouter

from app.api.v1 import admins, audit_logs, permissions, roles

router = APIRouter()
router.include_router(admins.router, prefix="/admins", tags=["admins"])
router.include_router(roles.router, prefix="/roles", tags=["roles"])
router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
