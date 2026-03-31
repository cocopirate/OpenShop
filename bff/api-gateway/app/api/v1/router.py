from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
import httpx
import structlog

from app.core.auth import verify_request
from app.core.public_routes import public_routes_registry
from app.core.config import settings
from app.core.response import (
    ROUTE_NOT_FOUND,
    UPSTREAM_TIMEOUT,
    UPSTREAM_UNAVAILABLE,
    err,
    get_request_id,
)

router = APIRouter()
log = structlog.get_logger(__name__)

# Route prefix → upstream URL (longest prefix wins)
ROUTE_MAP = {
    "/api/auth": settings.AUTH_SERVICE_URL,
    "/api/admins": settings.ADMIN_SERVICE_URL,
    "/api/sms": settings.SMS_SERVICE_URL,
    "/api/consumers": settings.CONSUMER_SERVICE_URL,
    # BFF aggregation routes
    "/api/app": settings.APP_BFF_URL,
    "/api/admin": settings.ADMIN_BFF_URL,
    # Direct product-service routes
    "/api/v1/admin/products": settings.PRODUCT_SERVICE_URL,
    "/api/v1/admin/skus": settings.PRODUCT_SERVICE_URL,
    "/api/v1/admin/categories": settings.PRODUCT_SERVICE_URL,
    "/api/v1/admin/attributes": settings.PRODUCT_SERVICE_URL,
    "/api/v1/admin/groups": settings.PRODUCT_SERVICE_URL,
    "/api/v1/products": settings.PRODUCT_SERVICE_URL,
    "/api/v1/groups": settings.PRODUCT_SERVICE_URL,
    # "/api/users": settings.ADMIN_SERVICE_URL,
    # "/api/roles": settings.ADMIN_SERVICE_URL,
    # "/api/permissions": settings.ADMIN_SERVICE_URL,
    # "/api/v1/merchants": settings.MERCHANT_SERVICE_URL,
    # "/api/v1/inventory": settings.INVENTORY_SERVICE_URL,
    # "/api/v1/orders": settings.ORDER_SERVICE_URL,
    # "/api/v1/aftersale": settings.AFTERSALE_SERVICE_URL,
    # "/api/v1/promotions": settings.PROMOTION_SERVICE_URL,
    # "/api/v1/locations": settings.LOCATION_SERVICE_URL,
    # "/api/v1/notifications": settings.NOTIFICATION_SERVICE_URL,
}


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(request: Request, path: str):
    full_path = "/" + path
    method = request.method

    # Check if this is a public path (skip auth)
    if not public_routes_registry.is_public(method, full_path):
        await verify_request(request)

    # Find upstream service
    upstream_url = _resolve_upstream(full_path)
    if upstream_url is None:
        return JSONResponse(
            status_code=404,
            content=err(ROUTE_NOT_FOUND, "No upstream service found"),
        )

    target_url = upstream_url + full_path
    if request.url.query:
        target_url += "?" + request.url.query

    # Forward request, stripping hop-by-hop and host headers
    hop_by_hop = {
        "host", "connection", "keep-alive", "proxy-connection",
        "te", "trailer", "transfer-encoding", "upgrade",
    }
    headers = {k: v for k, v in request.headers.items() if k.lower() not in hop_by_hop}
    # Propagate request_id to upstream service
    headers["X-Request-ID"] = get_request_id()
    body = await request.body()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
            )
        except httpx.ConnectError:
            log.warning("proxy.upstream_unavailable", url=target_url)
            return JSONResponse(
                status_code=503,
                content=err(UPSTREAM_UNAVAILABLE, "Upstream service unavailable"),
            )
        except httpx.TimeoutException:
            log.warning("proxy.upstream_timeout", url=target_url)
            return JSONResponse(
                status_code=504,
                content=err(UPSTREAM_TIMEOUT, "Upstream service timeout"),
            )

    # Strip hop-by-hop headers before returning
    excluded = {
        "transfer-encoding", "connection", "keep-alive",
        "proxy-connection", "te", "trailer", "trailers", "upgrade",
    }
    response_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=response_headers,
        media_type=resp.headers.get("content-type"),
    )


def _resolve_upstream(path: str) -> str | None:
    """Find the upstream URL for a given path (longest prefix wins)."""
    for prefix in sorted(ROUTE_MAP.keys(), key=len, reverse=True):
        if path == prefix or path.startswith(prefix + "/"):
            return ROUTE_MAP[prefix]
    return None
