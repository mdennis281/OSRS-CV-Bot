"""Pydantic models for item search and detail responses."""

from typing import Optional, List
from pydantic import BaseModel


class ItemModel(BaseModel):
    id: int
    name: str
    tradeable_on_ge: bool
    members: bool
    noted: bool
    noteable: bool
    placeholder: Optional[bool] = None
    stackable: bool
    equipable: bool
    cost: int
    lowalch: int
    highalch: int
    icon_b64: Optional[str] = None


class ItemSearchResponse(BaseModel):
    success: bool
    results: List[ItemModel] = []
    count: int = 0


class ItemDetailResponse(BaseModel):
    success: bool
    item: Optional[ItemModel] = None
    error: Optional[str] = None
