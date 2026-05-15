"""Item database API router – /api/items/*."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Query

from ui_v2.backend.services import item_service

router = APIRouter(prefix="/api/items", tags=["items"])


@router.get("/search")
def search_items(
    q: str = Query("", description="Search query"),
    limit: int = Query(50, ge=1, le=200),
    tradeable: Optional[str] = Query(None),
    members: Optional[str] = Query(None),
    stackable: Optional[str] = Query(None),
    equipable: Optional[str] = Query(None),
) -> Dict[str, Any]:
    filters: Dict[str, bool] = {}
    if tradeable == "true":
        filters["tradeable_on_ge"] = True
    if members == "true":
        filters["members"] = True
    if stackable == "true":
        filters["stackable"] = True
    if equipable == "true":
        filters["equipable"] = True

    results = item_service.search_items(q, limit, filters or None)
    return {"success": True, "results": results, "count": len(results)}


@router.get("/{item_id}")
def item_detail(item_id: int) -> Dict[str, Any]:
    item = item_service.get_item_detail(item_id)
    if not item:
        return {"success": False, "error": f"Item with ID {item_id} not found"}
    return {"success": True, "item": item}
