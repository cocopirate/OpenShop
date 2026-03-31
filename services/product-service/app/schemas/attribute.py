"""Pydantic schemas for Attribute."""
from __future__ import annotations

from pydantic import BaseModel

from app.models.attribute import AttributeType


class AttributeCreate(BaseModel):
    name: str
    type: AttributeType = AttributeType.SPEC


class AttributeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    type: AttributeType


class CategoryAttributeCreate(BaseModel):
    attribute_id: int


class CategoryAttributeResponse(BaseModel):
    model_config = {"from_attributes": True}

    category_id: int
    attribute_id: int
