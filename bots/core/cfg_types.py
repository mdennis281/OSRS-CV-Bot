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
        return random.random() < self.break_chance.val()
    
    def __repr__(self):
        return f"BreakCfgValue({self.break_duration}, {self.break_chance})"
    
class WaypointParam:
    """
    Represents a waypoint with x, y, and optional z coordinates.
    Tolerance is the allowed deviation from the exact coordinates.
    """
    def __init__(self, x: int, y: int, z: int = 0, tolerance: int = 5):
        self.x = x
        self.y = y
        self.z = z
        self.tolerance = tolerance

    @staticmethod
    def type() -> str:
        return "Waypoint"

    @property
    def value(self):
        return [(self.x, self.y, self.z), self.tolerance]
    
    @staticmethod
    def load(value: list) -> 'WaypointParam':
        """
        Parses a waypoint value and returns a WaypointParam instance.
        Supported formats:
        - [[x, y, z], tolerance]
        - [x, y]
        - [x, y, z]
        - [[x, y], tolerance]
        """
        # Default tolerance
        tolerance = 5

        # Handle format [[x, y, z], tolerance] or [[x, y], tolerance]
        if isinstance(value[0], list):
            if len(value) == 2:
                tolerance = value[1]
            value = value[0]

        # Validate the length of the value list
        if len(value) not in (2, 3):
            raise ValueError("Waypoint value must be a list of two or three integers.")

        # Extract coordinates and set default z if not provided
        x, y = value[0], value[1]
        z = value[2] if len(value) == 3 else 0

        return WaypointParam(x, y, z, tolerance)

    def __repr__(self):
        return f"WaypointValue({self._x}, {self._y}, {self._z})"
    
class RouteParam:
    def __init__(self, waypoints: List[WaypointParam]):
        self.waypoints = waypoints

    @staticmethod
    def type() -> str:
        return "Route"
    
    @property
    def value(self) -> List[List[int]]:
        return [wp.value for wp in self.waypoints]

    @staticmethod
    def load(value: List[List[int]]) -> 'RouteParam':
        waypoints = [WaypointParam.load(wp) for wp in value]
        return RouteParam(waypoints)

    def __repr__(self):
        return f"RouteValue({self.waypoints})"
    

TYPES = [BooleanParam, StringParam, IntParam, FloatParam, RGBParam, WaypointParam, RouteParam]