from __future__ import annotations

import json
import structlog
from fastapi import HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.core.config import settings
from app.core.security import create_access_token, generate_refresh_token, hash_password, verify_password
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

# Sliding-window refresh token account types (TTL resets on each refresh)
_SLIDING_ACCOUNT_TYPES = {"consumer"}


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


async def _store_refresh_token(
    redis: Redis,
    rt: str,
    payload: dict,
    account_type: str,
    fixed_ttl_seconds: int | None = None,
) -> None:
    """Persist *rt* → JSON payload in Redis with the appropriate TTL.

    Consumer accounts use a sliding window (TTL resets on each exchange).
    All other account types use a fixed window (TTL never extends).
    ``fixed_ttl_seconds`` allows callers to preserve the remaining TTL on
    token rotation so the original absolute expiry is honoured.
    """
    key = f"rt:{rt}"
    value = json.dumps(payload)
    if account_type in _SLIDING_ACCOUNT_TYPES:
        ttl = settings.REFRESH_TOKEN_CONSUMER_TTL_DAYS * 86400
    else:
        ttl = fixed_ttl_seconds if fixed_ttl_seconds is not None else settings.REFRESH_TOKEN_ADMIN_TTL_DAYS * 86400
    await redis.set(key, value, ex=ttl)


async def _get_auth_version(redis: Redis, biz_id: int, account_type: int) -> int:
    """Get or initialise the auth version counter for token invalidation."""
    ver_key = f"user_perm_ver:{biz_id}"
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
) -> tuple[str, str]:
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
        "uid": str(cred.biz_id),
        "account_type": "consumer",
        "ver": ver,
    })
    rt = generate_refresh_token()
    await _store_refresh_token(redis, rt, {
        "biz_id": cred.biz_id,
        "account_type": "consumer",
        "ver": ver,
    }, "consumer")
    await _log_attempt(db, cred.biz_id, ACCOUNT_CONSUMER, ip, device_info, 1)
    return token, rt


# --------------------------------------------------------------------------- #
# Merchant login                                                                #
# --------------------------------------------------------------------------- #


async def login_merchant(
    db: AsyncSession,
    redis: Redis,
    request: Request,
    phone: str,
    password: str,
) -> tuple[str, str, str]:
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
        "uid": str(cred.biz_id),
        "account_type": "merchant",
        "merchant_id": str(cred.biz_id),
        "ver": ver,
    })
    rt = generate_refresh_token()
    await _store_refresh_token(redis, rt, {
        "biz_id": cred.biz_id,
        "account_type": "merchant",
        "merchant_id": str(cred.biz_id),
        "ver": ver,
    }, "merchant")
    await _log_attempt(db, cred.biz_id, ACCOUNT_MERCHANT, ip, device_info, 1)
    return token, rt, str(cred.biz_id)


# --------------------------------------------------------------------------- #
# Merchant sub-account login                                                   #
# --------------------------------------------------------------------------- #


async def login_merchant_sub(
    db: AsyncSession,
    redis: Redis,
    request: Request,
    username: str,
    password: str,
) -> tuple[str, str, str, list[str]]:
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
        "uid": str(cred.biz_id),
        "account_type": "merchant_sub",
        "merchant_id": merchant_id,
        "permissions": permissions,
        "ver": ver,
    })
    rt = generate_refresh_token()
    await _store_refresh_token(redis, rt, {
        "biz_id": cred.biz_id,
        "account_type": "merchant_sub",
        "merchant_id": merchant_id,
        "permissions": permissions,
        "ver": ver,
    }, "merchant_sub")
    await _log_attempt(db, cred.biz_id, ACCOUNT_MERCHANT_SUB, ip, device_info, 1)
    return token, rt, merchant_id, permissions


# --------------------------------------------------------------------------- #
# Staff login                                                                   #
# --------------------------------------------------------------------------- #


