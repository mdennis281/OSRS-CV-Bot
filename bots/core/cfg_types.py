import random
from typing import List, Tuple

class BooleanParam:
    def __init__(self, value: bool):
        self.value = value

    @staticmethod
    def type() -> str:
        return "Boolean"
    
    @staticmethod
    def load(value: bool) -> 'BooleanParam':
        if not isinstance(value, bool):
            raise ValueError("Boolean value must be a boolean.")
        return BooleanParam(value)

    def val(self) -> bool:
        return self.value
    
    def __repr__(self):
        return f"BooleanValue({self.value})"
    
class StringParam:
    def __init__(self, value: str):
        self.value = value

    @staticmethod
    def type() -> str:
        return "String"
    
    @staticmethod
    def load(value: str) -> 'StringParam':
        if not isinstance(value, str):
            raise ValueError("String value must be a string.")
        return StringParam(value)

    def val(self) -> str:
        return self.value
    
    def __repr__(self):
        return f"StringValue({self.value})"
    
class StringListParam:
    def __init__(self, value: List[str]):
        self.value = value

    @staticmethod
    def type() -> str:
        return "StringList"
    
    @staticmethod
    def load(value: List[str]) -> 'StringListParam':
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ValueError("StringList value must be a list of strings.")
        return StringListParam(value)

    def val(self) -> List[str]:
        return self.value
    
    def __repr__(self):
        return f"StringListValue({self.value})"
    
class IntParam:
    def __init__(self, value: int):
        self.value = value

    @staticmethod
    def type() -> str:
        return "Int"
    
    @staticmethod
    def load(value: int) -> 'IntParam':
        if not isinstance(value, int):
            raise ValueError("Int value must be an integer.")
        return IntParam(value)

    def val(self) -> int:
        return self.value
    
    def __repr__(self):
        return f"IntValue({self.value})"
    
class FloatParam:
    def __init__(self, value: float):
        self.value = value

    @staticmethod
    def type() -> str:
        return "Float"
    
    @staticmethod
    def load(value: float) -> 'FloatParam':
        if not isinstance(value, float):
            raise ValueError("Float value must be a float.")
        return FloatParam(value)
    
    def __repr__(self):
        return f"FloatValue({self.value})"
    

class RGBParam:
    def __init__(self, r: int, g: int, b: int):
        self._r = r
        self._g = g
        self._b = b

    @staticmethod
    def type() -> str:
        return "RGB"

    @property
    def value(self) -> Tuple[int, int, int]:
        return (self._r, self._g, self._b)
    
    @staticmethod
    def load(value: List[int]) -> 'RGBParam':
        if len(value) != 3:
            raise ValueError("RGB value must be a list of three integers.")
        return RGBParam(value[0], value[1], value[2])

    def __repr__(self):
        return f"RGBValue({self._r}, {self._g}, {self._b})"
    
class RGBListParam:
    def __init__(self, value: List[RGBParam]):
        self.value = value

    @staticmethod
    def type() -> str:
        return "RGBList"
    
    @staticmethod
    def load(value: List[List[int]]) -> 'RGBListParam':
        if not isinstance(value, list) or not all(isinstance(v, list) and len(v) == 3 for v in value):
            raise ValueError("RGBList value must be a list of RGB lists.")
        return RGBListParam([RGBParam.load(v) for v in value])

    def __repr__(self):
        return f"RGBListValue({self.value})"
    
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
    
    def __repr__(self):
        return f"RangeValue({self.min_value}, {self.max_value})"


class BreakCfgParam:
    def __init__(self, break_duration: RangeParam, break_chance: FloatParam):
        self.break_duration = break_duration
        self.break_chance = break_chance
    
    @property
    def value(self):
        return self.break_duration.value, self.break_chance.value
    
    @staticmethod
    def type() -> str:
        return "BreakCfg"
    
    @staticmethod
    def load(value: List) -> 'BreakCfgParam':
        if len(value) != 2:
            raise ValueError("BreakCfg value must be a list of two elements: [break_duration, break_chance].")
        
        break_duration = RangeParam.load(value[0])
        break_chance = FloatParam.load(value[1])
        
        return BreakCfgParam(break_duration, break_chance)
    
    def should_break(self) -> bool:
        """Decides whether to take a break based on the configured chance."""
        return random.random() < self.break_chance.value
    
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
    
    def gen_tile(self, color:RGBParam) -> dict:
        # [{"regionId":12853,"regionX":58,"regionY":36,"z":0,"color":"#FF00FFFF"}]
        def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
            return "#{:02X}{:02X}{:02X}".format(*rgb)
        return {
            "regionId": self.chunk,
            "regionX": self.x,
            "regionY": self.y,
            "z": self.z,
            "color": _rgb_to_hex(color.value)
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

    def __repr__(self):
        return f"RouteValue({self.waypoints})"
    

TYPES = [BooleanParam, StringParam, IntParam, FloatParam, RGBParam, WaypointParam, RouteParam, StringListParam, RGBListParam]