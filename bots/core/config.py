from .cfg_types import RGBParam, RangeParam, BreakCfgParam, WaypointParam, RouteParam, ItemParam, ItemListParam
from .cfg_types import TYPES as CFG_TYPES
import json
from typing import Any, Dict, Union

# Define a type map for JSON import/export
TYPE_MAP = {
    "RGB": RGBParam,
    "Range": RangeParam,
    "BreakCfg": BreakCfgParam,
    "Waypoint": WaypointParam,
    "Route": RouteParam,
    "Item": ItemParam,
    "ItemList": ItemListParam,
}

example_config = {
    "bank_tile": {'type': "RGB", 'value': {"rgb": [255, 0, 100], "hex": "#FF0064"}},
    "furnace_tile": {'type': "RGB", 'value': {"rgb": [0, 255, 100], "hex": "#00FF64"}},
    "ore_name": "Iron ore",  # Basic string
    "bar_name": "Steel bar",  # Basic string
    "coal_per_bar": 2,  # Basic int
    "mine_delay": {'type': "Range", 'value': [0.2, 0.5]},
}


class BotConfigMixin:
    """
    Mixin class for bot configuration.
    This class can be used to add configuration properties to a bot.
    """
    
    def import_config(self, config: Dict[str, Any]):
        """
        Load configuration from a dictionary.
        
        Args:
            config: Dictionary containing configuration data. Can have:
                    - Simple values for basic types (int, str, float, list)
                    - Complex objects with 'type' and 'value' keys for custom parameter types
        """
        for key, value in config.items():
            if not hasattr(self, key):
                raise KeyError(f"Config key '{key}' not found in bot configuration.")
            
            current_value = getattr(self, key)
            
            # Handle complex parameter objects with type information
            if isinstance(value, dict) and 'type' in value:
                param_type = value['type']
                if param_type in TYPE_MAP:
                    param_class = TYPE_MAP[param_type]
                    # Use from_json if available, otherwise use load
                    if hasattr(param_class, 'from_json'):
                        setattr(self, key, param_class.from_json(value))
                    else:
                        setattr(self, key, param_class.load(value['value']))
                else:
                    raise ValueError(f"Unknown parameter type '{param_type}' for key '{key}'")
            
            # Handle basic Python types
            elif isinstance(current_value, (int, float, str, bool)):
                if not isinstance(value, type(current_value)):
                    raise TypeError(f"Type mismatch for key '{key}': expected {type(current_value)}, got {type(value)}")
                setattr(self, key, value)
            
            # Handle lists (need to preserve type if it's a list of custom params)
            elif isinstance(current_value, list):
                if isinstance(value, list):
                    # If current list contains custom parameter types, load them
                    if current_value and isinstance(current_value[0], CFG_TYPES):
                        param_class = type(current_value[0])
                        new_list = []
                        for item in value:
                            if isinstance(item, dict) and 'type' in item:
                                new_list.append(param_class.from_json(item))
                            else:
                                new_list.append(param_class.load(item))
                        setattr(self, key, new_list)
                    else:
                        # Basic list of primitives
                        setattr(self, key, value)
                else:
                    raise TypeError(f"Expected list for key '{key}', got {type(value)}")
            
            # Handle custom parameter types
            elif isinstance(current_value, CFG_TYPES):
                param_class = type(current_value)
                if hasattr(param_class, 'from_json') and isinstance(value, dict):
                    setattr(self, key, param_class.from_json(value))
                else:
                    setattr(self, key, param_class.load(value))
            
            else:
                raise TypeError(f"Unsupported config type for key '{key}': {type(current_value)}")
            
    def export_config(self) -> Dict[str, Any]:
        """
        Export the current configuration to a dictionary.
        
        Returns:
            Dictionary with configuration data suitable for JSON serialization
        """
        config = {}
        
        # Get all attributes including class attributes with annotations
        all_attrs = {}
        
        # Get class attributes (including annotated ones)
        for cls in reversed(self.__class__.__mro__):
            if hasattr(cls, '__annotations__'):
                for key in cls.__annotations__:
                    if hasattr(self, key):
                        all_attrs[key] = getattr(self, key)
        
        # Add instance attributes
        all_attrs.update(self.__dict__)
        
        for key, value in all_attrs.items():
            # Skip private attributes and methods
            if key.startswith('_') or callable(value):
                continue
                
            # Handle custom parameter types
            if isinstance(value, CFG_TYPES):
                if hasattr(value, 'to_json'):
                    config[key] = value.to_json()
                else:
                    config[key] = {
                        'type': value.type(),
                        'value': getattr(value, 'value', value)
                    }
            
            # Handle lists of custom parameter types
            elif isinstance(value, list) and value and isinstance(value[0], CFG_TYPES):
                config[key] = [item.to_json() if hasattr(item, 'to_json') else {
                    'type': item.type(),
                    'value': getattr(item, 'value', item)
                } for item in value]
            
            # Handle basic Python types
            elif isinstance(value, (int, float, str, bool, list)):
                config[key] = value
            
            else:
                # Try to convert to string for unknown types
                config[key] = str(value)
                
        return config
    
    def export_config_json(self, indent: int = 2) -> str:
        """
        Export configuration as JSON string.
        
        Args:
            indent: Number of spaces for JSON indentation
            
        Returns:
            JSON string representation of the configuration
        """
        return json.dumps(self.export_config(), indent=indent)
    
    def import_config_json(self, json_str: str):
        """
        Import configuration from JSON string.
        
        Args:
            json_str: JSON string containing configuration data
        """
        config_data = json.loads(json_str)
        self.import_config(config_data)