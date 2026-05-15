"""Pydantic models for configuration parameter types."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel


class ConfigParamModel(BaseModel):
    """Generic config parameter with type and value."""
    type: str
    value: Any
    description: str = ""
