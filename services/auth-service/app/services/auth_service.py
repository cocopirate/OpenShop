from __future__ import annotations

import structlog
from fastapi import HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.credential import AuthCredential, AuthLoginLog

log = structlog.get_logger(__name__)

AUTH_VERSION_TTL_SECONDS = 86400  # 24 h
UPSTREAM_SERVICE_TIMEOUT = 5.0    # seconds

# account_type constants
ACCOUNT_CONSUMER = 1
ACCOUNT_MERCHANT = 2
ACCOUNT_MERCHANT_SUB = 3
ACCOUNT_STAFF = 4
ACCOUNT_ADMIN = 5

# identity_type constants
IDENTITY_PHONE = 1
IDENTITY_EMAIL = 2
IDENTITY_USERNAME = 3
IDENTITY_WECHAT = 4


def _get_client_ip(request: Request) -> str:
    """Extract client IP from X-Forwarded-For, X-Real-IP, or direct connection."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return ""


async def _get_auth_version(redis: Redis, biz_id: int, account_type: int) -> int:
    """Get or initialise the auth version counter for token invalidation."""
    ver_key = f"auth_ver:{biz_id}:{account_type}"
    ver = await redis.get(ver_key)
    if ver is None:
        await redis.set(ver_key, 0, ex=AUTH_VERSION_TTL_SECONDS)
        return 0
    return int(ver)


async def _log_attempt(
    db: AsyncSession,
    biz_id: int,
    account_type: int,
    login_ip: str,
    device_info: str | None,
    result: int,
) -> None:
    log_entry = AuthLoginLog(
        biz_id=biz_id,
        account_type=account_type,
        login_ip=login_ip,
        device_info=device_info,
        result=result,
    )
    db.add(log_entry)
    # Flush without committing — the caller's session commit will persist it.
    await db.flush()


async def _lookup_credential(
    db: AsyncSession,
    identity: str,
    identity_type: int,
    account_type: int,
) -> AuthCredential | None:
    result = await db.execute(
        select(AuthCredential).where(
            AuthCredential.identity == identity,
            AuthCredential.identity_type == identity_type,
            AuthCredential.account_type == account_type,
        )
    )
    return result.scalar_one_or_none()


# --------------------------------------------------------------------------- #
# Consumer login                                                                #
# --------------------------------------------------------------------------- #


async def login_consumer(
    db: AsyncSession,
    redis: Redis,
    request: Request,
    phone: str,
    password: str,
) -> str:
    ip = _get_client_ip(request)
    device_info = request.headers.get("User-Agent")

    cred = await _lookup_credential(db, phone, IDENTITY_PHONE, ACCOUNT_CONSUMER)
    if cred is None or not verify_password(password, cred.credential or ""):
        if cred is not None:
            await _log_attempt(db, cred.biz_id, ACCOUNT_CONSUMER, ip, device_info, 0)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone or password")

    if cred.status != 1:
        await _log_attempt(db, cred.biz_id, ACCOUNT_CONSUMER, ip, device_info, 0)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    ver = await _get_auth_version(redis, cred.biz_id, ACCOUNT_CONSUMER)
    token = create_access_token({
        "sub": str(cred.biz_id),
        "account_type": "consumer",
        "ver": ver,
    })
    await _log_attempt(db, cred.biz_id, ACCOUNT_CONSUMER, ip, device_info, 1)
    return token


# --------------------------------------------------------------------------- #
# Merchant login                                                                #
# --------------------------------------------------------------------------- #


async def login_merchant(
    db: AsyncSession,
    redis: Redis,
    request: Request,
    phone: str,
    password: str,
) -> tuple[str, str]:
    ip = _get_client_ip(request)
    device_info = request.headers.get("User-Agent")

    cred = await _lookup_credential(db, phone, IDENTITY_PHONE, ACCOUNT_MERCHANT)
    if cred is None or not verify_password(password, cred.credential or ""):
        if cred is not None:
            await _log_attempt(db, cred.biz_id, ACCOUNT_MERCHANT, ip, device_info, 0)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone or password")

    if cred.status != 1:
        await _log_attempt(db, cred.biz_id, ACCOUNT_MERCHANT, ip, device_info, 0)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    ver = await _get_auth_version(redis, cred.biz_id, ACCOUNT_MERCHANT)
    token = create_access_token({
        "sub": str(cred.biz_id),
        "account_type": "merchant",
        "merchant_id": str(cred.biz_id),
        "ver": ver,
    })
    await _log_attempt(db, cred.biz_id, ACCOUNT_MERCHANT, ip, device_info, 1)
    return token, str(cred.biz_id)


# --------------------------------------------------------------------------- #
# Merchant sub-account login                                                   #
# --------------------------------------------------------------------------- #


async def login_merchant_sub(
    db: AsyncSession,
    redis: Redis,
    request: Request,
    username: str,
    password: str,
) -> tuple[str, str, list[str]]:
    ip = _get_client_ip(request)
    device_info = request.headers.get("User-Agent")

    cred = await _lookup_credential(db, username, IDENTITY_USERNAME, ACCOUNT_MERCHANT_SUB)
    if cred is None or not verify_password(password, cred.credential or ""):
        if cred is not None:
            await _log_attempt(db, cred.biz_id, ACCOUNT_MERCHANT_SUB, ip, device_info, 0)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    if cred.status != 1:
        await _log_attempt(db, cred.biz_id, ACCOUNT_MERCHANT_SUB, ip, device_info, 0)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    # Fetch merchant_id + permissions from merchant-service
    merchant_id, permissions = await _fetch_sub_account_info(cred.biz_id)

    ver = await _get_auth_version(redis, cred.biz_id, ACCOUNT_MERCHANT_SUB)
    token = create_access_token({
        "sub": str(cred.biz_id),
        "account_type": "merchant_sub",
        "merchant_id": merchant_id,
        "permissions": permissions,
        "ver": ver,
    })
    await _log_attempt(db, cred.biz_id, ACCOUNT_MERCHANT_SUB, ip, device_info, 1)
    return token, merchant_id, permissions


# --------------------------------------------------------------------------- #
# Staff login                                                                   #
# --------------------------------------------------------------------------- #


async def login_staff(
    db: AsyncSession,
    redis: Redis,
    request: Request,
    phone: str,
    password: str,
) -> str:
    ip = _get_client_ip(request)
    device_info = request.headers.get("User-Agent")

    cred = await _lookup_credential(db, phone, IDENTITY_PHONE, ACCOUNT_STAFF)
    if cred is None or not verify_password(password, cred.credential or ""):
        if cred is not None:
            await _log_attempt(db, cred.biz_id, ACCOUNT_STAFF, ip, device_info, 0)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone or password")

    if cred.status != 1:
        await _log_attempt(db, cred.biz_id, ACCOUNT_STAFF, ip, device_info, 0)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    # Fetch merchant_id, store_id, job_type from merchant-service
    merchant_id, store_id, job_type = await _fetch_staff_info(cred.biz_id)

    ver = await _get_auth_version(redis, cred.biz_id, ACCOUNT_STAFF)
    token = create_access_token({
        "sub": str(cred.biz_id),
        "account_type": "merchant_staff",
        "merchant_id": merchant_id,
        "store_id": store_id,
        "job_type": job_type,
        "ver": ver,
    })
    await _log_attempt(db, cred.biz_id, ACCOUNT_STAFF, ip, device_info, 1)
    return token


# --------------------------------------------------------------------------- #
# Admin login                                                                   #
# --------------------------------------------------------------------------- #


async def login_admin(
    db: AsyncSession,
    redis: Redis,
    request: Request,
    username: str,
    password: str,
) -> tuple[str, list[str]]:
    ip = _get_client_ip(request)
    device_info = request.headers.get("User-Agent")

    cred = await _lookup_credential(db, username, IDENTITY_USERNAME, ACCOUNT_ADMIN)
    if cred is None or not verify_password(password, cred.credential or ""):
        if cred is not None:
            await _log_attempt(db, cred.biz_id, ACCOUNT_ADMIN, ip, device_info, 0)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    if cred.status != 1:
        await _log_attempt(db, cred.biz_id, ACCOUNT_ADMIN, ip, device_info, 0)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    # Fetch permissions from admin-service
    permissions = await _fetch_admin_permissions(cred.biz_id)

    ver = await _get_auth_version(redis, cred.biz_id, ACCOUNT_ADMIN)
    token = create_access_token({
        "sub": str(cred.biz_id),
        "account_type": "admin",
        "permissions": permissions,
        "ver": ver,
    })
    await _log_attempt(db, cred.biz_id, ACCOUNT_ADMIN, ip, device_info, 1)
    return token, permissions


# --------------------------------------------------------------------------- #
# Consumer registration                                                         #
# --------------------------------------------------------------------------- #


async def register_consumer(
    db: AsyncSession,
    phone: str,
    password: str,
    biz_id: int,
) -> None:
    existing = await _lookup_credential(db, phone, IDENTITY_PHONE, ACCOUNT_CONSUMER)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already registered")

    cred = AuthCredential(
        identity=phone,
        identity_type=IDENTITY_PHONE,
        credential=hash_password(password),
        account_type=ACCOUNT_CONSUMER,
        biz_id=biz_id,
        status=1,
    )
    db.add(cred)
    await db.flush()


# --------------------------------------------------------------------------- #
# Logout (Redis version bump)                                                   #
# --------------------------------------------------------------------------- #


async def logout_token(redis: Redis, token_payload: dict) -> None:
    biz_id = token_payload.get("sub")
    account_type_str = token_payload.get("account_type", "")

    _account_type_map = {
        "consumer": ACCOUNT_CONSUMER,
        "merchant": ACCOUNT_MERCHANT,
        "merchant_sub": ACCOUNT_MERCHANT_SUB,
        "merchant_staff": ACCOUNT_STAFF,
        "admin": ACCOUNT_ADMIN,
    }
    account_type_int = _account_type_map.get(account_type_str)
    if biz_id is None or account_type_int is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    ver_key = f"auth_ver:{biz_id}:{account_type_int}"
    await redis.incr(ver_key)
    await redis.expire(ver_key, AUTH_VERSION_TTL_SECONDS)


# --------------------------------------------------------------------------- #
# Upstream service helpers                                                      #
# --------------------------------------------------------------------------- #


async def _fetch_sub_account_info(biz_id: int) -> tuple[str, list[str]]:
    url = f"{settings.MERCHANT_SERVICE_URL}/internal/sub-accounts/{biz_id}"
    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_SERVICE_TIMEOUT) as client:
            resp = await client.get(url)
    except httpx.RequestError as exc:
        log.error("merchant_service.unreachable", biz_id=biz_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Merchant service unavailable",
        ) from exc

    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-account not found in merchant service",
        )
    if resp.status_code != 200:
        log.error("merchant_service.error", biz_id=biz_id, status_code=resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Merchant service returned an error",
        )

    data = resp.json()
    merchant_id = str(data.get("merchant_id", ""))
    permissions: list[str] = data.get("permissions", [])
    return merchant_id, permissions


async def _fetch_staff_info(biz_id: int) -> tuple[str, str, str]:
    url = f"{settings.MERCHANT_SERVICE_URL}/internal/staff/{biz_id}"
    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_SERVICE_TIMEOUT) as client:
            resp = await client.get(url)
    except httpx.RequestError as exc:
        log.error("merchant_service.unreachable", biz_id=biz_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Merchant service unavailable",
        ) from exc

    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff not found in merchant service",
        )
    if resp.status_code != 200:
        log.error("merchant_service.error", biz_id=biz_id, status_code=resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Merchant service returned an error",
        )

    data = resp.json()
    merchant_id = str(data.get("merchant_id", ""))
    store_id = str(data.get("store_id", ""))
    job_type = str(data.get("job_type", ""))
    return merchant_id, store_id, job_type


async def _fetch_admin_permissions(biz_id: int) -> list[str]:
    url = f"{settings.ADMIN_SERVICE_URL}/internal/admins/{biz_id}"
    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_SERVICE_TIMEOUT) as client:
            resp = await client.get(url)
    except httpx.RequestError as exc:
        log.error("admin_service.unreachable", biz_id=biz_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin service unavailable",
        ) from exc

    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found in admin service",
        )
    if resp.status_code != 200:
        log.error("admin_service.error", biz_id=biz_id, status_code=resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin service returned an error",
        )

    data = resp.json()
    return data.get("permissions", [])
