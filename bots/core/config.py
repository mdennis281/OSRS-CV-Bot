from .cfg_types import StringParam, IntParam, FloatParam, BooleanParam, RGBParam
from .cfg_types import TYPES as CFG_TYPES

example_config = {
    "bank_tile": {'type': "RGB", 'value': [255, 0, 100]},
    "furnace_tile": {'type': "RGB", 'value': [0, 255, 100]},
    "ore_name": {'type': "String", 'value': "Iron ore"},
    "bar_name": {'type': "String", 'value': "Steel bar"},
    "coal_per_bar": {'type': "Int", 'value': 2},
}


class BotConfigMixin():
    """
    Mixin class for bot configuration.
    This class can be used to add configuration properties to a bot.
    """
    max_time: IntParam = IntParam(60)  



    def import_config(self, config: dict):
        """
        Load configuration from a dictionary.
        """
        for key, value in config.items():
            if key in self.__dict__:
                config = self.__dict__[key]
                if isinstance(config, CFG_TYPES):
                    # Load the value using the appropriate type class
                    self.__dict__[key] = config.load(value['value'])
                else:
                    raise TypeError(f"Unsupported config type for key '{key}': {type(config)}")
            else:
                raise KeyError(f"Config key '{key}' not found in bot configuration.")
            
    def export_config(self) -> dict:
        """
        Export the current configuration to a dictionary.
        """
        config = {}
        for key, value in self.__dict__.items():
            if isinstance(value, CFG_TYPES):
                config[key] = {
                    'type': value.type(),
                    'value': value.val()
                }
            else:
                raise TypeError(f"Unsupported config type for key '{key}': {type(value)}")
        return config