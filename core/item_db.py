import json
from dataclasses import dataclass
from typing import Dict, Optional, Any, List
from core.logger import get_logger
from PIL import Image
from io import BytesIO
import base64
from core import tools
from core import ocr
from core.logger import get_logger

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
    log = get_logger('Item')

    @property
    def icon(self) -> Image.Image:
        """
        Returns the icon image of the item.
        """
        if self.icon_b64:
            return Image.open(BytesIO(base64.b64decode(self.icon_b64)))
        return None
    
    def get_count(self, item_match: tools.MatchResult, sc: Image.Image) -> int:
        """
        Extracts and returns the item count from the provided screenshot and match area.
        """
        center = item_match.get_center()

        match = tools.MatchResult(
            start_x=center[0]-14,
            start_y=center[1]-30,
            end_x=center[0]+25,
            end_y=center[1]-5
        )
        #match.debug_draw(sc).show()
        
        scc = match.crop_in(sc)
        num_img = tools.mask_colors(scc, [
            (255, 255, 0), # < 100k
            # TODO: actually handle these
            # (255,255,255), # > 100k
            # (0, 255, 128)  # > 10M
        ], tolerance=5)

        try:
            return ocr.get_number(
                num_img,
                ocr.FontChoice.RUNESCAPE_PLAIN_11,
            )
        except Exception as e:
            self.log.error(f'Failed to get count for item: {self.name} - {str(e)}')
            match.debug_draw(sc).show()
            return 0

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
            self.log = get_logger('ItemLookup')
            self.log.info("Initializing ItemLookup...")
            self._items_by_id: Dict[int, Item] = {}
            self._items_by_name: Dict[str, Item] = {}
            self._load_data()
            self.log.info(f"Loaded {len(self._items_by_id)} items into cache.")

    def _load_data(self):
        """
        Loads data from JSON files, filters out duplicates, populates the item cache,
        and synthesizes noted variants from canonicals (upstream cache only ships
        canonical entries; noted lookups need an entry per linked_id_noted).
        """
        try:
            with open("data/items/items-cache-data.json", "r") as f:
                items_data = json.load(f)

            with open("data/items/icons-items-complete.json", "r") as f:
                icons_data = json.load(f)

            # Import here to avoid circulars at module import time
            from core.tools import base64_to_image, crop_transparent_border, image_to_base64

            def _crop_icon(b64: Optional[str], item_id: int, item_name: str) -> Optional[str]:
                if not b64:
                    return None
                try:
                    img = base64_to_image(b64)
                    cropped = crop_transparent_border(img)
                    return image_to_base64(cropped, fmt="PNG")
                except Exception as e:
                    self.log.debug(f"Icon crop failed for item {item_id} - {item_name}: {e}")
                    return b64

            # Pass 1: load canonicals
            for item in items_data.values():
                # Filter out duplicates: only include items with linked_id_item=None and linked_id_placeholder!=None
                if (item["linked_id_item"] is None and item["linked_id_placeholder"] is not None) or item["id"] not in self._items_by_id.keys():
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
                        icon_b64=_crop_icon(icons_data.get(str(item["id"])), item["id"], item["name"]),
                    )

                    # Populate lookup dictionaries
                    self._items_by_id[item_obj.id] = item_obj
                    self._items_by_name[item_obj.name.lower()] = item_obj

            # Pass 2: synthesize noted variants from canonicals.
            # Upstream cache (DayV-git/osrsreboxed-db) ships only canonicals; noted variants
            # were previously hand-baked into the cache file. Deriving them here keeps the
            # cache file in sync with upstream without manual augmentation.
            # Noted ids are looked up by id only (name lookups still resolve to canonical).
            for raw in list(items_data.values()):
                noted_id = raw.get("linked_id_noted")
                if noted_id is None or noted_id in self._items_by_id:
                    continue
                self._items_by_id[noted_id] = Item(
                    id=noted_id,
                    name=raw["name"],
                    tradeable_on_ge=raw["tradeable_on_ge"],
                    members=raw["members"],
                    noted=True,
                    noteable=True,
                    placeholder=False,
                    stackable=raw["stackable"],
                    equipable=raw["equipable"],
                    cost=raw["cost"],
                    lowalch=raw["lowalch"],
                    highalch=raw["highalch"],
                    icon_b64=_crop_icon(icons_data.get(str(noted_id)), noted_id, raw["name"]),
                )

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
    
    def get_item(self, item: Any) -> Optional[Item]:
        """
        Retrieves an item by its ID or name.
        
        If the input is an integer, it is treated as an item ID.
        If the input is a string, it is treated as an item name (case-insensitive).
        """
        if isinstance(item, int):
            return self.get_item_by_id(item)
        elif isinstance(item, str):
            return self.get_item_by_name(item)
        return None

    def search_items(self, query: str, limit: int = 50) -> Dict[int, Item]:
        """
        Searches for items whose names contain the query string (case-insensitive).
        
        Returns a dictionary of item IDs and their corresponding items, limited by the limit parameter.
        """
        if not query or not query.strip():
            return {}
            
        query = query.lower().strip()
        results = {}
        count = 0
        
        # First pass: exact matches get priority
        for item_id, item in self._items_by_id.items():
            if item.name.lower() == query:
                results[item_id] = item
                count += 1
                if count >= limit:
                    break
        
        # Second pass: starts with query
        if count < limit:
            for item_id, item in self._items_by_id.items():
                if item_id not in results and item.name.lower().startswith(query):
                    results[item_id] = item
                    count += 1
                    if count >= limit:
                        break
        
        # Third pass: contains query
        if count < limit:
            for item_id, item in self._items_by_id.items():
                if item_id not in results and query in item.name.lower():
                    results[item_id] = item
                    count += 1
                    if count >= limit:
                        break
        
        return results
    
    def search_items_advanced(self, query: str, filters: Dict[str, Any] = None, limit: int = 50) -> List[Item]:
        """
        Advanced search with filters and sorting.
        
        Args:
            query: Search term for item name
            filters: Dictionary of filters (tradeable_on_ge, members, stackable, etc.)
            limit: Maximum number of results to return
            
        Returns:
            List of Item objects sorted by relevance
        """
        if not query or not query.strip():
            return []
            
        # Get basic search results
        search_results = self.search_items(query, limit * 2)  # Get more for filtering
        results = list(search_results.values())
        
        # Apply filters if provided
        if filters:
            filtered_results = []
            for item in results:
                include = True
                for filter_key, filter_value in filters.items():
                    if hasattr(item, filter_key):
                        if getattr(item, filter_key) != filter_value:
                            include = False
                            break
                if include:
                    filtered_results.append(item)
            results = filtered_results
        
        # Sort by relevance (exact match first, then starts with, then contains)
        query_lower = query.lower()
        
        def relevance_score(item):
            name_lower = item.name.lower()
            if name_lower == query_lower:
                return 0  # Exact match - highest priority
            elif name_lower.startswith(query_lower):
                return 1  # Starts with - second priority
            else:
                return 2  # Contains - lowest priority
        
        results.sort(key=relevance_score)
        
        return results[:limit]

    def list_all_items(self) -> Dict[int, str]:
        """
        Returns a dictionary of all items with their IDs and names.
        """
        return {item.id: item.name for item in self._items_by_id.values()}


