import json
from dataclasses import dataclass
from typing import Dict, Optional, Any

@dataclass
class Item:
    """
    Represents an in-game item with its attributes.
    """
    id: int
    name: str
    tradeable_on_ge: bool
    members: bool
    noted: bool
    noteable: bool
    placeholder: bool
    stackable: bool
    equipable: bool
    cost: int
    lowalch: int
    highalch: int
    icon_b64: Optional[str] = None

class ItemLookup:
    """
    Singleton class for looking up items in the OSRS database.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ItemLookup, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_items_by_id"):
            self._items_by_id: Dict[int, Item] = {}
            self._items_by_name: Dict[str, Item] = {}
            self._load_data()

    def _load_data(self):
        """
        Loads data from JSON files, filters out duplicates, and populates the item cache.
        """
        try:
            with open("osrsbox-db-master/data/items/items-cache-data.json", "r") as f:
                items_data = json.load(f)

            with open("osrsbox-db-master/data/icons/icons-items-complete.json", "r") as f:
                icons_data = json.load(f)


            for item in items_data.values():
                # Filter out duplicates: only include items with linked_id_item=None and linked_id_placeholder!=None
                if (item["linked_id_item"] is None and item["linked_id_placeholder"] is not None) or item["id"] not in self._items_by_id.keys():
                    icon_b64 = icons_data.get(str(item["id"]))
                    
                    # Create an Item dataclass
                    item_obj = Item(
                        id=item["id"],
                        name=item["name"],
                        tradeable_on_ge=item["tradeable_on_ge"],
                        members=item["members"],
                        noted=item["noted"],
                        noteable=item["noteable"],
                        placeholder=item["placeholder"],
                        stackable=item["stackable"],
                        equipable=item["equipable"],
                        cost=item["cost"],
                        lowalch=item["lowalch"],
                        highalch=item["highalch"],
                        icon_b64=icon_b64
                    )

                    # Populate lookup dictionaries
                    self._items_by_id[item_obj.id] = item_obj
                    self._items_by_name[item_obj.name.lower()] = item_obj

        except Exception as e:
            raise RuntimeError(f"Failed to load item data: {e}")

    def get_item_by_id(self, item_id: int) -> Optional[Item]:
        """
        Retrieves an item by its ID.
        """
        return self._items_by_id.get(item_id)

    def get_item_by_name(self, name: str) -> Optional[Item]:
        """
        Retrieves an item by its name (case-insensitive).
        """
        return self._items_by_name.get(name.lower())

    def search_items(self, query: str) -> Dict[int, Item]:
        """
        Searches for items whose names contain the query string (case-insensitive).
        
        Returns a dictionary of item IDs and their corresponding items.
        """
        query = query.lower()
        return {
            item_id: item
            for item_id, item in self._items_by_id.items()
            if query in item.name.lower()
        }

    def list_all_items(self) -> Dict[int, str]:
        """
        Returns a dictionary of all items with their IDs and names.
        """
        return {item.id: item.name for item in self._items_by_id.values()}


