"""Consumer profile and points endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import CONSUMER_NOT_FOUND, err, ok
from app.schemas.consumer import ConsumerCreate, ConsumerResponse, ConsumerUpdate
from app.services import consumer_service

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_consumer(
    body: ConsumerCreate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    consumer = await consumer_service.create_consumer(db, body)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(ConsumerResponse.model_validate(consumer).model_dump(mode="json")),
    )


@router.get("/{consumer_id}")
async def get_consumer(
    consumer_id: UUID, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    consumer = await consumer_service.get_consumer(db, consumer_id)
    if consumer is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(CONSUMER_NOT_FOUND, "Consumer not found"),
        )
    return JSONResponse(
        content=ok(ConsumerResponse.model_validate(consumer).model_dump(mode="json"))
    )


@router.put("/{consumer_id}")
async def update_consumer(
    consumer_id: UUID, body: ConsumerUpdate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    consumer = await consumer_service.update_consumer(db, consumer_id, body)
    if consumer is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(CONSUMER_NOT_FOUND, "Consumer not found"),
        )
    return JSONResponse(
        content=ok(ConsumerResponse.model_validate(consumer).model_dump(mode="json"))
    )


@router.get("/{consumer_id}/points")
async def get_points(
    consumer_id: UUID, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    consumer = await consumer_service.get_consumer(db, consumer_id)
    if consumer is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(CONSUMER_NOT_FOUND, "Consumer not found"),
        )
    return JSONResponse(content=ok({"points": consumer.points}))
