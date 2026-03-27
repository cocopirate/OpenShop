import json

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from app.core.config import settings
from app.core.redis import get_redis

# Public paths that don't need auth
PUBLIC_PATHS = {
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/admin/login"),
    ("POST", "/api/auth/consumer/login"),
    ("POST", "/api/auth/merchant/login"),
    ("POST", "/api/auth/merchant-sub/login"),
    ("POST", "/api/auth/staff/login"),
    ("POST", "/api/auth/register/consumer"),
    ("GET", "/health"),
    ("GET", "/health/ready"),
    ("GET", "/metrics"),
}

# Permission map: (method, path_prefix) → permission_code
PERMISSION_MAP = {
    ("GET", "/api/admins"): "user:list",
    ("POST", "/api/admins"): "user:create",
    ("PUT", "/api/admins"): "user:update",
    ("DELETE", "/api/admins"): "user:delete",
    ("GET", "/api/users"): "user:list",
    ("POST", "/api/users"): "user:create",
    ("PUT", "/api/users"): "user:update",
    ("DELETE", "/api/users"): "user:delete",
    ("GET", "/api/roles"): "role:list",
    ("POST", "/api/roles"): "role:create",
    ("PUT", "/api/roles"): "role:update",
    ("DELETE", "/api/roles"): "role:delete",
    ("GET", "/api/permissions"): "permission:list",
    ("POST", "/api/permissions"): "permission:create",
    ("GET", "/api/orders"): "order:list",
    ("POST", "/api/orders"): "order:create",
    ("GET", "/api/products"): "product:list",
    ("POST", "/api/products"): "product:create",
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
