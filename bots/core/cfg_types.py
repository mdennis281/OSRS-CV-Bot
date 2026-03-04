import random
import json
from typing import List, Tuple, Dict, Any, Union, Optional
class RGBParam:
    def __init__(self, r: int, g: int, b: int):
        # Validate RGB values are in valid range
        if not all(0 <= val <= 255 for val in [r, g, b]):
            raise ValueError("RGB values must be between 0 and 255")
        self._r = r
        self._g = g
        self._b = b

    @staticmethod
    def type() -> str:
        return "RGB"

    @property
    def value(self) -> Tuple[int, int, int]:
        """Get RGB values as a tuple"""
        return (self._r, self._g, self._b)
    
    @property
    def r(self) -> int:
        """Get red value"""
        return self._r
    
    @property
    def g(self) -> int:
        """Get green value"""
        return self._g
    
    @property
    def b(self) -> int:
        """Get blue value"""
        return self._b
    
    def to_hex(self) -> str:
        """Export RGB as hex string (e.g., '#FF0000')"""
        return "#{:02X}{:02X}{:02X}".format(self._r, self._g, self._b)
    
    def to_rgb_tuple(self) -> Tuple[int, int, int]:
        """Export RGB as tuple"""  
        return self.value
    
    @classmethod
    def from_rgb(cls, r: int, g: int, b: int) -> 'RGBParam':
        """Create RGBParam from RGB values"""
        return cls(r, g, b)
    
    @classmethod  
    def from_tuple(cls, rgb_tuple: Tuple[int, int, int]) -> 'RGBParam':
        """Create RGBParam from RGB tuple"""
        if len(rgb_tuple) != 3:
            raise ValueError("RGB tuple must contain exactly 3 values")
        return cls(*rgb_tuple)
    
    @classmethod
    def from_hex(cls, hex_color: str) -> 'RGBParam':
        """Create RGBParam from hex string (e.g., '#FF0000' or 'FF0000')"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            raise ValueError("Hex color must be 6 characters long")
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return cls(r, g, b)
        except ValueError as e:
            raise ValueError(f"Invalid hex color format: {hex_color}") from e
    
    @staticmethod
    def load(value) -> 'RGBParam':
        """Load RGBParam from various input formats"""
        if isinstance(value, list) and len(value) == 3:
            # List of integers [r, g, b]
            return RGBParam.from_tuple(tuple(value))
        elif isinstance(value, tuple) and len(value) == 3:
            # Tuple of integers (r, g, b)
            return RGBParam.from_tuple(value)
        elif isinstance(value, str):
            # Hex string '#FF0000' or 'FF0000'
            return RGBParam.from_hex(value)
        else:
            raise ValueError("RGB value must be a list/tuple of three integers or a hex string")

    def __repr__(self):
        return f"RGBParam({self._r}, {self._g}, {self._b})"
    
    def __eq__(self, other):
        if isinstance(other, RGBParam):
            return self.value == other.value
        elif isinstance(other, tuple) and len(other) == 3:
            return self.value == other
        return False
    
    def __iter__(self):
        """Allow unpacking like a tuple: r, g, b = rgb_param"""
        return iter(self.value)
    
    def __getitem__(self, index):
        """Allow indexing like a tuple: rgb_param[0] for red"""
        return self.value[index]
    
    def __len__(self):
        """Allow len() to work like a tuple"""
        return 3
    
    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": {
                "rgb": self.to_rgb_tuple(),
                "hex": self.to_hex()
            }
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'RGBParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        
        value = data["value"]
        # Try to load from hex first, then from rgb tuple
        if isinstance(value, dict):
            if "hex" in value:
                return cls.from_hex(value["hex"])
            elif "rgb" in value:
                return cls.from_tuple(tuple(value["rgb"]))
        
        # Fallback to the existing load method
        return cls.load(value)
    
class RangeParam:
    def __init__(self, min_value: float, max_value: float):
        self.min_value = min_value
        self.max_value = max_value

    @staticmethod
    def type() -> str:
        return "Range"
    
    @property
    def value(self) -> Tuple[float, float]:
        return (self.min_value, self.max_value)
    
    @staticmethod
    def load(value: List[float]) -> 'RangeParam':
        if len(value) != 2:
            raise ValueError("Range value must be a list of two floats.")
        return RangeParam(value[0], value[1])
    
    def choose(self) -> float:
        """Randomly choose a value within the range [min_value, max_value]."""
        return random.uniform(self.min_value, self.max_value)
    
    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": [self.min_value, self.max_value]
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'RangeParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        return cls.load(data["value"])
    
    def __repr__(self):
        return f"RangeValue({self.min_value}, {self.max_value})"


class BreakCfgParam:
    def __init__(self, break_duration: RangeParam, break_chance):
        """
        break_duration: RangeParam
        break_chance: float or FloatParam (legacy). Stored internally as float.
        """
        self.break_duration = break_duration
        # accept either raw float or FloatParam for backward compatibility
        if hasattr(break_chance, "value"):
            self.break_chance = float(getattr(break_chance, "value"))
        else:
            self.break_chance = float(break_chance)
    
    @property
    def value(self):
        return self.break_duration.value, self.break_chance
    
    @staticmethod
    def type() -> str:
        return "BreakCfg"
    
    @staticmethod
    def load(value: List) -> 'BreakCfgParam':
        if len(value) != 2:
            raise ValueError("BreakCfg value must be a list of two elements: [break_duration, break_chance].")
        
        break_duration = RangeParam.load(value[0])
        # accept raw float from config
        try:
            break_chance = float(value[1])
        except Exception as e:
            raise ValueError(f"BreakCfg break_chance must be a float: {e}") from e
        
        return BreakCfgParam(break_duration, break_chance)
    
    def should_break(self) -> bool:
        """Decides whether to take a break based on the configured chance."""
        return random.random() < float(self.break_chance)
    
    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": {
                "break_duration": self.break_duration.to_json(),
                "break_chance": self.break_chance
            }
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'BreakCfgParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        
        value = data["value"]
        if isinstance(value, dict):
            break_duration = RangeParam.from_json(value["break_duration"])
            break_chance = value["break_chance"]
            return cls(break_duration, break_chance)
        else:
            # Fallback to existing load method
            return cls.load(value)
    
    def __repr__(self):
        return f"BreakCfgValue({self.break_duration}, {self.break_chance})"
    
class WaypointParam:
    """
    Represents a waypoint with x, y, and optional z coordinates.
    Tolerance is the allowed deviation from the exact coordinates.
    """
    
    def __init__(self, x: int, y: int, z: int, chunk: int, tolerance: int = 5):
        self.x = x
        self.y = y
        self.z = z
        self.chunk = chunk
        self.tolerance = tolerance

    @staticmethod
    def type() -> str:
        return "Waypoint"

    @property
    def value(self):
        return [(self.x, self.y, self.z), self.chunk, self.tolerance]
    
    def gen_tile(self, color: RGBParam) -> dict:
        # [{"regionId":12853,"regionX":58,"regionY":36,"z":0,"color":"#FF00FFFF"}]
        return {
            "regionId": self.chunk,
            "regionX": self.x,
            "regionY": self.y,
            "z": self.z,
            "color": color.to_hex()
        }
    
    

    
    @staticmethod
    def load(value: list) -> 'WaypointParam':
        """
        Parses a waypoint value and returns a WaypointParam instance.
        Supported formats:
        - [[x, y, z], chunk, tolerance]
        - [x, y, z, chunk]
        - [[x, y, z], chunk]
        """
        # Default tolerance
        tolerance = 5
        
        # Handle format [[x, y, z], chunk, tolerance] or [[x, y, z], chunk]
        if isinstance(value[0], list):
            coords = value[0]
            if len(coords) != 3:
                raise ValueError("Waypoint coordinates must include x, y, and z values.")
            
            if len(value) < 2:
                raise ValueError("Waypoint must include chunk value.")
            
            chunk = value[1]
            if len(value) > 2:
                tolerance = value[2]
            
            return WaypointParam(coords[0], coords[1], coords[2], chunk, tolerance)
        
        # Handle format [x, y, z, chunk]
        elif len(value) == 4:
            x, y, z, chunk = value
            return WaypointParam(x, y, z, chunk, tolerance)
        
        else:
            raise ValueError("Invalid waypoint format. Must provide x, y, z, and chunk values.")

    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": {
                "x": self.x,
                "y": self.y,
                "z": self.z,
                "chunk": self.chunk,
                "tolerance": self.tolerance
            }
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'WaypointParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        
        value = data["value"]
        if isinstance(value, dict):
            return cls(
                value["x"], value["y"], value["z"],
                value["chunk"], value.get("tolerance", 5)
            )
        else:
            # Fallback to existing load method
            return cls.load(value)
    
    def __repr__(self):
        return f"WaypointValue({self.x}, {self.y}, {self.z})"
    
class RouteParam:
    def __init__(self, waypoints: List[WaypointParam]):
        self.waypoints = waypoints

    @staticmethod
    def type() -> str:
        return "Route"
    
    @property
    def value(self) -> List[List[int]]:
        return [wp.value for wp in self.waypoints]
    
    def reverse(self) -> 'RouteParam':
        """Returns a new RouteParam with waypoints in reverse order."""
        return RouteParam(self.waypoints[::-1])

    @staticmethod
    def load(value: List[List[int]]) -> 'RouteParam':
        waypoints = [WaypointParam.load(wp) for wp in value]
        return RouteParam(waypoints)

    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": [wp.to_json() for wp in self.waypoints]
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'RouteParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        
        waypoints = []
        for wp_data in data["value"]:
            if isinstance(wp_data, dict) and wp_data.get("type") == "Waypoint":
                waypoints.append(WaypointParam.from_json(wp_data))
            else:
                waypoints.append(WaypointParam.load(wp_data))
        
        return cls(waypoints)
    
    def __repr__(self):
        return f"RouteValue({self.waypoints})"


class ItemParam:
    """
    Represents an OSRS item parameter that can look up items from the item database.
    Supports lookup by item ID, item name, or direct Item object.
    """
    
    def __init__(self, item_identifier):
        from core.item_db import ItemLookup, Item
        
        self._item_lookup = ItemLookup()
        self._item: Optional[Item] = None
        self._original_identifier = item_identifier
        
        # Store the item based on the identifier type
        if isinstance(item_identifier, int):
            self._item = self._item_lookup.get_item_by_id(item_identifier)
            if not self._item:
                raise ValueError(f"Item with ID {item_identifier} not found in database")
        elif isinstance(item_identifier, str):
            self._item = self._item_lookup.get_item_by_name(item_identifier)
            if not self._item:
                raise ValueError(f"Item with name '{item_identifier}' not found in database")
        elif hasattr(item_identifier, 'id') and hasattr(item_identifier, 'name'):
            # Assume it's an Item object
            self._item = item_identifier
        else:
            raise ValueError(f"Invalid item identifier type: {type(item_identifier)}")

    @staticmethod
    def type() -> str:
        return "Item"

    @property
    def item(self):
        """Get the Item object"""
        return self._item
    
    @property
    def value(self) -> Dict[str, Any]:
        """Get item data as a dictionary"""
        if not self._item:
            return {}
        return {
            'id': self._item.id,
            'name': self._item.name,
            'stackable': self._item.stackable,
            'equipable': self._item.equipable,
            'tradeable_on_ge': self._item.tradeable_on_ge,
            'members': self._item.members,
            'cost': self._item.cost,
            'highalch': self._item.highalch,
            'lowalch': self._item.lowalch
        }
    
    @property
    def id(self) -> int:
        """Get item ID"""
        return self._item.id if self._item else 0
    
    @property
    def name(self) -> str:
        """Get item name"""
        return self._item.name if self._item else ""
    
    @property
    def stackable(self) -> bool:
        """Check if item is stackable"""
        return self._item.stackable if self._item else False
    
    @property
    def equipable(self) -> bool:
        """Check if item is equipable"""
        return self._item.equipable if self._item else False
    
    @classmethod
    def from_id(cls, item_id: int) -> 'ItemParam':
        """Create ItemParam from item ID"""
        return cls(item_id)
    
    @classmethod
    def from_name(cls, item_name: str) -> 'ItemParam':
        """Create ItemParam from item name"""
        return cls(item_name)
    
    @classmethod
    def from_item(cls, item) -> 'ItemParam':
        """Create ItemParam from Item object"""
        return cls(item)
    
    @staticmethod
    def load(value: Union[int, str, Dict[str, Any]]) -> 'ItemParam':
        """Load ItemParam from various input formats"""
        if isinstance(value, int):
            # Item ID
            return ItemParam.from_id(value)
        elif isinstance(value, str):
            # Item name
            return ItemParam.from_name(value)
        elif isinstance(value, dict):
            # Dictionary with id or name
            if 'id' in value:
                return ItemParam.from_id(value['id'])
            elif 'name' in value:
                return ItemParam.from_name(value['name'])
            else:
                raise ValueError("Item dictionary must contain 'id' or 'name' key")
        else:
            raise ValueError("Item value must be an int (ID), str (name), or dict with id/name")
    
    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": {
                "id": self.id,
                "name": self.name,
                "stackable": self.stackable,
                "equipable": self.equipable,
                "tradeable_on_ge": self._item.tradeable_on_ge if self._item else False,
                "members": self._item.members if self._item else False,
                "cost": self._item.cost if self._item else 0,
                "highalch": self._item.highalch if self._item else 0,
                "lowalch": self._item.lowalch if self._item else 0
            }
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'ItemParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        
        value = data["value"]
        if isinstance(value, dict):
            # Prefer ID over name for more reliable lookup
            if "id" in value:
                return cls.from_id(value["id"])
            elif "name" in value:
                return cls.from_name(value["name"])
            else:
                raise ValueError("Item JSON value must contain 'id' or 'name'")
        else:
            # Fallback to load method
            return cls.load(value)
    
    def search_similar(self, limit: int = 10):
        """Search for items with similar names"""
        if not self._item:
            return []
        
        # Get items that contain parts of this item's name
        words = self._item.name.lower().split()
        similar_items = []
        
        for word in words:
            if len(word) > 2:  # Skip very short words
                found_items = self._item_lookup.search_items(word)
                for item in found_items.values():
                    if item.id != self._item.id and item not in similar_items:
                        similar_items.append(item)
                        if len(similar_items) >= limit:
                            break
            if len(similar_items) >= limit:
                break
        
        return similar_items[:limit]
    
    def __repr__(self):
        return f"ItemParam(id={self.id}, name='{self.name}')"
    
    def __str__(self):
        return self.name
    
    def __eq__(self, other):
        if isinstance(other, ItemParam):
            return self.id == other.id
        elif isinstance(other, int):
            return self.id == other
        elif isinstance(other, str):
            return self.name.lower() == other.lower()
        return False
    




class BooleanParam:
    """Boolean parameter type"""
    
    def __init__(self, value: bool = False):
        self._value = bool(value)
    
    @staticmethod
    def type() -> str:
        return "Boolean"
    
    @property
    def value(self) -> bool:
        return self._value
    
    @value.setter
    def value(self, val: bool):
        self._value = bool(val)
    
    @staticmethod
    def load(value: Union[bool, str, int]) -> 'BooleanParam':
        """Load BooleanParam from various input formats"""
        if isinstance(value, bool):
            return BooleanParam(value)
        elif isinstance(value, str):
            return BooleanParam(value.lower() in ('true', '1', 'yes', 'on'))
        elif isinstance(value, int):
            return BooleanParam(bool(value))
        else:
            raise ValueError("Boolean value must be a bool, str, or int")
    
    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": self._value
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'BooleanParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        return cls(data["value"])
    
    def __repr__(self):
        return f"BooleanParam({self._value})"
    
    def __bool__(self):
        return self._value


class StringParam:
    """String parameter type"""
    
    def __init__(self, value: str = ""):
        self._value = str(value)
    
    @staticmethod
    def type() -> str:
        return "String"
    
    @property
    def value(self) -> str:
        return self._value
    
    @value.setter
    def value(self, val: str):
        self._value = str(val)
    
    @staticmethod
    def load(value: str) -> 'StringParam':
        """Load StringParam from string"""
        return StringParam(str(value))
    
    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": self._value
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'StringParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        return cls(data["value"])
    
    def __repr__(self):
        return f"StringParam('{self._value}')"
    
    def __str__(self):
        return self._value


class IntParam:
    """Integer parameter type"""
    
    def __init__(self, value: int = 0):
        self._value = int(value)
    
    @staticmethod
    def type() -> str:
        return "Int"
    
    @property
    def value(self) -> int:
        return self._value
    
    @value.setter
    def value(self, val: int):
        self._value = int(val)
    
    @staticmethod
    def load(value: Union[int, str]) -> 'IntParam':
        """Load IntParam from int or string"""
        return IntParam(int(value))
    
    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": self._value
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'IntParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        return cls(data["value"])
    
    def __repr__(self):
        return f"IntParam({self._value})"
    
    def __int__(self):
        return self._value


class FloatParam:
    """Float parameter type"""
    
    def __init__(self, value: float = 0.0):
        self._value = float(value)
    
    @staticmethod
    def type() -> str:
        return "Float"
    
    @property
    def value(self) -> float:
        return self._value
    
    @value.setter
    def value(self, val: float):
        self._value = float(val)
    
    @staticmethod
    def load(value: Union[float, int, str]) -> 'FloatParam':
        """Load FloatParam from float, int, or string"""
        return FloatParam(float(value))
    
    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": self._value
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'FloatParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        return cls(data["value"])
    
    def __repr__(self):
        return f"FloatParam({self._value})"
    
    def __float__(self):
        return self._value


class StringListParam:
    """String list parameter type"""
    
    def __init__(self, value: List[str] = None):
        self._value = list(value) if value else []
    
    @staticmethod
    def type() -> str:
        return "StringList"
    
    @property
    def value(self) -> List[str]:
        return self._value.copy()
    
    @value.setter
    def value(self, val: List[str]):
        self._value = list(val)
    
    @staticmethod
    def load(value: List[str]) -> 'StringListParam':
        """Load StringListParam from list of strings"""
        return StringListParam(value)
    
    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": self._value
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'StringListParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        return cls(data["value"])
    
    def __repr__(self):
        return f"StringListParam({self._value})"
    
    def __len__(self):
        return len(self._value)
    
    def __getitem__(self, index):
        return self._value[index]
    
    def __iter__(self):
        return iter(self._value)


class RGBListParam:
    """List of RGB parameters"""
    
    def __init__(self, value: List[RGBParam] = None):
        self._value = list(value) if value else []
    
    @staticmethod
    def type() -> str:
        return "RGBList"
    
    @property
    def value(self) -> List[RGBParam]:
        return self._value.copy()
    
    @value.setter
    def value(self, val: List[RGBParam]):
        self._value = list(val)
    
    @staticmethod
    def load(value: List[List[int]]) -> 'RGBListParam':
        """Load RGBListParam from list of RGB tuples"""
        rgb_params = [RGBParam.from_tuple(tuple(rgb)) for rgb in value]
        return RGBListParam(rgb_params)
    
    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": [rgb.to_json() for rgb in self._value]
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'RGBListParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        
        rgb_params = []
        for rgb_data in data["value"]:
            if isinstance(rgb_data, dict) and rgb_data.get("type") == "RGB":
                rgb_params.append(RGBParam.from_json(rgb_data))
            else:
                # Fallback for simple list format
                rgb_params.append(RGBParam.from_tuple(tuple(rgb_data)))
        
        return cls(rgb_params)
    
    def __repr__(self):
        return f"RGBListParam({self._value})"
    
    def __len__(self):
        return len(self._value)
    
    def __getitem__(self, index):
        return self._value[index]
    
    def __iter__(self):
        return iter(self._value)


class ItemListParam:
    """List of Item parameters"""
    
    def __init__(self, value: List[ItemParam] = None):
        self._value = list(value) if value else []
    
    @staticmethod
    def type() -> str:
        return "ItemList"
    
    @property
    def value(self) -> List[ItemParam]:
        return self._value.copy()
    
    @value.setter
    def value(self, val: List[ItemParam]):
        self._value = list(val)
    
    @staticmethod
    def load(value: List[Any]) -> 'ItemListParam':
        """Load ItemListParam from list of item identifiers (ids, names, or dicts)"""
        item_params = [ItemParam.load(item) for item in value]
        return ItemListParam(item_params)
    
    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return {
            "type": self.type(),
            "value": [item.to_json() for item in self._value]
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'ItemListParam':
        """Import from JSON data"""
        if data.get("type") != cls.type():
            raise ValueError(f"Expected type '{cls.type()}', got '{data.get('type')}'")
        
        item_params = []
        for item_data in data["value"]:
            if isinstance(item_data, dict) and item_data.get("type") == "Item":
                item_params.append(ItemParam.from_json(item_data))
            else:
                item_params.append(ItemParam.load(item_data))
        
        return cls(item_params)
    
    def append(self, item: ItemParam):
        """Add an item to the list"""
        self._value.append(item)
    
    def remove(self, index: int):
        """Remove an item by index"""
        del self._value[index]
    
    def __repr__(self):
        return f"ItemListParam({self._value})"
    
    def __len__(self):
        return len(self._value)
    
    def __getitem__(self, index):
        return self._value[index]
    
    def __iter__(self):
        return iter(self._value)


TYPES = (RGBParam, WaypointParam, RouteParam, RangeParam, BreakCfgParam, ItemParam, ItemListParam, BooleanParam, StringParam, IntParam, FloatParam, StringListParam, RGBListParam)