async def login_staff(
    db: AsyncSession,
    redis: Redis,
    request: Request,
    phone: str,
    password: str,
) -> tuple[str, str]:
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
        "uid": str(cred.biz_id),
        "account_type": "merchant_staff",
        "merchant_id": merchant_id,
        "store_id": store_id,
        "job_type": job_type,
        "ver": ver,
    })
    rt = generate_refresh_token()
    await _store_refresh_token(redis, rt, {
        "biz_id": cred.biz_id,
        "account_type": "merchant_staff",
        "merchant_id": merchant_id,
        "store_id": store_id,
        "job_type": job_type,
        "ver": ver,
    }, "merchant_staff")
    await _log_attempt(db, cred.biz_id, ACCOUNT_STAFF, ip, device_info, 1)
    return token, rt


# --------------------------------------------------------------------------- #
# Admin login                                                                   #
# --------------------------------------------------------------------------- #


async def login_admin(
    db: AsyncSession,
    redis: Redis,
    request: Request,
    username: str,
    password: str,
) -> tuple[str, str]:
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
        "uid": str(cred.biz_id),
        "account_type": "admin",
        "permissions": permissions,
        "ver": ver,
    })
    rt = generate_refresh_token()
    await _store_refresh_token(redis, rt, {
        "biz_id": cred.biz_id,
        "account_type": "admin",
        "permissions": permissions,
        "ver": ver,
    }, "admin")
    await _log_attempt(db, cred.biz_id, ACCOUNT_ADMIN, ip, device_info, 1)
    return token, rt


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


async def logout_token(
    redis: Redis,
    token_payload: dict,
    refresh_token: str | None = None,
) -> None:
    biz_id = token_payload.get("sub")
    account_type_str = token_payload.get("account_type", "")

    if biz_id is None or account_type_str not in {
        "consumer", "merchant", "merchant_sub", "merchant_staff", "admin"
    }:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    ver_key = f"user_perm_ver:{biz_id}"
    await redis.incr(ver_key)
    await redis.expire(ver_key, AUTH_VERSION_TTL_SECONDS)

    if refresh_token:
        await redis.delete(f"rt:{refresh_token}")


# --------------------------------------------------------------------------- #
# Refresh token exchange                                                        #
# --------------------------------------------------------------------------- #


async def exchange_refresh_token(
    redis: Redis,
    refresh_token_str: str,
) -> tuple[str, str, dict]:
    """Validate *refresh_token_str*, rotate it, and issue a new access token.

    Returns (new_access_token, new_refresh_token, rt_payload).

    Rotation strategy:
    - Consumer: sliding window — new refresh token gets a full TTL reset.
    - All others: fixed window — new refresh token preserves the remaining TTL
      so the absolute 30-day expiry established at login is never extended.
    """
    key = f"rt:{refresh_token_str}"

    # Capture remaining TTL *before* any async gap
    remaining_ttl: int = await redis.ttl(key)
    raw = await redis.get(key)

    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalid or expired",
        )

    payload: dict = json.loads(raw)
    biz_id: int = int(payload["biz_id"])
    account_type: str = payload["account_type"]

    # Delete old token (rotation — one-time use)
    await redis.delete(key)

    # Re-read the live auth version so permissions/logout state is honoured
    ver = await _get_auth_version(redis, biz_id, 0)

    # Build new access-token claims, restoring optional extra fields
    claims: dict = {
        "sub": str(biz_id),
        "uid": str(biz_id),
        "account_type": account_type,
        "ver": ver,
    }
    for field in ("merchant_id", "permissions", "store_id", "job_type"):
        if field in payload:
            claims[field] = payload[field]

    new_access_token = create_access_token(claims)

    # Determine new refresh token TTL
    if account_type in _SLIDING_ACCOUNT_TYPES:
        new_ttl: int | None = None  # _store_refresh_token will use full consumer TTL
    else:
        # Fixed window: preserve remaining TTL; fall back to default if key had no TTL
        new_ttl = remaining_ttl if remaining_ttl > 0 else settings.REFRESH_TOKEN_ADMIN_TTL_DAYS * 86400

    new_rt = generate_refresh_token()
    new_rt_payload = {**payload, "ver": ver}
    await _store_refresh_token(redis, new_rt, new_rt_payload, account_type, fixed_ttl_seconds=new_ttl)

    return new_access_token, new_rt, payload


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

    payload = resp.json()
    # admin-service 使用统一响应包裹：{"code":0,"message":"success","data":{...}}
    data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
    if not isinstance(data, dict):
        return []
    permissions = data.get("permissions", [])
    return permissions if isinstance(permissions, list) else []


