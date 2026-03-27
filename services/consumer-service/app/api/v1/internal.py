"""Internal endpoints for use by other microservices (order-service, etc.)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import CONSUMER_NOT_FOUND, INSUFFICIENT_POINTS, err, ok
from app.schemas.consumer import ConsumerCreate, PointsAdjustRequest
from app.services import consumer_service

router = APIRouter()


@router.get("/consumers/by-phone/{phone}")
async def get_consumer_by_phone_internal(
    phone: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    consumer = await consumer_service.get_consumer_by_phone(db, phone)
    if consumer is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(CONSUMER_NOT_FOUND, "Consumer not found"),
        )
    return JSONResponse(
        content=ok({
            "id": consumer.id,
            "public_id": str(consumer.public_id),
            "nickname": consumer.nickname,
            "phone": consumer.phone,
            "level": consumer.level,
            "status": consumer.status,
        })
    )


@router.post("/consumers", status_code=status.HTTP_201_CREATED)
async def create_consumer_internal(
    body: ConsumerCreate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    consumer = await consumer_service.create_consumer(db, body)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok({
            "id": consumer.id,
            "public_id": str(consumer.public_id),
            "phone": consumer.phone,
        }),
    )


@router.get("/consumers/{consumer_id}")
async def get_consumer_internal(
    consumer_id: UUID, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    consumer = await consumer_service.get_consumer(db, consumer_id)
    if consumer is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(CONSUMER_NOT_FOUND, "Consumer not found"),
        )
    return JSONResponse(
        content=ok({
            "id": consumer.id,
            "public_id": str(consumer.public_id),
            "nickname": consumer.nickname,
            "phone": consumer.phone,
            "level": consumer.level,
            "status": consumer.status,
        })
    )


@router.post("/consumers/{consumer_id}/points")
async def adjust_points(
    consumer_id: UUID, body: PointsAdjustRequest, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    consumer = await consumer_service.get_consumer(db, consumer_id)
    if consumer is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(CONSUMER_NOT_FOUND, "Consumer not found"),
        )

    if body.delta < 0 and consumer.points + body.delta < 0:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=err(INSUFFICIENT_POINTS, "Insufficient points balance"),
        )

    consumer = await consumer_service.adjust_points(db, consumer_id, body.delta)
    return JSONResponse(content=ok({"points": consumer.points}))
