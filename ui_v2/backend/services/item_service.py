"""Wraps core.item_db.ItemLookup for the API layer."""

from typing import Any, Dict, List, Optional

from core.item_db import ItemLookup, Item


def _item_to_dict(item: Item, include_placeholder: bool = False) -> Dict[str, Any]:
    """Serialize an Item dataclass to a JSON-compatible dict."""
    d: Dict[str, Any] = {
        "id": item.id,
        "name": item.name,
        "tradeable_on_ge": item.tradeable_on_ge,
        "members": item.members,
        "noted": item.noted,
        "noteable": item.noteable,
        "stackable": item.stackable,
        "equipable": item.equipable,
        "cost": item.cost,
        "lowalch": item.lowalch,
        "highalch": item.highalch,
        "icon_b64": item.icon_b64,
    }
    if include_placeholder:
        d["placeholder"] = item.placeholder
    return d


def search_items(
    query: str,
    limit: int = 50,
    filters: Optional[Dict[str, bool]] = None,
) -> List[Dict[str, Any]]:
    """Search items, returning serialized dicts."""
    lookup = ItemLookup()

    if filters:
        items = lookup.search_items_advanced(query, filters, limit)
        return [_item_to_dict(item) for item in items]

    items_dict = lookup.search_items(query, limit)
    return [_item_to_dict(item) for item in items_dict.values()]


def get_item_detail(item_id: int) -> Optional[Dict[str, Any]]:
    """Return full item detail or None."""
    item = ItemLookup().get_item_by_id(item_id)
    if not item:
        return None
    return _item_to_dict(item, include_placeholder=True)
