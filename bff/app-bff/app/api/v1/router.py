"""App BFF routes – aggregates product-service data for mobile/mini-program clients."""
from __future__ import annotations

from typing import Optional

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.response import err, ok

router = APIRouter()

_PRODUCT_BASE = settings.PRODUCT_SERVICE_URL + "/api/v1"


async def _forward(method: str, url: str, request: Request, **kwargs) -> JSONResponse:
    """Forward a request to an upstream service and relay the response."""
    headers = {
        "X-Request-ID": request.headers.get("X-Request-ID", ""),
        "Authorization": request.headers.get("Authorization", ""),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.request(method, url, headers=headers, **kwargs)
        except httpx.ConnectError:
            return JSONResponse(status_code=503, content=err(50301, "Upstream unavailable"))
        except httpx.TimeoutException:
            return JSONResponse(status_code=504, content=err(50401, "Upstream timeout"))
    return JSONResponse(status_code=resp.status_code, content=resp.json())


# --------------------------------------------------------------------------- #
# Product endpoints (read-only, public)                                        #
# --------------------------------------------------------------------------- #


@router.get("/products", tags=["public"], summary="商品列表")
async def list_products(
    request: Request,
    category_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    params: dict = {"page": page, "size": size}
    if category_id is not None:
        params["category_id"] = category_id
    return await _forward("GET", f"{_PRODUCT_BASE}/products", request, params=params)


@router.get("/products/{spu_id}", tags=["public"], summary="商品详情")
async def get_product(spu_id: int, request: Request) -> JSONResponse:
    return await _forward("GET", f"{_PRODUCT_BASE}/products/{spu_id}", request)


@router.get("/groups/{group_id}/products", tags=["public"], summary="分组商品列表")
async def get_group_products(group_id: int, request: Request) -> JSONResponse:
    return await _forward("GET", f"{_PRODUCT_BASE}/groups/{group_id}/products", request)


# --------------------------------------------------------------------------- #
# Category endpoint (public)                                                   #
# --------------------------------------------------------------------------- #


@router.get("/categories/tree", tags=["public"], summary="分类树")
async def get_category_tree(request: Request) -> JSONResponse:
    return await _forward("GET", f"{_PRODUCT_BASE}/admin/categories/tree", request)
