import json

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from app.core.config import settings
from app.core.redis import get_redis

# Permission map: (method, path_prefix) → permission_code
PERMISSION_MAP = {
    ("GET", "/api/admins"): "admin.admins.view",
    ("POST", "/api/admins"): "admin.admins.create",
    ("PUT", "/api/admins"): "admin.admins.update",
    ("DELETE", "/api/admins"): "admin.admins.delete",
    ("GET", "/api/users"): "admin.admins.view",
    ("POST", "/api/users"): "admin.admins.create",
    ("PUT", "/api/users"): "admin.admins.update",
    ("DELETE", "/api/users"): "admin.admins.delete",
    ("GET", "/api/roles"): "admin.roles.view",
    ("POST", "/api/roles"): "admin.roles.create",
    ("PUT", "/api/roles"): "admin.roles.update",
    ("DELETE", "/api/roles"): "admin.roles.delete",
    ("GET", "/api/permissions"): "admin.permissions.view",
    ("POST", "/api/permissions"): "admin.permissions.create",
    ("GET", "/api/orders"): "admin.orders.view",
    ("POST", "/api/orders"): "admin.orders.create",
    ("GET", "/api/products"): "admin.products.view",
    ("POST", "/api/products"): "admin.products.create",
}


async def verify_request(request: Request) -> dict:
    """
    Verify JWT token and check permissions.
    Returns the decoded token payload.
    Raises HTTPException on failure.
    """
    # Extract token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = auth_header[7:]

    # Decode JWT (validates signature + expiry)
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    uid = payload.get("uid")
    token_ver = payload.get("ver", 0)

    redis = get_redis()

    # Check user status
    user_status = await redis.get(f"user_status:{uid}")
    if user_status == "disabled":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is disabled")

    # Check permission version (token invalidation)
    redis_ver = await redis.get(f"user_perm_ver:{uid}")
    if redis_ver is not None and int(redis_ver) != token_ver:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalidated, please login again")

    # Check path permissions
    path = request.url.path
    method = request.method
    required_perm = _resolve_permission(method, path)

    if required_perm:
        permissions_raw = await redis.get(f"user_permissions:{uid}")
        if permissions_raw:
            permissions = json.loads(permissions_raw)
        else:
            permissions = payload.get("permissions", [])

        if "*" not in permissions and required_perm not in permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {required_perm}")

    return payload


def _resolve_permission(method: str, path: str) -> str | None:
    """Map (method, path) to a permission code. Returns None if no mapping found."""
    # Try exact match first
    if (method, path) in PERMISSION_MAP:
        return PERMISSION_MAP[(method, path)]

    # Try prefix match (e.g. /api/users/123 → /api/users)
    for (m, p), code in PERMISSION_MAP.items():
        if m == method and path.startswith(p + "/"):
            return code

    # Try base path match (strip trailing slash and query)
    base_path = path.rstrip("/").split("?")[0]
    for (m, p), code in PERMISSION_MAP.items():
        if m == method and base_path.startswith(p):
            return code

    return None
