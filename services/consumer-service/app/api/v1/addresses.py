"""Consumer address CRUD endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ADDRESS_NOT_FOUND, CONSUMER_NOT_FOUND, err, ok
from app.schemas.consumer import AddressCreate, AddressResponse, AddressUpdate
from app.services import address_service, consumer_service

router = APIRouter()


async def _resolve_consumer_id(consumer_id: UUID, db: AsyncSession) -> int | None:
    """Resolve public UUID to internal integer ID, returning None if not found."""
    consumer = await consumer_service.get_consumer(db, consumer_id)
    return consumer.id if consumer else None


@router.get("/{consumer_id}/addresses")
async def list_addresses(
    consumer_id: UUID, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    internal_id = await _resolve_consumer_id(consumer_id, db)
    if internal_id is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(CONSUMER_NOT_FOUND, "Consumer not found"),
        )
    addresses = await address_service.list_addresses(db, internal_id)
    return JSONResponse(
        content=ok([AddressResponse.model_validate(a).model_dump(mode="json") for a in addresses])
    )


@router.post("/{consumer_id}/addresses", status_code=status.HTTP_201_CREATED)
async def create_address(
    consumer_id: UUID, body: AddressCreate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    internal_id = await _resolve_consumer_id(consumer_id, db)
    if internal_id is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(CONSUMER_NOT_FOUND, "Consumer not found"),
        )
    address = await address_service.create_address(db, internal_id, body)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(AddressResponse.model_validate(address).model_dump(mode="json")),
    )


@router.put("/{consumer_id}/addresses/{addr_id}")
async def update_address(
    consumer_id: UUID, addr_id: int, body: AddressUpdate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    internal_id = await _resolve_consumer_id(consumer_id, db)
    if internal_id is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(CONSUMER_NOT_FOUND, "Consumer not found"),
        )
    address = await address_service.update_address(db, internal_id, addr_id, body)
    if address is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(ADDRESS_NOT_FOUND, "Address not found"),
        )
    return JSONResponse(
        content=ok(AddressResponse.model_validate(address).model_dump(mode="json"))
    )


@router.delete("/{consumer_id}/addresses/{addr_id}")
async def delete_address(
    consumer_id: UUID, addr_id: int, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    internal_id = await _resolve_consumer_id(consumer_id, db)
    if internal_id is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(CONSUMER_NOT_FOUND, "Consumer not found"),
        )
    deleted = await address_service.delete_address(db, internal_id, addr_id)
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(ADDRESS_NOT_FOUND, "Address not found"),
        )
    return JSONResponse(content=ok({"message": "deleted"}))


@router.post("/{consumer_id}/addresses/{addr_id}/set-default")
async def set_default_address(
    consumer_id: UUID, addr_id: int, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    internal_id = await _resolve_consumer_id(consumer_id, db)
    if internal_id is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(CONSUMER_NOT_FOUND, "Consumer not found"),
        )
    address = await address_service.set_default_address(db, internal_id, addr_id)
    if address is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(ADDRESS_NOT_FOUND, "Address not found"),
        )
    return JSONResponse(
        content=ok(AddressResponse.model_validate(address).model_dump(mode="json"))
    )