async def _verify_sms_code_via_service(phone: str, code: str) -> bool:
    """Call SMS service to verify an OTP code."""
    url = f"{settings.SMS_SERVICE_URL}/api/sms/verify"
    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_SERVICE_TIMEOUT) as client:
            resp = await client.post(url, json={"phone": phone, "code": code})
    except httpx.RequestError as exc:
        log.error("sms_service.unreachable", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMS service unavailable",
        ) from exc
    return resp.status_code == 200


async def _fetch_or_create_consumer_id(phone: str) -> int:
    """Get the consumer's integer ID from consumer-service, creating one if needed."""
    base_url = settings.CONSUMER_SERVICE_URL

    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_SERVICE_TIMEOUT) as client:
            resp = await client.get(f"{base_url}/internal/consumers/by-phone/{phone}")
    except httpx.RequestError as exc:
        log.error("consumer_service.unreachable", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Consumer service unavailable",
        ) from exc

    if resp.status_code == 200:
        data = resp.json()
        return int(data["data"]["id"])

    if resp.status_code == 404:
        # Consumer profile doesn't exist yet – create one
        try:
            async with httpx.AsyncClient(timeout=UPSTREAM_SERVICE_TIMEOUT) as client:
                resp = await client.post(
                    f"{base_url}/internal/consumers",
                    json={"phone": phone},
                )
        except httpx.RequestError as exc:
            log.error("consumer_service.unreachable", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Consumer service unavailable",
            ) from exc

        if resp.status_code == 201:
            data = resp.json()
            return int(data["data"]["id"])

        log.error("consumer_service.create_failed", status_code=resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to create consumer profile",
        )

    log.error("consumer_service.error", status_code=resp.status_code)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Consumer service returned an error",
    )


# --------------------------------------------------------------------------- #
# Consumer SMS login / auto-register                                           #
# --------------------------------------------------------------------------- #


async def login_or_register_consumer_by_sms(
    db: AsyncSession,
    redis: Redis,
    request: Request,
    phone: str,
    code: str,
) -> tuple[str, str]:
    """Verify SMS code then log in or auto-register the consumer.

    - If the SMS code is invalid, raises 422.
    - If no credential exists for the phone, creates a consumer profile in
      consumer-service and registers a credential with no password.
    - If a credential exists, validates account status and issues a JWT.
    """
    ip = _get_client_ip(request)
    device_info = request.headers.get("User-Agent")

    # Step 1: Verify the SMS code via SMS service
    if not await _verify_sms_code_via_service(phone, code):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid or expired verification code",
        )

    # Step 2: Look up existing credential
    cred = await _lookup_credential(db, phone, IDENTITY_PHONE, ACCOUNT_CONSUMER)

    if cred is None:
        # Step 3a: New user – create consumer profile + auth credential
        biz_id = await _fetch_or_create_consumer_id(phone)
        new_cred = AuthCredential(
            identity=phone,
            identity_type=IDENTITY_PHONE,
            # SMS-only accounts have no password credential; authentication is
            # always performed via OTP.  Users who want password login must set
            # a password separately through a dedicated endpoint.
            credential=None,
            account_type=ACCOUNT_CONSUMER,
            biz_id=biz_id,
            status=1,
        )
        db.add(new_cred)
        await db.flush()
        await db.refresh(new_cred)
        cred = new_cred
    else:
        # Step 3b: Existing user – check account status
        if cred.status != 1:
            await _log_attempt(db, cred.biz_id, ACCOUNT_CONSUMER, ip, device_info, 0)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

    # Step 4: Issue JWT token
    ver = await _get_auth_version(redis, cred.biz_id, ACCOUNT_CONSUMER)
    token = create_access_token({
        "sub": str(cred.biz_id),
        "uid": str(cred.biz_id),
        "account_type": "consumer",
        "ver": ver,
    })
    rt = generate_refresh_token()
    await _store_refresh_token(redis, rt, {
        "biz_id": cred.biz_id,
        "account_type": "consumer",
        "ver": ver,
    }, "consumer")
    await _log_attempt(db, cred.biz_id, ACCOUNT_CONSUMER, ip, device_info, 1)
    return token, rt
